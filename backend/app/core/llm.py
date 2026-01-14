"""
LLM（大语言模型）调用封装
支持 Claude 和 GPT-4，包含重试机制
"""
from typing import Optional, List, Dict, Any, Callable, TypeVar
from abc import ABC, abstractmethod
import httpx
import asyncio
import random
from functools import wraps
from loguru import logger

from app.core.config import settings


# 重试配置
MAX_RETRIES = 3
BASE_DELAY = 1.0  # 基础延迟（秒）
MAX_DELAY = 30.0  # 最大延迟（秒）

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


class BaseLLM(ABC):
    """LLM基类"""
    
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


class ClaudeLLM(BaseLLM):
    """Claude API 封装"""
    
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
        """发送聊天消息到Claude（带重试机制）"""
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
        
        async def _make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        
        try:
            return await retry_with_exponential_backoff(_make_request)
        except Exception as e:
            logger.error(f"Claude API调用失败（已重试）: {e}")
            raise


class OpenAILLM(BaseLLM):
    """OpenAI GPT API 封装（也支持通义千问兼容接口）"""
    
    def __init__(self, api_key: str, base_url: str = None, model: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model or settings.AI_FALLBACK_MODEL
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """发送聊天消息到GPT（带重试机制）"""
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
        
        async def _make_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        
        try:
            return await retry_with_exponential_backoff(_make_request)
        except Exception as e:
            logger.error(f"OpenAI API调用失败（已重试）: {e}")
            raise


class LLMFactory:
    """LLM工厂类"""
    
    _claude_instance: Optional[ClaudeLLM] = None
    _openai_instance: Optional[OpenAILLM] = None
    _qwen_instance: Optional[OpenAILLM] = None
    
    @classmethod
    def get_primary(cls) -> BaseLLM:
        """获取主要LLM（优先级：通义千问 > Claude > OpenAI）"""
        # 优先使用通义千问（国内访问快，有免费额度）
        if settings.DASHSCOPE_API_KEY:
            if cls._qwen_instance is None:
                cls._qwen_instance = OpenAILLM(
                    api_key=settings.DASHSCOPE_API_KEY,
                    base_url=settings.DASHSCOPE_BASE_URL,
                    model=settings.DASHSCOPE_MODEL
                )
            return cls._qwen_instance
        
        # 其次使用 Claude
        if settings.ANTHROPIC_API_KEY:
            if cls._claude_instance is None:
                cls._claude_instance = ClaudeLLM(settings.ANTHROPIC_API_KEY)
            return cls._claude_instance
        
        # 最后使用 OpenAI
        return cls.get_fallback()
    
    @classmethod
    def get_fallback(cls) -> BaseLLM:
        """获取备用LLM（GPT-4）"""
        if settings.OPENAI_API_KEY:
            if cls._openai_instance is None:
                cls._openai_instance = OpenAILLM(settings.OPENAI_API_KEY)
            return cls._openai_instance
        raise ValueError("未配置任何AI API密钥，请在.env中配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")


async def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = None,
    max_tokens: int = None,
    use_fallback: bool = False,
    auto_fallback: bool = True
) -> str:
    """
    统一的聊天完成接口（带自动降级）
    
    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大token数
        use_fallback: 是否使用备用模型
        auto_fallback: 主模型失败时是否自动切换到备用模型
    
    Returns:
        AI回复内容
    """
    kwargs = {
        "messages": messages,
        "system_prompt": system_prompt,
        "temperature": temperature or settings.AI_TEMPERATURE,
        "max_tokens": max_tokens or settings.AI_MAX_TOKENS
    }
    
    if use_fallback:
        llm = LLMFactory.get_fallback()
        return await llm.chat(**kwargs)
    
    # 先尝试主模型
    try:
        llm = LLMFactory.get_primary()
        return await llm.chat(**kwargs)
    except Exception as e:
        if auto_fallback:
            logger.warning(f"主LLM调用失败，尝试备用模型: {e}")
            try:
                fallback_llm = LLMFactory.get_fallback()
                # 避免使用同一个实例
                if fallback_llm is not llm:
                    return await fallback_llm.chat(**kwargs)
            except ValueError:
                # 没有配置备用模型
                pass
            except Exception as fallback_error:
                logger.error(f"备用LLM也调用失败: {fallback_error}")
        raise
