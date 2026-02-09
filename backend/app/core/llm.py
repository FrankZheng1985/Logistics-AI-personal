"""
LLM（大语言模型）调用封装
支持 Claude 和 GPT-4，包含重试机制和用量记录
"""
from typing import Optional, List, Dict, Any, Callable, TypeVar
from abc import ABC, abstractmethod
import httpx
import asyncio
import random
import time
import uuid
from loguru import logger

from app.core.config import settings


# 重试配置
MAX_RETRIES = 3
BASE_DELAY = 1.0  # 基础延迟（秒）
MAX_DELAY = 30.0  # 最大延迟（秒）

# 限流配置
MAX_CONCURRENT_REQUESTS = 10  # 最大并发请求数
REQUESTS_PER_MINUTE = 60      # 每分钟最大请求数

# 全局限流器
_request_semaphore: asyncio.Semaphore = None
_request_times: list = []  # 记录请求时间戳


def _get_semaphore() -> asyncio.Semaphore:
    """获取或创建信号量（延迟初始化）"""
    global _request_semaphore
    if _request_semaphore is None:
        _request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    return _request_semaphore


async def _check_rate_limit():
    """
    检查请求频率限制
    使用滑动窗口算法
    """
    global _request_times
    
    now = time.time()
    # 清理超过1分钟的记录
    _request_times = [t for t in _request_times if now - t < 60]
    
    if len(_request_times) >= REQUESTS_PER_MINUTE:
        # 计算需要等待的时间
        oldest = _request_times[0]
        wait_time = 60 - (now - oldest) + 0.1
        if wait_time > 0:
            logger.warning(f"LLM 请求频率限制，等待 {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
    
    _request_times.append(time.time())

# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ConnectTimeout,
)

# 可重试的HTTP状态码
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

T = TypeVar('T')

# 当前调用上下文（用于传递agent_name等信息）
_current_context: Dict[str, Any] = {}


def set_llm_context(agent_name: str = None, task_type: str = None, agent_id: int = None):
    """设置LLM调用上下文"""
    global _current_context
    _current_context = {
        "agent_name": agent_name,
        "task_type": task_type,
        "agent_id": agent_id
    }


def clear_llm_context():
    """清除LLM调用上下文"""
    global _current_context
    _current_context = {}


def get_llm_context() -> Dict[str, Any]:
    """获取当前LLM调用上下文"""
    return _current_context.copy()


