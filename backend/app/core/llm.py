"""
LLM（大语言模型）调用封装
支持 Claude 和 GPT-4
"""
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import httpx
from loguru import logger

from app.core.config import settings


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
        """发送聊天消息到Claude"""
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
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
            except Exception as e:
                logger.error(f"Claude API调用失败: {e}")
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
        """发送聊天消息到GPT"""
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
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenAI API调用失败: {e}")
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
    use_fallback: bool = False
) -> str:
    """
    统一的聊天完成接口
    
    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大token数
        use_fallback: 是否使用备用模型
    
    Returns:
        AI回复内容
    """
    llm = LLMFactory.get_fallback() if use_fallback else LLMFactory.get_primary()
    
    return await llm.chat(
        messages=messages,
        system_prompt=system_prompt,
        temperature=temperature or settings.AI_TEMPERATURE,
        max_tokens=max_tokens or settings.AI_MAX_TOKENS
    )
