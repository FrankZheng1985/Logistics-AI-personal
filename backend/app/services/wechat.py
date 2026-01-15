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
        try:
            # 解码base64
            encrypted_bytes = base64.b64decode(encrypted)
            logger.debug(f"Encrypted bytes length: {len(encrypted_bytes)}")
            
            # AES解密
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            decrypted = cipher.decrypt(encrypted_bytes)
            logger.debug(f"Decrypted bytes length: {len(decrypted)}")
            
            # PKCS7去除补位
            pad = decrypted[-1]
            if isinstance(pad, int):
                pad_len = pad
            else:
                pad_len = ord(pad)
            
            content = decrypted[:-pad_len] if pad_len > 0 else decrypted
            logger.debug(f"Content length after padding removal: {len(content)}")
            
            if len(content) < 20:
                raise ValueError(f"解密后内容太短: {len(content)} bytes")
            
            # 解析内容 (16字节随机 + 4字节msg长度 + msg + corp_id)
            msg_len = struct.unpack(">I", content[16:20])[0]
            logger.debug(f"Message length: {msg_len}")
            
            msg = content[20:20+msg_len].decode("utf-8")
            logger.debug(f"Decrypted message: {msg}")
            
            return msg
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
    
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
    
    @staticmethod
    def is_external_user(user_id: str) -> bool:
        """
        判断是否为外部联系人（客户）
        
        企业微信用户ID规则：
        - 内部员工：自定义的UserID，如 "Frank.Z"、"zhangsan"
        - 外部联系人：以 "wm" 或 "wo" 开头，如 "wmxxxxxxxxxxxxxx"
        """
        if not user_id:
            return False
        user_id_lower = user_id.lower()
        return user_id_lower.startswith("wm") or user_id_lower.startswith("wo")
    
    @staticmethod
    def is_internal_user(user_id: str) -> bool:
        """
        判断是否为内部员工
        """
        return not WeChatService.is_external_user(user_id)
    
    @staticmethod
    def get_user_type(user_id: str) -> str:
        """
        获取用户类型
        返回: "external" (外部客户) 或 "internal" (内部员工)
        """
        return "external" if WeChatService.is_external_user(user_id) else "internal"
    
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
        
        # 提取消息字段（包括群聊ID ChatId）
        result = {
            "ToUserName": msg_root.find("ToUserName").text if msg_root.find("ToUserName") is not None else None,
            "FromUserName": msg_root.find("FromUserName").text if msg_root.find("FromUserName") is not None else None,
            "CreateTime": msg_root.find("CreateTime").text if msg_root.find("CreateTime") is not None else None,
            "MsgType": msg_root.find("MsgType").text if msg_root.find("MsgType") is not None else None,
            "Content": msg_root.find("Content").text if msg_root.find("Content") is not None else None,
            "MsgId": msg_root.find("MsgId").text if msg_root.find("MsgId") is not None else None,
            "AgentID": msg_root.find("AgentID").text if msg_root.find("AgentID") is not None else None,
            # 群聊消息特有字段
            "ChatId": msg_root.find("ChatId").text if msg_root.find("ChatId") is not None else None,
        }
        
        # 记录是否为群消息
        if result.get("ChatId"):
            logger.info(f"📢 检测到群消息: ChatId={result['ChatId']}")
        
        return result
    
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
    
    # 群名称缓存
    _group_name_cache: Dict[str, str] = {}
    _user_name_cache: Dict[str, str] = {}
    
    async def get_group_name(self, chat_id: str) -> str:
        """
        获取企业微信群名称
        
        Args:
            chat_id: 群聊ID
            
        Returns:
            群名称，获取失败返回群ID
        """
        if not chat_id:
            return "未知群"
        
        # 检查缓存
        if chat_id in self._group_name_cache:
            return self._group_name_cache[chat_id]
        
        try:
            if not self.is_configured:
                return chat_id
            
            access_token = await self.get_access_token()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/appchat/get",
                    params={
                        "access_token": access_token,
                        "chatid": chat_id
                    }
                )
                data = response.json()
                
                if data.get("errcode") == 0:
                    chat_info = data.get("chat_info", {})
                    group_name = chat_info.get("name", chat_id)
                    self._group_name_cache[chat_id] = group_name
                    return group_name
                else:
                    logger.warning(f"获取群名称失败: {data}")
                    return chat_id
                    
        except Exception as e:
            logger.error(f"获取群名称异常: {e}")
            return chat_id
    
    async def get_user_name(self, user_id: str) -> str:
        """
        获取企业微信用户名称
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户名称，获取失败返回用户ID
        """
        if not user_id:
            return "未知用户"
        
        # 检查缓存
        if user_id in self._user_name_cache:
            return self._user_name_cache[user_id]
        
        try:
            if not self.is_configured:
                return user_id
            
            access_token = await self.get_access_token()
            
            # 判断是内部用户还是外部联系人
            if self.is_external_user(user_id):
                # 外部联系人
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/externalcontact/get",
                        params={
                            "access_token": access_token,
                            "external_userid": user_id
                        }
                    )
                    data = response.json()
                    
                    if data.get("errcode") == 0:
                        contact_info = data.get("external_contact", {})
                        user_name = contact_info.get("name", user_id)
                        self._user_name_cache[user_id] = user_name
                        return user_name
            else:
                # 内部员工
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/user/get",
                        params={
                            "access_token": access_token,
                            "userid": user_id
                        }
                    )
                    data = response.json()
                    
                    if data.get("errcode") == 0:
                        user_name = data.get("name", user_id)
                        self._user_name_cache[user_id] = user_name
                        return user_name
            
            return user_id
            
        except Exception as e:
            logger.error(f"获取用户名称异常: {e}")
            return user_id
    
    async def get_group_chat_list(self) -> list:
        """
        获取应用可见的群聊列表
        """
        try:
            if not self.is_configured:
                return []
            
            access_token = await self.get_access_token()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/appchat/get_list",
                    params={"access_token": access_token},
                    json={}
                )
                data = response.json()
                
                if data.get("errcode") == 0:
                    return data.get("chat_id_list", [])
                else:
                    logger.warning(f"获取群聊列表失败: {data}")
                    return []
                    
        except Exception as e:
            logger.error(f"获取群聊列表异常: {e}")
            return []


# 创建单例
wechat_service = WeChatService()
