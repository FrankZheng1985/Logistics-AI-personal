"""
小欧间谍 - 企业微信消息回调接口
接收用户发来的消息，执行相应的监控任务
"""
import hashlib
import base64
import struct
import xml.etree.ElementTree as ET
from typing import Optional
from fastapi import APIRouter, Request, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger
from Crypto.Cipher import AES

from app.core.config import settings


router = APIRouter()


class EUMonitorWeChatCrypto:
    """小欧间谍企业微信消息加解密"""
    
    def __init__(self):
        self.token = getattr(settings, 'WECHAT_EU_MONITOR_TOKEN', '')
        self.encoding_aes_key = getattr(settings, 'WECHAT_EU_MONITOR_ENCODING_AES_KEY', '')
        self.corp_id = settings.WECHAT_CORP_ID or ''
        
        if self.encoding_aes_key:
            self.aes_key = base64.b64decode(self.encoding_aes_key + "=")
        else:
            self.aes_key = None
    
    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证URL有效性并返回解密后的echostr"""
        if not self.token:
            raise ValueError("Token未配置")
        
        # 验证签名
        sort_list = sorted([self.token, timestamp, nonce, echostr])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        logger.debug(f"[小欧间谍] 签名验证: calculated={sha1}, expected={msg_signature}")
        
        if sha1 != msg_signature:
            raise ValueError(f"签名验证失败")
        
        # 解密echostr
        return self._decrypt(echostr)
    
    def _decrypt(self, encrypted: str) -> str:
        """解密消息"""
        if not self.aes_key:
            raise ValueError("EncodingAESKey未配置")
        
        try:
            encrypted_bytes = base64.b64decode(encrypted)
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            decrypted = cipher.decrypt(encrypted_bytes)
            
            # PKCS7去除补位
            pad = decrypted[-1]
            pad_len = pad if isinstance(pad, int) else ord(pad)
            content = decrypted[:-pad_len] if pad_len > 0 else decrypted
            
            if len(content) < 20:
                raise ValueError(f"解密后内容太短")
            
            # 解析内容
            msg_len = struct.unpack(">I", content[16:20])[0]
            msg = content[20:20+msg_len].decode("utf-8")
            
            return msg
        except Exception as e:
            logger.error(f"[小欧间谍] 解密失败: {e}")
            raise
    
    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypted_msg: str) -> str:
        """解密接收的消息"""
        if not self.token:
            raise ValueError("Token未配置")
        
        sort_list = sorted([self.token, timestamp, nonce, encrypted_msg])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        if sha1 != msg_signature:
            raise ValueError("消息签名验证失败")
        
        return self._decrypt(encrypted_msg)


# 创建加解密实例
eu_monitor_crypto = EUMonitorWeChatCrypto()


@router.get("/callback")
async def verify_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    验证企业微信回调URL
    企业微信会发送GET请求验证URL有效性
    """
    logger.info(f"[小欧间谍] 收到URL验证请求: timestamp={timestamp}, nonce={nonce}")
    
    try:
        # 重新初始化crypto以获取最新配置
        crypto = EUMonitorWeChatCrypto()
        decrypted = crypto.verify_signature(msg_signature, timestamp, nonce, echostr)
        logger.info(f"[小欧间谍] URL验证成功")
        return PlainTextResponse(content=decrypted)
    except Exception as e:
        logger.error(f"[小欧间谍] URL验证失败: {e}")
        return PlainTextResponse(content="error", status_code=403)


@router.post("/callback")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    """
    接收企业微信消息
    """
    try:
        body = await request.body()
        xml_data = body.decode("utf-8")
        logger.info(f"[小欧间谍] 收到消息回调")
        
        # 解析XML获取加密内容
        root = ET.fromstring(xml_data)
        encrypted = root.find("Encrypt").text
        
        # 解密消息
        crypto = EUMonitorWeChatCrypto()
        decrypted_xml = crypto.decrypt_message(msg_signature, timestamp, nonce, encrypted)
        
        # 解析解密后的XML
        msg_root = ET.fromstring(decrypted_xml)
        
        from_user = msg_root.find("FromUserName").text if msg_root.find("FromUserName") is not None else None
        msg_type = msg_root.find("MsgType").text if msg_root.find("MsgType") is not None else None
        content = msg_root.find("Content").text if msg_root.find("Content") is not None else None
        
        logger.info(f"[小欧间谍] 收到消息: from={from_user}, type={msg_type}, content={content}")
        
        # 处理文本消息
        if msg_type == "text" and content:
            # 在后台处理消息，避免超时
            background_tasks.add_task(process_user_message, from_user, content)
        
        # 返回空字符串表示成功
        return PlainTextResponse(content="")
        
    except Exception as e:
        logger.error(f"[小欧间谍] 消息处理失败: {e}")
        return PlainTextResponse(content="")