async def retry_with_exponential_backoff(
    func: Callable,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    retryable_exceptions: tuple = RETRYABLE_EXCEPTIONS,
    retryable_status_codes: set = RETRYABLE_STATUS_CODES,
) -> Any:
    """
    带指数退避的重试机制
    
    Args:
        func: 要执行的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟秒数
        max_delay: 最大延迟秒数
        retryable_exceptions: 可重试的异常类型
        retryable_status_codes: 可重试的HTTP状态码
    
    Returns:
        函数执行结果
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            last_exception = e
            status_code = e.response.status_code
            
            if status_code not in retryable_status_codes:
                # 不可重试的状态码，直接抛出
                raise
            
            if attempt < max_retries:
                # 计算延迟时间（指数退避 + 随机抖动）
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                logger.warning(
                    f"LLM API返回{status_code}，{delay:.1f}秒后重试 "
                    f"(尝试 {attempt + 1}/{max_retries + 1})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"LLM API调用失败，已达最大重试次数: {e}")
                raise
                
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                logger.warning(
                    f"LLM API连接错误: {type(e).__name__}，{delay:.1f}秒后重试 "
                    f"(尝试 {attempt + 1}/{max_retries + 1})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"LLM API调用失败，已达最大重试次数: {e}")
                raise
                
        except Exception as e:
            # 其他异常不重试，直接抛出
            logger.error(f"LLM API调用出现不可重试的错误: {e}")
            raise
    
    # 不应该到达这里，但以防万一
    if last_exception:
        raise last_exception


def estimate_tokens(text: str) -> int:
    """
    估算文本的token数量
    粗略估算：中文约1.5字/token，英文约4字符/token
    """
    if not text:
        return 0
    
    # 统计中文字符
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 统计其他字符
    other_chars = len(text) - chinese_chars
    
    # 中文按1.5字/token，其他按4字符/token估算
    estimated = int(chinese_chars / 1.5 + other_chars / 4)
    return max(1, estimated)


class BaseLLM(ABC):
    """LLM基类"""
    
    provider: str = "unknown"  # 提供商标识
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """发送聊天消息"""
        pass
    
    async def _record_usage(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        response_time_ms: int,
        is_success: bool = True,
        error_message: str = None,
        request_id: str = None
    ):
        """记录API调用用量"""
        try:
            from app.services.ai_usage_service import record_ai_usage
            
            context = get_llm_context()
            
            await record_ai_usage(
                provider=self.provider,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                agent_name=context.get("agent_name"),
                agent_id=context.get("agent_id"),
                task_type=context.get("task_type"),
                request_id=request_id or str(uuid.uuid4())[:8],
                response_time_ms=response_time_ms,
                is_success=is_success,
                error_message=error_message
            )
        except Exception as e:
            # 用量记录失败不应影响主流程
            logger.warning(f"记录LLM用量失败: {e}")


class ClaudeLLM(BaseLLM):
    """Claude API 封装"""
    
    provider = "anthropic"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.model = settings.AI_PRIMARY_MODEL
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """发送聊天消息到Claude（带重试机制和用量记录）"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        # 估算输入tokens
        input_text = system_prompt or ""
        for msg in messages:
            input_text += msg.get("content", "")
        estimated_input_tokens = estimate_tokens(input_text)
        
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        async def _make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        
        try:
            # 应用限流
            await _check_rate_limit()
            semaphore = _get_semaphore()
            
            async with semaphore:
                data = await retry_with_exponential_backoff(_make_request)
            
            response_text = data["content"][0]["text"]
        
            # 计算响应时间
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 获取实际token使用量（Claude API返回的）
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", estimated_input_tokens)
            output_tokens = usage.get("output_tokens", estimate_tokens(response_text))
            
            # 记录用量
            await self._record_usage(
                model_name=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response_time_ms=response_time_ms,
                is_success=True,
                request_id=request_id
            )
            
            return response_text
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 记录失败
            await self._record_usage(
                model_name=self.model,
                input_tokens=estimated_input_tokens,
                output_tokens=0,
                response_time_ms=response_time_ms,
                is_success=False,
                error_message=str(e),
                request_id=request_id
            )
            
            logger.error(f"Claude API调用失败（已重试）: {e}")
            raise


