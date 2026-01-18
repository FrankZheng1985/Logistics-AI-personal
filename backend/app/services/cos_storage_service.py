"""
腾讯云COS存储服务
用于上传录音文件、图片等资源，获取公网可访问URL
"""
import os
import time
import uuid
from typing import Optional, Tuple
from loguru import logger

from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

from app.core.config import settings


class COSStorageService:
    """腾讯云COS对象存储服务"""
    
    def __init__(self):
        # COS专用凭证优先，否则使用腾讯云统一凭证
        self.secret_id = settings.COS_SECRET_ID or getattr(settings, 'TENCENT_SECRET_ID', None)
        self.secret_key = settings.COS_SECRET_KEY or getattr(settings, 'TENCENT_SECRET_KEY', None)
        self.bucket = settings.COS_BUCKET
        self.region = settings.COS_REGION or "ap-guangzhou"
        self._client: Optional[CosS3Client] = None
    
    @property
    def is_configured(self) -> bool:
        """检查COS是否已配置"""
        return bool(self.secret_id and self.secret_key and self.bucket)
    
    @property
    def client(self) -> Optional[CosS3Client]:
        """获取COS客户端"""
        if not self.is_configured:
            return None
        
        if self._client is None:
            config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
                Token=None,
                Scheme='https'
            )
            self._client = CosS3Client(config)
        
        return self._client
    
    def _generate_key(self, filename: str, folder: str = "audio") -> str:
        """生成COS对象key（路径）"""
        # 使用日期+UUID生成唯一key
        date_path = time.strftime("%Y/%m/%d")
        unique_id = str(uuid.uuid4())[:8]
        
        # 获取文件扩展名
        ext = os.path.splitext(filename)[1] or ".mp3"
        
        return f"{folder}/{date_path}/{unique_id}{ext}"
    
    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        folder: str = "audio",
        content_type: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        上传字节数据到COS
        
        Args:
            data: 文件字节数据
            filename: 原始文件名
            folder: 存储文件夹（audio/image/video等）
            content_type: 内容类型
        
        Returns:
            (success, url_or_error)
        """
        if not self.is_configured:
            return False, "腾讯云COS未配置，请设置COS_SECRET_ID、COS_SECRET_KEY、COS_BUCKET"
        
        try:
            key = self._generate_key(filename, folder)
            
            # 根据文件扩展名设置content_type
            if not content_type:
                ext = os.path.splitext(filename)[1].lower()
                content_type_map = {
                    ".mp3": "audio/mpeg",
                    ".m4a": "audio/mp4",
                    ".wav": "audio/wav",
                    ".amr": "audio/amr",
                    ".ogg": "audio/ogg",
                    ".aac": "audio/aac",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".mp4": "video/mp4",
                }
                content_type = content_type_map.get(ext, "application/octet-stream")
            
            # 上传到COS
            import io
            response = self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=io.BytesIO(data),
                ContentType=content_type
            )
            
            # 生成公网访问URL
            url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"
            
            logger.info(f"[COS] 文件上传成功: {key} -> {url}")
            return True, url
            
        except Exception as e:
            logger.error(f"[COS] 文件上传失败: {e}")
            return False, str(e)
    
    async def upload_file(
        self,
        file_path: str,
        folder: str = "audio"
    ) -> Tuple[bool, str]:
        """
        上传本地文件到COS
        
        Args:
            file_path: 本地文件路径
            folder: 存储文件夹
        
        Returns:
            (success, url_or_error)
        """
        if not self.is_configured:
            return False, "腾讯云COS未配置"
        
        try:
            filename = os.path.basename(file_path)
            key = self._generate_key(filename, folder)
            
            # 上传文件
            response = self.client.upload_file(
                Bucket=self.bucket,
                Key=key,
                LocalFilePath=file_path,
                EnableMD5=False
            )
            
            # 生成公网访问URL
            url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"
            
            logger.info(f"[COS] 文件上传成功: {file_path} -> {url}")
            return True, url
            
        except Exception as e:
            logger.error(f"[COS] 文件上传失败: {e}")
            return False, str(e)
    
    async def delete_file(self, key: str) -> bool:
        """删除COS文件"""
        if not self.is_configured:
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            logger.info(f"[COS] 文件删除成功: {key}")
            return True
        except Exception as e:
            logger.error(f"[COS] 文件删除失败: {e}")
            return False
    
    def get_config_status(self) -> dict:
        """获取配置状态"""
        return {
            "configured": self.is_configured,
            "secret_id": bool(self.secret_id),
            "secret_key": bool(self.secret_key),
            "bucket": bool(self.bucket),
            "region": self.region,
            "message": "配置完整" if self.is_configured else "请配置COS_SECRET_ID、COS_SECRET_KEY、COS_BUCKET"
        }


# 创建单例
cos_storage_service = COSStorageService()