async def process_user_message(user_id: str, message: str):
    """
    处理用户发来的消息
    """
    try:
        from app.agents.eu_customs_monitor import eu_customs_monitor_agent
        
        logger.info(f"[小欧间谍] 开始处理用户消息: {message}")
        
        # 解析用户指令
        message_lower = message.lower().strip()
        
        # 发送处理中提示
        await send_reply(user_id, "🕵️ 收到！小欧间谍正在为您执行任务...")
        
        result = None
        
        # 根据关键词执行不同任务
        if any(kw in message_lower for kw in ["采集", "新闻", "监控", "抓取", "获取"]):
            # 执行新闻采集
            result = await eu_customs_monitor_agent.process({"action": "monitor", "max_results": 20})
            
            if result.get("error"):
                reply = f"❌ 采集失败: {result.get('error')}"
            else:
                important_count = result.get("important_count", 0)
                total_count = result.get("total_news", 0)
                sources = ', '.join(result.get('sources_searched', []))
                
                # 先发送采集结果概要
                summary = f"""✅ 采集完成！

📊 本次采集结果
- 总新闻数: {total_count} 条
- 重要新闻: {important_count} 条
- 来源: {sources}"""
                
                await send_reply(user_id, summary)
                
                # 如果有重要新闻，分批发送TOP10
                important_news = result.get("important_news", [])
                if important_news:
                    # 发送TOP10重要新闻
                    await send_top_news(user_id, important_news[:10])
                
                return  # 已经发送了回复，直接返回
        
        elif any(kw in message_lower for kw in ["统计", "汇总", "报告", "今日", "本周"]):
            # 获取统计信息
            result = await eu_customs_monitor_agent.process({"action": "get_stats"})
            
            today = result.get("today", {})
            week = result.get("this_week", {})
            
            reply = f"""📊 **欧洲海关情报统计**

**今日**
- 采集新闻: {today.get('total', 0)} 条
- 重要新闻: {today.get('important', 0)} 条
- 平均重要度: {today.get('avg_score', 0)} 分

**本周**
- 采集新闻: {week.get('total', 0)} 条
- 重要新闻: {week.get('important', 0)} 条"""
        
        elif any(kw in message_lower for kw in ["帮助", "help", "功能", "指令", "命令"]):
            reply = """🕵️ **小欧间谍使用指南**

您可以发送以下指令：

📰 **采集新闻**
发送: "采集新闻" / "开始监控" / "获取最新"

📊 **查看统计**
发送: "今日统计" / "本周汇总" / "查看报告"

🔍 **搜索特定内容**
发送: "搜索 反倾销" / "查询 关税调整"

⏰ **自动任务**
每天早上6点自动采集，重要新闻即时推送"""
        
        elif "搜索" in message_lower or "查询" in message_lower:
            # 提取搜索关键词
            keyword = message.replace("搜索", "").replace("查询", "").strip()
            if keyword:
                reply = f"🔍 正在搜索「{keyword}」相关新闻...\n\n（功能开发中，敬请期待）"
            else:
                reply = "请输入搜索关键词，例如：搜索 反倾销"
        
        else:
            reply = """🕵️ 小欧间谍在线！

我可以帮您：
- 采集欧洲海关最新新闻
- 查看情报统计汇总
- 搜索特定政策信息

发送「帮助」查看完整指令"""
        
        # 发送回复
        await send_reply(user_id, reply)
        
    except Exception as e:
        logger.error(f"[小欧间谍] 处理消息异常: {e}")
        await send_reply(user_id, f"❌ 处理失败: {str(e)}")


async def send_top_news(user_id: str, news_list: list):
    """
    发送TOP重要新闻列表（分批发送避免消息过长）
    """
    if not news_list:
        return
    
    # 每5条新闻一批
    batch_size = 5
    for batch_idx in range(0, len(news_list), batch_size):
        batch = news_list[batch_idx:batch_idx + batch_size]
        start_num = batch_idx + 1
        
        if batch_idx == 0:
            msg = f"🔔 TOP{len(news_list)}重要新闻：\n\n"
        else:
            msg = ""
        
        for i, news in enumerate(batch, start=start_num):
            urgency = news.get("urgency", "一般")
            emoji = "🚨" if urgency == "紧急" else "⚠️" if urgency == "重要" else "📌"
            score = news.get("importance_score", 0)
            news_type = news.get("news_type", "")
            title = news.get("title_cn", news.get("title", ""))[:40]
            summary = news.get("summary_cn", "")[:60]
            suggestion = news.get("business_suggestion", "")[:40]
            
            msg += f"""{emoji} {i}. {title}
类型: {news_type} | {score}分
摘要: {summary}...
建议: {suggestion}

"""
        
        await send_reply(user_id, msg.strip())
        
        # 批次之间稍微延迟
        if batch_idx + batch_size < len(news_list):
            import asyncio
            await asyncio.sleep(0.5)


async def send_reply(user_id: str, content: str):
    """
    通过小欧间谍应用发送回复消息
    """
    try:
        import httpx
        
        corp_id = settings.WECHAT_CORP_ID
        agent_id = getattr(settings, 'WECHAT_EU_MONITOR_AGENT_ID', None)
        secret = getattr(settings, 'WECHAT_EU_MONITOR_SECRET', None)
        
        if not all([corp_id, agent_id, secret]):
            logger.error("[小欧间谍] 企业微信配置不完整")
            return
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 获取token
            token_resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={"corpid": corp_id, "corpsecret": secret}
            )
            token_data = token_resp.json()
            
            if token_data.get("errcode") != 0:
                logger.error(f"[小欧间谍] 获取token失败: {token_data}")
                return
            
            access_token = token_data.get("access_token")
            
            # 发送文本消息
            send_resp = await client.post(
                f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}",
                json={
                    "touser": user_id,
                    "msgtype": "text",
                    "agentid": int(agent_id),
                    "text": {"content": content}
                }
            )
            send_data = send_resp.json()
            
            if send_data.get("errcode") != 0:
                logger.error(f"[小欧间谍] 发送回复失败: {send_data}")
            else:
                logger.info(f"[小欧间谍] 回复已发送给 {user_id}")
                
    except Exception as e:
        logger.error(f"[小欧间谍] 发送回复异常: {e}")
