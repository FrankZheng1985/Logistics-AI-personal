"""
Maria 智能缓存服务
使用Redis缓存常见查询结果，大幅提升响应速度
"""
import json
import redis.asyncio as redis
from typing import Any, Optional
from datetime import timedelta
from loguru import logger

from app.core.config import settings


class CacheService:
    """智能缓存服务"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """连接Redis"""
        if self._connected:
            return
        
        try:
            # 从REDIS_URL解析连接参数，使用DB1作为缓存数据库
            redis_url = settings.REDIS_URL.replace("/0", "/1")  # 使用DB1，DB0给任务队列
            
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True
            )
            await self.redis_client.ping()
            self._connected = True
            logger.info("✅ 缓存服务已连接Redis (DB1)")
        except Exception as e:
            logger.warning(f"⚠️ Redis连接失败，缓存功能不可用: {e}")
            self.redis_client = None
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self._connected or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(f"maria:cache:{key}")
            if value:
                logger.debug(f"[缓存命中] {key}")
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"[缓存获取失败] {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值（会被JSON序列化）
            ttl: 过期时间（秒），默认5分钟
        """
        if not self._connected or not self.redis_client:
            return False
        
        try:
            await self.redis_client.setex(
                f"maria:cache:{key}",
                ttl,
                json.dumps(value, ensure_ascii=False, default=str)
            )
            logger.debug(f"[缓存写入] {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"[缓存写入失败] {key}: {e}")
            return False
    
    async def delete(self, key: str):
        """删除缓存"""
        if not self._connected or not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(f"maria:cache:{key}")
            logger.debug(f"[缓存删除] {key}")
            return True
        except Exception as e:
            logger.warning(f"[缓存删除失败] {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """清除匹配模式的所有缓存"""
        if not self._connected or not self.redis_client:
            return False
        
        try:
            keys = []
            async for key in self.redis_client.scan_iter(f"maria:cache:{pattern}*"):
                keys.append(key)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"[缓存清除] 清除了 {len(keys)} 个缓存: {pattern}*")
            return True
        except Exception as e:
            logger.warning(f"[缓存清除失败] {pattern}: {e}")
            return False
    
    async def get_or_set(self, key: str, fetch_func, ttl: int = 300) -> Any:
        """获取缓存，如果不存在则调用函数并缓存结果
        
        Args:
            key: 缓存键
            fetch_func: 异步函数，用于获取数据
            ttl: 缓存过期时间（秒）
        """
        # 先尝试从缓存获取
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # 缓存未命中，调用函数获取数据
        try:
            logger.debug(f"[缓存未命中] {key}，正在获取数据...")
            result = await fetch_func()
            
            # 缓存结果
            await self.set(key, result, ttl)
            
            return result
        except Exception as e:
            logger.error(f"[数据获取失败] {key}: {e}")
            raise
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
            logger.info("Redis缓存连接已关闭")


# 全局缓存服务实例
cache_service = CacheService()


# 便捷的缓存装饰器
def cached(ttl: int = 300, key_prefix: str = ""):
    """
    缓存装饰器
    
    使用示例:
    @cached(ttl=600, key_prefix="email_summary")
    async def get_email_summary(user_id: str):
        # 数据库查询...
        return result
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                cache_key += f":{':'.join(str(arg) for arg in args)}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # 使用get_or_set
            return await cache_service.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                ttl
            )
        return wrapper
    return decorator