class OpenAILLM(BaseLLM):
    """OpenAI GPT API 封装（也支持通义千问兼容接口）"""
    
    def __init__(self, api_key: str, base_url: str = None, model: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model or settings.AI_FALLBACK_MODEL
        
        # 根据base_url判断provider
        if "dashscope" in self.base_url:
            self.provider = "dashscope"
        elif "deepseek" in self.base_url:
            self.provider = "deepseek"
        else:
            self.provider = "openai"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """发送聊天消息到GPT（带重试机制和用量记录）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 如果有系统提示，添加到消息列表开头
        full_messages = messages.copy()
        if system_prompt:
            full_messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 估算输入tokens
        input_text = ""
        for msg in full_messages:
            input_text += msg.get("content", "")
        estimated_input_tokens = estimate_tokens(input_text)
        
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        async def _make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()
        
        try:
            # 应用限流
            await _check_rate_limit()
            semaphore = _get_semaphore()
            
            async with semaphore:
                data = await retry_with_exponential_backoff(_make_request)
            
            response_text = data["choices"][0]["message"]["content"]
        
            # 计算响应时间
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 获取实际token使用量（API返回的）
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", estimated_input_tokens)
            output_tokens = usage.get("completion_tokens", estimate_tokens(response_text))
            
            # 记录用量
            await self._record_usage(
                model_name=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response_time_ms=response_time_ms,
                is_success=True,
                request_id=request_id
            )
            
            return response_text
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 记录失败
            await self._record_usage(
                model_name=self.model,
                input_tokens=estimated_input_tokens,
                output_tokens=0,
                response_time_ms=response_time_ms,
                is_success=False,
                error_message=str(e),
                request_id=request_id
            )
            
            logger.error(f"OpenAI API调用失败（已重试）: {e}")
            raise


    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """
        带工具调用的聊天（Function Calling）
        
        Args:
            messages: 消息列表
            tools: OpenAI 格式的工具定义列表
            temperature: 温度
            max_tokens: 最大token数
            system_prompt: 系统提示词
            tool_choice: 工具选择策略（auto/none/required）
        
        Returns:
            {"content": "文本回复", "tool_calls": [{"id": "...", "function": {"name": "...", "arguments": "..."}}]}
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        full_messages = messages.copy()
        if system_prompt:
            full_messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": tool_choice,
        }
        
        # 估算输入tokens
        input_text = ""
        for msg in full_messages:
            input_text += msg.get("content", "") or ""
        estimated_input_tokens = estimate_tokens(input_text)
        
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        async def _make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120.0  # 工具调用可能需要更多时间思考
                )
                response.raise_for_status()
                return response.json()
        
        try:
            # 应用限流
            await _check_rate_limit()
            semaphore = _get_semaphore()
            
            async with semaphore:
                data = await retry_with_exponential_backoff(_make_request)
            
            message = data["choices"][0]["message"]
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", estimated_input_tokens)
            output_tokens = usage.get("completion_tokens", 0)
            
            await self._record_usage(
                model_name=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                response_time_ms=response_time_ms,
                is_success=True,
                request_id=request_id
            )
            
            # 返回标准化格式
            result = {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", None),
                "role": "assistant"
            }
            return result
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            await self._record_usage(
                model_name=self.model,
                input_tokens=estimated_input_tokens,
                output_tokens=0,
                response_time_ms=response_time_ms,
                is_success=False,
                error_message=str(e),
                request_id=request_id
            )
            
            logger.error(f"OpenAI API (tools) 调用失败: {e}")
            raise


