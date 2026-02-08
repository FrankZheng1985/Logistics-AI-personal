"""
CredentialService - 凭证加密服务

使用 AES-256-GCM 加密存储在数据库中的敏感凭证（如邮箱密码、API密钥）。

加密密钥从环境变量 CREDENTIAL_ENCRYPTION_KEY 读取。
如果未配置，降级为明文模式（现有行为不受影响）。

加密流程：
1. 加密：plaintext -> AES-256-GCM(key, nonce) -> base64(nonce + ciphertext + tag) -> stored_value
2. 解密：stored_value -> base64_decode -> nonce + ciphertext + tag -> AES-256-GCM decrypt -> plaintext
"""
import base64
import os
from typing import Optional
from loguru import logger


class CredentialService:
    """凭证加密服务"""
    
    # 加密标记前缀，用于区分加密值和明文值
    ENCRYPTED_PREFIX = "enc::"
    
    def __init__(self):
        self._key: Optional[bytes] = None
        self._available = False
        self._init_key()
    
    def _init_key(self):
        """从环境变量初始化加密密钥"""
        key_str = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "")
        
        if not key_str:
            logger.info("[Credential] 未配置 CREDENTIAL_ENCRYPTION_KEY，凭证将以明文存储（兼容模式）")
            return
        
        try:
            # 支持 hex 格式的 32 字节密钥
            if len(key_str) == 64:
                self._key = bytes.fromhex(key_str)
            # 支持 base64 格式
            elif len(key_str) == 44:
                self._key = base64.b64decode(key_str)
            else:
                # 用 SHA-256 哈希用户提供的任意字符串作为密钥
                import hashlib
                self._key = hashlib.sha256(key_str.encode('utf-8')).digest()
            
            if len(self._key) != 32:
                logger.error(f"[Credential] 加密密钥长度不正确: {len(self._key)} bytes, 需要32 bytes")
                self._key = None
                return
            
            self._available = True
            logger.info("[Credential] 凭证加密服务已启用 (AES-256-GCM)")
            
        except Exception as e:
            logger.error(f"[Credential] 加密密钥初始化失败: {e}")
            self._key = None
    
    @property
    def is_available(self) -> bool:
        """加密功能是否可用"""
        return self._available
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密凭证
        
        Args:
            plaintext: 明文凭证
        
        Returns:
            加密后的字符串（带 enc:: 前缀），如果加密不可用则原样返回
        """
        if not plaintext:
            return plaintext
        
        if not self._available:
            return plaintext
        
        # 已经加密过的不重复加密
        if plaintext.startswith(self.ENCRYPTED_PREFIX):
            return plaintext
        
        try:
            from Crypto.Cipher import AES
            
            # AES-256-GCM
            nonce = os.urandom(12)  # 96-bit nonce
            cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
            
            # 拼接: nonce(12) + ciphertext(N) + tag(16)
            encrypted_bytes = nonce + ciphertext + tag
            
            # Base64 编码
            encoded = base64.b64encode(encrypted_bytes).decode('ascii')
            
            return f"{self.ENCRYPTED_PREFIX}{encoded}"
            
        except ImportError:
            logger.warning("[Credential] pycryptodome 未安装，无法加密")
            return plaintext
        except Exception as e:
            logger.error(f"[Credential] 加密失败: {e}")
            return plaintext
    
    def decrypt(self, stored_value: str) -> str:
        """
        解密凭证
        
        Args:
            stored_value: 存储的值（可能是加密的或明文的）
        
        Returns:
            明文凭证
        """
        if not stored_value:
            return stored_value
        
        # 如果不是加密值，直接返回（兼容旧数据）
        if not stored_value.startswith(self.ENCRYPTED_PREFIX):
            return stored_value
        
        if not self._available:
            logger.warning("[Credential] 检测到加密凭证但加密密钥未配置，无法解密")
            return stored_value
        
        try:
            from Crypto.Cipher import AES
            
            # 去掉前缀
            encoded = stored_value[len(self.ENCRYPTED_PREFIX):]
            encrypted_bytes = base64.b64decode(encoded)
            
            # 拆分: nonce(12) + ciphertext(N) + tag(16)
            nonce = encrypted_bytes[:12]
            tag = encrypted_bytes[-16:]
            ciphertext = encrypted_bytes[12:-16]
            
            # 解密
            cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            
            return plaintext.decode('utf-8')
            
        except ImportError:
            logger.warning("[Credential] pycryptodome 未安装，无法解密")
            return stored_value
        except Exception as e:
            logger.error(f"[Credential] 解密失败: {e}")
            return stored_value
    
    @staticmethod
    def generate_key() -> str:
        """生成一个新的加密密钥（hex格式，可设为环境变量）"""
        key = os.urandom(32)
        return key.hex()


# 单例
credential_service = CredentialService()
