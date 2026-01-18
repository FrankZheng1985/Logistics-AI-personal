"""
小助企业微信回调API
处理老板通过企业微信发送的消息
支持：文本消息、语音消息、文件消息（会议录音）
"""
import os
import xml.etree.ElementTree as ET
import hashlib
import base64
import struct
import time
from collections import OrderedDict
from typing import Optional
from Crypto.Cipher import AES

from fastapi import APIRouter, Request, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger
import httpx

from app.core.config import settings

router = APIRouter(prefix="/wechat_assistant", tags=["小助企业微信"])


# ==================== 配置 ====================

def get_config():
    """获取小助企业微信配置"""
    return {
        "corp_id": os.getenv("WECHAT_ASSISTANT_CORP_ID", ""),
        "agent_id": os.getenv("WECHAT_ASSISTANT_AGENT_ID", ""),
        "secret": os.getenv("WECHAT_ASSISTANT_SECRET", ""),
        "token": os.getenv("WECHAT_ASSISTANT_TOKEN", ""),
        "encoding_aes_key": os.getenv("WECHAT_ASSISTANT_ENCODING_AES_KEY", "")
    }


# ==================== 消息加解密 ====================

class WeChatCrypto:
    """企业微信消息加解密"""
    
    def __init__(self):
        config = get_config()
        self.token = config["token"]
        self.encoding_aes_key = config["encoding_aes_key"]
        self.corp_id = config["corp_id"]
        
        if self.encoding_aes_key:
            self.aes_key = base64.b64decode(self.encoding_aes_key + "=")
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证URL有效性"""
        # 验证签名
        sorted_params = sorted([self.token, timestamp, nonce, echostr])
        sign = hashlib.sha1("".join(sorted_params).encode()).hexdigest()
        
        if sign != msg_signature:
            raise ValueError("签名验证失败")
        
        # 解密echostr
        return self._decrypt(echostr)
    
    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypted: str) -> str:
        """解密消息"""
        # 验证签名
        sorted_params = sorted([self.token, timestamp, nonce, encrypted])
        sign = hashlib.sha1("".join(sorted_params).encode()).hexdigest()
        
        if sign != msg_signature:
            raise ValueError("消息签名验证失败")
        
        return self._decrypt(encrypted)
    
    def _decrypt(self, encrypted: str) -> str:
        """AES解密"""
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        decrypted = cipher.decrypt(base64.b64decode(encrypted))
        
        # 去除补位
        pad_len = decrypted[-1]
        content = decrypted[:-pad_len]
        
        # 解析内容
        msg_len = struct.unpack(">I", content[16:20])[0]
        msg = content[20:20+msg_len].decode("utf-8")
        
        return msg


def get_crypto() -> Optional[WeChatCrypto]:
    """获取加解密实例"""
    config = get_config()
    if config["token"] and config["encoding_aes_key"]:
        return WeChatCrypto()
    return None


# ==================== 消息去重 ====================

_processed_messages = OrderedDict()
_MAX_CACHE_SIZE = 1000


def is_message_processed(msg_id: str) -> bool:
    """检查消息是否已处理"""
    return msg_id in _processed_messages


def mark_message_processed(msg_id: str):
    """标记消息为已处理"""
    _processed_messages[msg_id] = time.time()
    # 清理过旧的缓存
    while len(_processed_messages) > _MAX_CACHE_SIZE:
        _processed_messages.popitem(last=False)


# ==================== Access Token ====================

_access_token_cache = {"token": None, "expires_at": 0}


async def get_access_token() -> str:
    """获取企业微信access_token"""
    global _access_token_cache
    
    # 检查缓存
    if _access_token_cache["token"] and time.time() < _access_token_cache["expires_at"]:
        return _access_token_cache["token"]
    
    config = get_config()
    if not config["corp_id"] or not config["secret"]:
        raise ValueError("企业微信配置不完整")
    
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {
        "corpid": config["corp_id"],
        "corpsecret": config["secret"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
    
    if data.get("errcode") != 0:
        raise ValueError(f"获取access_token失败: {data.get('errmsg')}")
    
    _access_token_cache["token"] = data["access_token"]
    _access_token_cache["expires_at"] = time.time() + data["expires_in"] - 300  # 提前5分钟刷新
    
    return _access_token_cache["token"]


# ==================== 发送消息 ====================

async def send_text_message(user_id: str, content: str):
    """发送文本消息给用户"""
    config = get_config()
    
    try:
        access_token = await get_access_token()
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        # 企业微信消息限制2048字符，超长需分段
        messages = []
        while len(content) > 2000:
            messages.append(content[:2000])
            content = content[2000:]
        messages.append(content)
        
        for msg in messages:
            data = {
                "touser": user_id,
                "msgtype": "text",
                "agentid": int(config["agent_id"]),
                "text": {"content": msg},
                "safe": 0
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data)
                result = response.json()
            
            if result.get("errcode") != 0:
                logger.error(f"[小助] 发送消息失败: {result}")
            else:
                logger.info(f"[小助] 消息已发送给 {user_id}")
                
    except Exception as e:
        logger.error(f"[小助] 发送消息异常: {e}")


async def download_media(media_id: str) -> Optional[bytes]:
    """下载媒体文件"""
    try:
        access_token = await get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.headers.get("content-type", "").startswith("application/json"):
                # 返回的是错误信息
                logger.error(f"[小助] 下载媒体失败: {response.text}")
                return None
            
            return response.content
            
    except Exception as e:
        logger.error(f"[小助] 下载媒体异常: {e}")
        return None


# ==================== 消息处理 ====================

async def process_text_message(user_id: str, content: str):
    """处理文本消息"""
    from app.agents.assistant_agent import assistant_agent
    
    logger.info(f"[小助] 处理文本消息: user={user_id}, content={content[:50]}...")
    
    try:
        # 调用小助处理消息
        result = await assistant_agent.process({
            "message": content,
            "user_id": user_id,
            "message_type": "text"
        })
        
        # 发送回复
        response = result.get("response", "抱歉，我没能理解你的意思。")
        await send_text_message(user_id, response)
        
    except Exception as e:
        logger.error(f"[小助] 处理消息失败: {e}")
        await send_text_message(user_id, "处理消息时出现了问题，请稍后再试。")


async def process_voice_message(user_id: str, media_id: str):
    """处理语音消息"""
    logger.info(f"[小助] 收到语音消息: user={user_id}, media_id={media_id}")
    
    # 下载语音文件
    voice_data = await download_media(media_id)
    if not voice_data:
        await send_text_message(user_id, "语音下载失败，请重新发送。")
        return
    
    # TODO: 短语音可以实时转文字
    # 目前先提示用户发送录音文件
    await send_text_message(user_id, "收到语音消息。如果是会议录音，请发送完整的录音文件。")


async def process_file_message(user_id: str, media_id: str, file_name: str):
    """处理文件消息（可能是会议录音）"""
    from app.agents.assistant_agent import assistant_agent
    from app.services.speech_recognition_service import speech_recognition_service
    
    logger.info(f"[小助] 收到文件: user={user_id}, file={file_name}")
    
    # 检查是否是音频文件
    audio_extensions = [".mp3", ".m4a", ".wav", ".amr", ".ogg", ".aac"]
    is_audio = any(file_name.lower().endswith(ext) for ext in audio_extensions)
    
    if not is_audio:
        await send_text_message(user_id, f"收到文件: {file_name}\n\n目前我只能处理音频文件（mp3/m4a/wav等）。")
        return
    
    # 通知用户开始处理
    await send_text_message(user_id, f"📼 收到会议录音: {file_name}\n\n正在处理中，转写完成后会自动发送会议纪要。\n⏱ 预计需要2-5分钟")
    
    try:
        # 下载音频文件
        audio_data = await download_media(media_id)
        if not audio_data:
            await send_text_message(user_id, "音频文件下载失败，请重新发送。")
            return
        
        # 保存到临时文件并上传到云存储
        # TODO: 上传到腾讯云COS
        # 目前先用本地文件
        import tempfile
        import os
        
        ext = os.path.splitext(file_name)[1] or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
        
        # 这里需要将文件上传到公网可访问的URL
        # 暂时跳过，提示用户
        await send_text_message(user_id, "音频处理功能需要配置腾讯云存储，请联系管理员完成配置。")
        
        # 清理临时文件
        os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"[小助] 处理音频文件失败: {e}")
        await send_text_message(user_id, "处理音频文件时出现问题，请稍后重试。")


# ==================== API路由 ====================

@router.get("/callback", summary="URL验证")
async def verify_callback(
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="加密的随机字符串")
):
    """
    企业微信URL验证
    配置回调URL时，企业微信会发送GET请求验证
    """
    try:
        crypto = get_crypto()
        if not crypto:
            logger.error("[小助] 企业微信配置不完整")
            raise ValueError("企业微信配置不完整")
        
        decrypted = crypto.verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info(f"[小助] URL验证成功")
        return PlainTextResponse(content=decrypted)
        
    except Exception as e:
        logger.error(f"[小助] URL验证失败: {e}")
        return PlainTextResponse(content="error", status_code=403)


@router.post("/callback", summary="接收消息")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数")
):
    """
    接收企业微信消息
    必须在3秒内返回success，消息在后台处理
    """
    try:
        crypto = get_crypto()
        if not crypto:
            logger.error("[小助] 企业微信配置不完整")
            return PlainTextResponse(content="success")
        
        # 获取并解析消息
        xml_data = await request.body()
        xml_str = xml_data.decode("utf-8")
        
        # 解析XML获取加密内容
        root = ET.fromstring(xml_str)
        encrypted = root.find("Encrypt").text
        
        # 解密消息
        decrypted_xml = crypto.decrypt_message(msg_signature, timestamp, nonce, encrypted)
        
        # 解析解密后的消息
        msg_root = ET.fromstring(decrypted_xml)
        
        message = {
            "FromUserName": msg_root.find("FromUserName").text if msg_root.find("FromUserName") is not None else None,
            "CreateTime": msg_root.find("CreateTime").text if msg_root.find("CreateTime") is not None else None,
            "MsgType": msg_root.find("MsgType").text if msg_root.find("MsgType") is not None else None,
            "Content": msg_root.find("Content").text if msg_root.find("Content") is not None else None,
            "MsgId": msg_root.find("MsgId").text if msg_root.find("MsgId") is not None else None,
            "MediaId": msg_root.find("MediaId").text if msg_root.find("MediaId") is not None else None,
            "FileName": msg_root.find("FileName").text if msg_root.find("FileName") is not None else None,
        }
        
        logger.info(f"[小助] 收到消息: {message}")
        
        # 消息去重
        msg_id = message.get("MsgId")
        if msg_id and is_message_processed(msg_id):
            logger.info(f"[小助] 跳过重复消息: {msg_id}")
            return PlainTextResponse(content="success")
        
        if msg_id:
            mark_message_processed(msg_id)
        
        user_id = message.get("FromUserName")
        msg_type = message.get("MsgType")
        
        # 根据消息类型处理
        if msg_type == "text":
            content = message.get("Content", "")
            background_tasks.add_task(process_text_message, user_id, content)
            
        elif msg_type == "voice":
            media_id = message.get("MediaId")
            if media_id:
                background_tasks.add_task(process_voice_message, user_id, media_id)
                
        elif msg_type == "file":
            media_id = message.get("MediaId")
            file_name = message.get("FileName", "unknown")
            if media_id:
                background_tasks.add_task(process_file_message, user_id, media_id, file_name)
        
        # 立即返回success
        return PlainTextResponse(content="success")
        
    except Exception as e:
        logger.error(f"[小助] 处理消息异常: {e}")
        return PlainTextResponse(content="success")


# ==================== 主动推送API ====================

@router.post("/send", summary="主动发送消息")
async def send_message_api(
    user_id: str = Query(..., description="用户ID"),
    content: str = Query(..., description="消息内容")
):
    """主动发送消息给用户（供内部调用）"""
    await send_text_message(user_id, content)
    return {"success": True, "message": "消息已发送"}


@router.get("/config-status", summary="检查配置状态")
async def check_config_status():
    """检查企业微信配置状态"""
    config = get_config()
    
    return {
        "configured": bool(config["corp_id"] and config["secret"]),
        "corp_id": bool(config["corp_id"]),
        "agent_id": bool(config["agent_id"]),
        "secret": bool(config["secret"]),
        "token": bool(config["token"]),
        "encoding_aes_key": bool(config["encoding_aes_key"]),
        "message": "配置完整" if all([config["corp_id"], config["agent_id"], config["secret"], config["token"], config["encoding_aes_key"]]) else "配置不完整，请设置环境变量"
    }
