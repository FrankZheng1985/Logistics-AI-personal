"""
企业微信回调API - 小析2（菠萝蜜/群情报员）
专门处理群消息监控和情报分析
"""
import asyncio
from collections import OrderedDict
from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.core.config import settings
from app.agents.analyst2 import analyst2_agent
from app.services.knowledge_service import knowledge_service
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/wechat/analyst2", tags=["企业微信-小析2"])

# 消息去重缓存
_processed_messages = OrderedDict()
_MAX_CACHE_SIZE = 1000


def is_message_processed(msg_id: str) -> bool:
    """检查消息是否已处理过"""
    return msg_id in _processed_messages


def mark_message_processed(msg_id: str):
    """标记消息为已处理"""
    _processed_messages[msg_id] = True
    while len(_processed_messages) > _MAX_CACHE_SIZE:
        _processed_messages.popitem(last=False)


class Analyst2WeChatCrypto:
    """小析2专用的企业微信消息加解密"""
    
    def __init__(self):
        import hashlib
        import base64
        import struct
        from Crypto.Cipher import AES
        
        self.token = settings.WECHAT_ANALYST2_TOKEN
        self.corp_id = settings.WECHAT_CORP_ID
        encoding_aes_key = settings.WECHAT_ANALYST2_ENCODING_AES_KEY
        
        if encoding_aes_key:
            self.aes_key = base64.b64decode(encoding_aes_key + "=")
        else:
            self.aes_key = None
    
    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.aes_key and self.corp_id)
    
    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证URL有效性并返回解密后的echostr"""
        import hashlib
        
        sort_list = sorted([self.token, timestamp, nonce, echostr])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        if sha1 != msg_signature:
            raise ValueError(f"签名验证失败")
        
        return self._decrypt(echostr)
    
    def _decrypt(self, encrypted: str) -> str:
        """解密消息"""
        import base64
        import struct
        from Crypto.Cipher import AES
        
        encrypted_bytes = base64.b64decode(encrypted)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        decrypted = cipher.decrypt(encrypted_bytes)
        
        pad = decrypted[-1]
        pad_len = pad if isinstance(pad, int) else ord(pad)
        content = decrypted[:-pad_len] if pad_len > 0 else decrypted
        
        msg_len = struct.unpack(">I", content[16:20])[0]
        msg = content[20:20+msg_len].decode("utf-8")
        
        return msg
    
    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypted_msg: str) -> str:
        """解密接收的消息"""
        import hashlib
        
        sort_list = sorted([self.token, timestamp, nonce, encrypted_msg])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        if sha1 != msg_signature:
            raise ValueError("消息签名验证失败")
        
        return self._decrypt(encrypted_msg)


# 创建加解密实例
analyst2_crypto = Analyst2WeChatCrypto()


@router.get("/callback")
async def verify_callback(
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="加密的随机字符串")
):
    """
    企业微信回调URL验证 - 小析2
    """
    try:
        logger.info(f"[小析2] 收到URL验证请求: timestamp={timestamp}")
        
        if not analyst2_crypto.is_configured:
            logger.error("[小析2] 企业微信配置未完成")
            raise HTTPException(status_code=500, detail="小析2企业微信配置未完成")
        
        decrypted = analyst2_crypto.verify_signature(msg_signature, timestamp, nonce, echostr)
        
        logger.info("[小析2] ✅ URL验证成功")
        return PlainTextResponse(content=decrypted)
        
    except Exception as e:
        logger.error(f"[小析2] ❌ URL验证失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/callback")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数")
):
    """
    接收企业微信消息 - 小析2
    小析2专注于群消息分析，不发送回复
    """
    try:
        import xml.etree.ElementTree as ET
        
        xml_data = await request.body()
        xml_str = xml_data.decode("utf-8")
        
        logger.info(f"[小析2] 收到消息: timestamp={timestamp}")
        
        if not analyst2_crypto.is_configured:
            logger.error("[小析2] 企业微信配置未完成")
            return PlainTextResponse(content="success")
        
        # 解析XML获取加密内容
        root = ET.fromstring(xml_str)
        encrypted = root.find("Encrypt").text
        
        # 解密消息
        decrypted_xml = analyst2_crypto.decrypt_message(msg_signature, timestamp, nonce, encrypted)
        
        # 解析解密后的XML
        msg_root = ET.fromstring(decrypted_xml)
        message = {
            "ToUserName": msg_root.find("ToUserName").text if msg_root.find("ToUserName") is not None else None,
            "FromUserName": msg_root.find("FromUserName").text if msg_root.find("FromUserName") is not None else None,
            "CreateTime": msg_root.find("CreateTime").text if msg_root.find("CreateTime") is not None else None,
            "MsgType": msg_root.find("MsgType").text if msg_root.find("MsgType") is not None else None,
            "Content": msg_root.find("Content").text if msg_root.find("Content") is not None else None,
            "MsgId": msg_root.find("MsgId").text if msg_root.find("MsgId") is not None else None,
            "AgentID": msg_root.find("AgentID").text if msg_root.find("AgentID") is not None else None,
            "ChatId": msg_root.find("ChatId").text if msg_root.find("ChatId") is not None else None,
        }
        
        logger.info(f"[小析2] 解析消息: {message}")
        
        # 处理文本消息
        if message.get("MsgType") == "text":
            msg_id = message.get("MsgId")
            content = message.get("Content")
            chat_id = message.get("ChatId")
            
            # 消息去重
            if msg_id and is_message_processed(msg_id):
                logger.info(f"[小析2] ⏭️ 跳过重复消息: MsgId={msg_id}")
                return PlainTextResponse(content="success")
            
            if msg_id:
                mark_message_processed(msg_id)
            
            # 判断是群消息还是私聊
            if chat_id:
                logger.info(f"[小析2] 📢 收到群消息: ChatId={chat_id}, 内容={content[:30]}...")
                background_tasks.add_task(process_group_message, message)
            else:
                logger.info(f"[小析2] 💬 收到私聊消息（忽略）: {content[:30]}...")
                # 小析2只处理群消息，私聊消息忽略
        
        return PlainTextResponse(content="success")
        
    except Exception as e:
        logger.error(f"[小析2] ❌ 处理消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return PlainTextResponse(content="success")


async def process_group_message(message: dict):
    """
    处理群消息 - 小析2分析并存入知识库
    """
    try:
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        import uuid
        
        chat_id = message.get("ChatId", "")
        user_id = message.get("FromUserName", "")
        content = message.get("Content", "")
        
        # 暂时使用简单的群名和用户名
        group_name = f"群_{chat_id[-6:]}" if chat_id else "未知群"
        sender_name = user_id
        
        logger.info(f"[小析2] 分析群消息: 群={group_name}, 发送者={sender_name}")
        
        # 调用小析2分析
        analysis = await analyst2_agent.process({
            "group_id": chat_id,
            "group_name": group_name,
            "sender_name": sender_name,
            "content": content,
            "message_type": "text"
        })
        
        # 保存到数据库
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO wechat_messages 
                    (group_id, sender_id, sender_name, content, is_valuable, 
                     analysis_result, created_at)
                    VALUES (:group_id, :sender_id, :sender_name, :content, :is_valuable,
                            :analysis_result::jsonb, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "group_id": chat_id,
                    "sender_id": user_id,
                    "sender_name": sender_name,
                    "content": content,
                    "is_valuable": analysis.get("is_valuable", False),
                    "analysis_result": analysis
                }
            )
            await db.commit()
        
        # 处理有价值信息
        if analysis.get("is_valuable"):
            category = analysis.get("category", "")
            summary = analysis.get("summary", "")
            
            logger.info(f"[小析2] ✅ 发现有价值信息: {category} - {summary}")
            
            # 记录任务完成
            await conversation_service.record_agent_task("analyst2", success=True)
            
            if category == "lead":
                await _create_lead(analysis, chat_id, content)
            elif category in ["intel", "knowledge"]:
                await _save_to_knowledge(analysis, group_name, content, category)
        else:
            logger.debug(f"[小析2] 消息无价值，已跳过: {analysis.get('reason', '')}")
                
    except Exception as e:
        logger.error(f"[小析2] 处理群消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def _create_lead(analysis: dict, group_id: str, content: str):
    """创建线索"""
    try:
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        import uuid
        
        key_info = analysis.get("key_info", {})
        contact_info = key_info.get("contact_info", {})
        
        async with AsyncSessionLocal() as db:
            lead_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO leads 
                    (id, source, source_url, title, content, contact_info, 
                     status, quality_score, created_at)
                    VALUES (:id, 'wechat_group', :source_url, :title, :content, 
                            :contact_info::jsonb, 'new', :quality_score, NOW())
                """),
                {
                    "id": lead_id,
                    "source_url": f"wechat://group/{group_id}",
                    "title": analysis.get("summary", "微信群线索")[:100],
                    "content": content,
                    "contact_info": contact_info or {},
                    "quality_score": analysis.get("confidence", 50)
                }
            )
            await db.commit()
            logger.info(f"[小析2] 已创建线索: {lead_id}")
    except Exception as e:
        logger.error(f"[小析2] 创建线索失败: {e}")


async def _save_to_knowledge(analysis: dict, group_name: str, content: str, category: str):
    """保存到知识库"""
    try:
        kb_category = "market_intel" if category == "intel" else "case"
        title_prefix = "[群情报]" if category == "intel" else "[群分享]"
        
        await knowledge_service.add_knowledge(
            category=kb_category,
            title=f"{title_prefix} {analysis.get('summary', '信息')[:50]}",
            content=content,
            summary=analysis.get("summary"),
            keywords=analysis.get("keyword_matches", []),
            source=f"企业微信群: {group_name}"
        )
        logger.info(f"[小析2] 已保存到知识库: {category}")
    except Exception as e:
        logger.error(f"[小析2] 保存知识库失败: {e}")
