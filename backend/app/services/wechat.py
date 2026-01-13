"""
企业微信服务
"""
from typing import Dict, Any, Optional
import httpx
import hashlib
import base64
import struct
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from loguru import logger

from app.core.config import settings


class WeChatCrypto:
    """企业微信消息加解密"""
    
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token = token
        self.corp_id = corp_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
    
    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证URL有效性并返回解密后的echostr"""
        # 验证签名
        sort_list = sorted([self.token, timestamp, nonce, echostr])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        logger.debug(f"Token: {self.token}")
        logger.debug(f"Sorted list: {sort_list}")
        logger.debug(f"Calculated SHA1: {sha1}")
        logger.debug(f"Expected signature: {msg_signature}")
        
        if sha1 != msg_signature:
            raise ValueError(f"签名验证失败: 计算值={sha1}, 期望值={msg_signature}")
        
        # 解密echostr
        return self._decrypt(echostr)
    
    def _decrypt(self, encrypted: str) -> str:
        """解密消息"""
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        decrypted = cipher.decrypt(base64.b64decode(encrypted))
        
        # 去除补位
        pad = decrypted[-1]
        content = decrypted[:-pad]
        
        # 解析内容 (16字节随机 + 4字节msg长度 + msg + corp_id)
        msg_len = struct.unpack(">I", content[16:20])[0]
        msg = content[20:20+msg_len].decode("utf-8")
        
        return msg
    
    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypted_msg: str) -> str:
        """解密接收的消息"""
        # 验证签名
        sort_list = sorted([self.token, timestamp, nonce, encrypted_msg])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        if sha1 != msg_signature:
            raise ValueError("消息签名验证失败")
        
        return self._decrypt(encrypted_msg)


class WeChatService:
    """企业微信服务"""
    
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.agent_id = settings.WECHAT_AGENT_ID
        self.secret = settings.WECHAT_SECRET
        self.token = settings.WECHAT_TOKEN
        self.encoding_aes_key = settings.WECHAT_ENCODING_AES_KEY
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"
        self._access_token: Optional[str] = None
        self._crypto: Optional[WeChatCrypto] = None
    
    @property
    def crypto(self) -> WeChatCrypto:
        """获取加解密实例"""
        if self._crypto is None and self.token and self.encoding_aes_key and self.corp_id:
            self._crypto = WeChatCrypto(self.token, self.encoding_aes_key, self.corp_id)
        return self._crypto
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.corp_id and self.secret)
    
    @property
    def is_callback_configured(self) -> bool:
        """检查回调是否已配置"""
        return bool(self.token and self.encoding_aes_key and self.corp_id)
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证回调URL"""
        if not self.is_callback_configured:
            raise ValueError("企业微信回调未配置")
        return self.crypto.verify_signature(msg_signature, timestamp, nonce, echostr)
    
    def parse_message(self, msg_signature: str, timestamp: str, nonce: str, xml_data: str) -> Dict[str, Any]:
        """解析接收的消息"""
        if not self.is_callback_configured:
            raise ValueError("企业微信回调未配置")
        
        # 解析XML获取加密内容
        root = ET.fromstring(xml_data)
        encrypted = root.find("Encrypt").text
        
        # 解密消息
        decrypted_xml = self.crypto.decrypt_message(msg_signature, timestamp, nonce, encrypted)
        
        # 解析解密后的XML
        msg_root = ET.fromstring(decrypted_xml)
        return {
            "ToUserName": msg_root.find("ToUserName").text if msg_root.find("ToUserName") is not None else None,
            "FromUserName": msg_root.find("FromUserName").text if msg_root.find("FromUserName") is not None else None,
            "CreateTime": msg_root.find("CreateTime").text if msg_root.find("CreateTime") is not None else None,
            "MsgType": msg_root.find("MsgType").text if msg_root.find("MsgType") is not None else None,
            "Content": msg_root.find("Content").text if msg_root.find("Content") is not None else None,
            "MsgId": msg_root.find("MsgId").text if msg_root.find("MsgId") is not None else None,
            "AgentID": msg_root.find("AgentID").text if msg_root.find("AgentID") is not None else None,
        }
    
    async def get_access_token(self) -> str:
        """获取access_token"""
        if not self.is_configured:
            raise ValueError("企业微信未配置")
        
        # TODO: 实现token缓存
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/gettoken",
                params={
                    "corpid": self.corp_id,
                    "corpsecret": self.secret
                }
            )
            data = response.json()
            
            if data.get("errcode") == 0:
                self._access_token = data.get("access_token")
                return self._access_token
            else:
                raise Exception(f"获取access_token失败: {data}")
    
    async def send_text_message(
        self,
        user_ids: list[str],
        content: str
    ) -> Dict[str, Any]:
        """发送文本消息"""
        if not self.is_configured:
            return {"status": "error", "message": "企业微信未配置"}
        
        access_token = await self.get_access_token()
        
        payload = {
            "touser": "|".join(user_ids),
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/message/send",
                params={"access_token": access_token},
                json=payload
            )
            data = response.json()
            
            if data.get("errcode") == 0:
                logger.info(f"企业微信消息发送成功")
                return {"status": "sent", "data": data}
            else:
                logger.error(f"企业微信消息发送失败: {data}")
                return {"status": "error", "data": data}
    
    async def send_markdown_message(
        self,
        user_ids: list[str],
        content: str
    ) -> Dict[str, Any]:
        """发送Markdown消息"""
        if not self.is_configured:
            return {"status": "error", "message": "企业微信未配置"}
        
        access_token = await self.get_access_token()
        
        payload = {
            "touser": "|".join(user_ids),
            "msgtype": "markdown",
            "agentid": self.agent_id,
            "markdown": {
                "content": content
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/message/send",
                params={"access_token": access_token},
                json=payload
            )
            return response.json()


# 创建单例
wechat_service = WeChatService()