class HunyuanLLM(BaseLLM):
    """腾讯混元 API 封装"""
    
    provider = "hunyuan"
    
    def __init__(self, secret_id: str, secret_key: str, model: str = "hunyuan-pro"):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.model = model
        self.endpoint = "hunyuan.tencentcloudapi.com"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """调用腾讯混元 API"""
        import hashlib
        import hmac
        from datetime import datetime
        
        # 构建消息
        full_messages = messages.copy()
        if system_prompt:
            full_messages.insert(0, {"role": "system", "content": system_prompt})
        
        # 腾讯云 API 签名（简化版，实际应使用 SDK）
        # 这里使用 HTTP API 兼容模式
        try:
            import httpx
            
            # 腾讯混元也支持 OpenAI 兼容接口
            headers = {
                "Authorization": f"Bearer {self.secret_id}:{self.secret_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": full_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            start_time = time.time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
            
            response_text = data["choices"][0]["message"]["content"]
            
            # 记录用量
            response_time_ms = int((time.time() - start_time) * 1000)
            usage = data.get("usage", {})
            await self._record_usage(
                model_name=self.model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                response_time_ms=response_time_ms,
                is_success=True
            )
            
            return response_text
            
        except Exception as e:
            logger.error(f"腾讯混元 API 调用失败: {e}")
            raise


class LLMFactory:
    """
    LLM工厂类 - 博士后级多模型智能路由
    
    模型矩阵：
    - Qwen-Max: 主力模型，综合能力强
    - DeepSeek: 代码专家，逻辑分析强
    - 混元Pro: 腾讯云原生，稳定备份
    - Claude (OpenRouter): 复杂推理，法律分析
    - Gemini (OpenRouter): 长上下文，多模态
    - GPT-4 (OpenRouter): 通用备选
    """
    
    _claude_instance: Optional[ClaudeLLM] = None
    _openai_instance: Optional[OpenAILLM] = None
    _qwen_instance: Optional[OpenAILLM] = None
    _deepseek_instance: Optional[OpenAILLM] = None
    _hunyuan_instance: Optional[HunyuanLLM] = None
    _openrouter_claude_instance: Optional[OpenAILLM] = None
    _openrouter_gemini_instance: Optional[OpenAILLM] = None
    _openrouter_gpt4_instance: Optional[OpenAILLM] = None
    
    @classmethod
    def get_primary(cls) -> BaseLLM:
        """获取主力LLM（Qwen-Max 优先）"""
        # 优先使用通义千问 Max
        if settings.DASHSCOPE_API_KEY:
            if cls._qwen_instance is None:
                cls._qwen_instance = OpenAILLM(
                    api_key=settings.DASHSCOPE_API_KEY,
                    base_url=settings.DASHSCOPE_BASE_URL,
                    model=settings.DASHSCOPE_MODEL  # qwen-max
                )
            return cls._qwen_instance
        
        # 备用：DeepSeek
        if settings.DEEPSEEK_API_KEY:
            return cls.get_deepseek()
        
        raise ValueError("未配置任何AI API密钥，请在.env中配置 DASHSCOPE_API_KEY")
    
    @classmethod
    def get_deepseek(cls) -> BaseLLM:
        """获取 DeepSeek（代码和逻辑分析专家）"""
        if settings.DEEPSEEK_API_KEY:
            if cls._deepseek_instance is None:
                cls._deepseek_instance = OpenAILLM(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_API_BASE,
                    model="deepseek-chat"
                )
            return cls._deepseek_instance
        return cls.get_primary()
    
    @classmethod
    def get_hunyuan(cls) -> Optional[BaseLLM]:
        """获取腾讯混元（稳定备份）"""
        secret_id = getattr(settings, 'HUNYUAN_SECRET_ID', None) or getattr(settings, 'TENCENT_SECRET_ID', None)
        secret_key = getattr(settings, 'HUNYUAN_SECRET_KEY', None) or getattr(settings, 'TENCENT_SECRET_KEY', None)
        
        if secret_id and secret_key:
            if cls._hunyuan_instance is None:
                cls._hunyuan_instance = HunyuanLLM(
                    secret_id=secret_id,
                    secret_key=secret_key,
                    model=getattr(settings, 'HUNYUAN_MODEL', 'hunyuan-pro')
                )
            return cls._hunyuan_instance
        return None
    
    @classmethod
    def get_claude_via_openrouter(cls) -> Optional[BaseLLM]:
        """通过 OpenRouter 获取 Claude（复杂推理/法律分析）"""
        api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        if api_key:
            if cls._openrouter_claude_instance is None:
                cls._openrouter_claude_instance = OpenAILLM(
                    api_key=api_key,
                    base_url=getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    model=getattr(settings, 'OPENROUTER_CLAUDE_MODEL', 'anthropic/claude-3.5-sonnet')
                )
                cls._openrouter_claude_instance.provider = "openrouter/claude"
            return cls._openrouter_claude_instance
        return None
    
    @classmethod
    def get_gemini_via_openrouter(cls) -> Optional[BaseLLM]:
        """通过 OpenRouter 获取 Gemini（长上下文/多模态）"""
        api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        if api_key:
            if cls._openrouter_gemini_instance is None:
                cls._openrouter_gemini_instance = OpenAILLM(
                    api_key=api_key,
                    base_url=getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    model=getattr(settings, 'OPENROUTER_GEMINI_MODEL', 'google/gemini-pro-1.5')
                )
                cls._openrouter_gemini_instance.provider = "openrouter/gemini"
            return cls._openrouter_gemini_instance
        return None
    
    @classmethod
    def get_gpt4_via_openrouter(cls) -> Optional[BaseLLM]:
        """通过 OpenRouter 获取 GPT-4"""
        api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        if api_key:
            if cls._openrouter_gpt4_instance is None:
                cls._openrouter_gpt4_instance = OpenAILLM(
                    api_key=api_key,
                    base_url=getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    model=getattr(settings, 'OPENROUTER_GPT4_MODEL', 'openai/gpt-4-turbo')
                )
                cls._openrouter_gpt4_instance.provider = "openrouter/gpt4"
            return cls._openrouter_gpt4_instance
        return None
    
    @classmethod
    def get_advanced(cls) -> BaseLLM:
        """获取高级LLM（复杂任务：代码/计划/深度分析）
        优先级：DeepSeek > Claude(OpenRouter) > Qwen-Max
        """
        # DeepSeek-V3 在代码和长文本逻辑上最强
        if settings.DEEPSEEK_API_KEY:
            return cls.get_deepseek()
        
        # Claude 擅长复杂推理
        claude = cls.get_claude_via_openrouter()
        if claude:
            return claude
        
        # 回退到 Qwen-Max
        return cls.get_primary()
    
    @classmethod
    def get_for_task(cls, task_type: str) -> BaseLLM:
        """
        根据任务类型智能选择最优模型
        
        Args:
            task_type: 任务类型
                - "code": 代码生成/分析
                - "legal": 法律/合同分析
                - "finance": 财务/会计分析
                - "creative": 创意写作
                - "chat": 日常对话
                - "long_doc": 长文档分析
                - "reasoning": 复杂推理
        
        Returns:
            最适合的 LLM 实例
        """
        task_type = task_type.lower() if task_type else "chat"
        
        # 代码任务 → DeepSeek 最强
        if task_type in ["code", "coding", "programming"]:
            return cls.get_deepseek()
        
        # 法律/合同分析 → Claude 推理能力强
        if task_type in ["legal", "contract", "law"]:
            claude = cls.get_claude_via_openrouter()
            if claude:
                return claude
            return cls.get_deepseek()  # DeepSeek 也不错
        
        # 财务/会计 → DeepSeek 逻辑强
        if task_type in ["finance", "accounting", "calculation"]:
            return cls.get_deepseek()
        
        # 长文档 → Gemini 上下文窗口大
        if task_type in ["long_doc", "long_document", "summarize"]:
            gemini = cls.get_gemini_via_openrouter()
            if gemini:
                return gemini
            return cls.get_primary()
        
        # 复杂推理 → Claude 或 DeepSeek
        if task_type in ["reasoning", "analysis", "planning"]:
            claude = cls.get_claude_via_openrouter()
            if claude:
                return claude
            return cls.get_deepseek()
        
        # 创意写作 → Qwen-Max 中文写作强
        if task_type in ["creative", "writing", "copywriting"]:
            return cls.get_primary()
        
        # 默认：日常对话用 Qwen-Max
        return cls.get_primary()
    
    @classmethod
    def get_fallback(cls) -> BaseLLM:
        """获取备用LLM（按优先级尝试所有可用模型）"""
        # 尝试顺序：Qwen > DeepSeek > 混元 > OpenRouter GPT-4
        if settings.DASHSCOPE_API_KEY:
            return cls.get_primary()
        
        if settings.DEEPSEEK_API_KEY:
            return cls.get_deepseek()
        
        hunyuan = cls.get_hunyuan()
        if hunyuan:
            return hunyuan
        
        gpt4 = cls.get_gpt4_via_openrouter()
        if gpt4:
            return gpt4
        
        raise ValueError("未配置任何AI API密钥")


async def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = None,
    max_tokens: int = None,
    use_fallback: bool = False,
    use_advanced: bool = False,
    auto_fallback: bool = True,
    agent_name: str = None,
    task_type: str = None,
    agent_id: int = None,
    tools: List[Dict[str, Any]] = None,
    tool_choice: str = "auto",
    model_preference: str = None  # 新增：模型偏好（code/legal/finance/creative/long_doc/reasoning）
) -> Any:
    """
    统一的聊天完成接口（博士后级智能路由 + 自动降级）
    
    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大token数
        use_fallback: 是否使用备用模型
        use_advanced: 是否使用高级模型（代码/计划书/深度分析）
        auto_fallback: 主模型失败时是否自动切换到备用模型
        agent_name: AI员工名称（用于用量统计）
        task_type: 任务类型（用于用量统计）
        agent_id: AI员工ID（用于用量统计）
        tools: 工具定义列表
        tool_choice: 工具选择策略
        model_preference: 模型偏好，用于智能路由
            - "code": 代码任务 → DeepSeek
            - "legal": 法律分析 → Claude (OpenRouter)
            - "finance": 财务分析 → DeepSeek
            - "creative": 创意写作 → Qwen-Max
            - "long_doc": 长文档 → Gemini (OpenRouter)
            - "reasoning": 复杂推理 → Claude (OpenRouter)
    
    Returns:
        - 无 tools 时：str（AI回复文本）
        - 有 tools 时：dict（{"content": "...", "tool_calls": [...]}）
    """
    # 设置调用上下文
    if agent_name or task_type or agent_id:
        set_llm_context(agent_name=agent_name, task_type=task_type, agent_id=agent_id)
    
    kwargs = {
        "messages": messages,
        "system_prompt": system_prompt,
        "temperature": temperature or settings.AI_TEMPERATURE,
        "max_tokens": max_tokens or settings.AI_MAX_TOKENS
    }
    
    try:
        # ===== 智能模型选择 =====
        def select_llm():
            """根据参数智能选择最优模型"""
            # 1. 如果指定了模型偏好，使用智能路由
            if model_preference:
                return LLMFactory.get_for_task(model_preference)
            
            # 2. 如果使用备用模型
            if use_fallback:
                return LLMFactory.get_fallback()
            
            # 3. 如果使用高级模型
            if use_advanced:
                return LLMFactory.get_advanced()
            
            # 4. 默认使用主力模型
            return LLMFactory.get_primary()
        
        # ===== 带工具调用的模式 =====
        if tools:
            tools_kwargs = {
                **kwargs,
                "tools": tools,
                "tool_choice": tool_choice,
            }
            
            llm = select_llm()
            
            # 只有 OpenAILLM 支持 chat_with_tools
            if hasattr(llm, 'chat_with_tools'):
                try:
                    return await llm.chat_with_tools(**tools_kwargs)
                except Exception as e:
                    if auto_fallback:
                        logger.warning(f"LLM tools调用失败，尝试备用: {e}")
                        for fallback_llm in [LLMFactory.get_advanced(), LLMFactory.get_primary()]:
                            if fallback_llm is not llm and hasattr(fallback_llm, 'chat_with_tools'):
                                try:
                                    return await fallback_llm.chat_with_tools(**tools_kwargs)
                                except Exception:
                                    continue
                        # 所有工具调用都失败，降级为纯文本
                        logger.warning("所有LLM的tools调用都失败，降级为纯文本对话")
                        result = await llm.chat(**kwargs)
                        return {"content": result, "tool_calls": None}
                    raise
            else:
                # 不支持工具调用的 LLM，降级为纯文本
                result = await llm.chat(**kwargs)
                return {"content": result, "tool_calls": None}
        
        # ===== 普通文本模式 =====
        llm = select_llm()
        
        # 尝试选中的模型
        try:
            return await llm.chat(**kwargs)
        except Exception as e:
            if auto_fallback:
                logger.warning(f"LLM调用失败 ({llm.provider if hasattr(llm, 'provider') else 'unknown'})，尝试备用模型: {e}")
                # 尝试备用模型列表
                fallback_order = [
                    LLMFactory.get_deepseek,
                    LLMFactory.get_primary,
                    LLMFactory.get_hunyuan,
                    LLMFactory.get_claude_via_openrouter,
                    LLMFactory.get_gpt4_via_openrouter
                ]
                for get_fallback in fallback_order:
                    try:
                        fallback_llm = get_fallback()
                        if fallback_llm and fallback_llm is not llm:
                            logger.info(f"尝试备用模型: {fallback_llm.provider if hasattr(fallback_llm, 'provider') else 'unknown'}")
                            return await fallback_llm.chat(**kwargs)
                    except Exception as fallback_error:
                        continue
                logger.error("所有备用模型都调用失败")
            raise
    finally:
        # 清除调用上下文
        clear_llm_context()
