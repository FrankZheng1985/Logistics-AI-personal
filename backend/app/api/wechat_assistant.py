"""
Clauwdbot 企业微信回调API（由小助升级）
处理老板通过企业微信发送的消息
支持：文本消息、语音消息、文件消息（会议录音）
AI中心超级助理 - 最高权限执行官
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

router = APIRouter(prefix="/wechat_assistant", tags=["Clauwdbot企业微信"])


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
        
        # 企业微信消息限制2048字符，超长截断（只发一条）
        if len(content) > 2000:
            content = content[:1950] + "\n\n...(内容已精简)"
        
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": int(config["agent_id"]),
            "text": {"content": content},
            "safe": 0
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            result = response.json()
        
        if result.get("errcode") != 0:
            logger.error(f"[Clauwdbot] 发送消息失败: {result}")
        else:
            logger.info(f"[Clauwdbot] 消息已发送给 {user_id}")
                
    except Exception as e:
        logger.error(f"[Clauwdbot] 发送消息异常: {e}")


async def upload_media(filepath: str, media_type: str = "file") -> Optional[str]:
    """上传临时素材到企业微信，返回 media_id"""
    import os
    
    if not os.path.exists(filepath):
        logger.error(f"[Clauwdbot] 文件上传失败，文件不存在: {filepath}")
        return None
    
    try:
        access_token = await get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type={media_type}"
        
        filename = os.path.basename(filepath)
        logger.info(f"[Clauwdbot] 正在上传文件到企业微信: {filename}, url: {url}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(filepath, "rb") as f:
                files = {"media": (filename, f, "application/octet-stream")}
                response = await client.post(url, files=files)
                result = response.json()
        
        if result.get("errcode") != 0:
            logger.error(f"[Clauwdbot] 企业微信上传接口返回错误: {result}")
            return None
        
        media_id = result.get("media_id")
        logger.info(f"[Clauwdbot] 文件上传成功，media_id: {media_id}")
        return media_id
        
    except Exception as e:
        logger.error(f"[Clauwdbot] 上传文件过程中出现异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def send_file_message(user_id: str, filepath: str):
    """发送文件消息给用户（上传+发送）"""
    logger.info(f"[Clauwdbot] 开始执行发送文件流程: {filepath} -> {user_id}")
    config = get_config()
    
    # 1. 上传文件获取 media_id
    media_id = await upload_media(filepath)
    if not media_id:
        logger.error(f"[Clauwdbot] 发送文件失败: 无法获取 media_id")
        await send_text_message(user_id, "文件上传失败，请检查服务器日志。")
        return
    
    # 2. 发送文件消息
    try:
        access_token = await get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        data = {
            "touser": user_id,
            "msgtype": "file",
            "agentid": int(config["agent_id"]),
            "file": {"media_id": media_id},
            "safe": 0
        }
        
        logger.info(f"[Clauwdbot] 正在发送文件消息: {media_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            result = response.json()
        
        if result.get("errcode") != 0:
            logger.error(f"[Clauwdbot] 企业微信消息发送接口返回错误: {result}")
            await send_text_message(user_id, f"文件发送失败，微信返回错误: {result.get('errmsg')}")
        else:
            logger.info(f"[Clauwdbot] 文件消息已成功发送给 {user_id}")
                
    except Exception as e:
        logger.error(f"[Clauwdbot] 发送文件消息过程中出现异常: {str(e)}")
        await send_text_message(user_id, "文件发送过程中出现系统异常。")


async def download_media(media_id: str) -> Optional[bytes]:
    """下载媒体文件"""
    try:
        access_token = await get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            if response.headers.get("content-type", "").startswith("application/json"):
                # 返回的是错误信息
                logger.error(f"[Clauwdbot] 下载媒体失败: {response.text}")
                return None
            
            return response.content
            
    except Exception as e:
        logger.error(f"[Clauwdbot] 下载媒体异常: {e}")
        return None


# ==================== 消息处理 ====================

async def process_text_message(user_id: str, content: str):
    """处理文本消息 — Maria ReAct 引擎"""
    from app.agents.assistant_agent import clauwdbot_agent
    
    logger.info(f"[Maria] 处理文本消息: user={user_id}, content={content[:50]}...")
    
    # ===== 0. 判断是否需要发送"处理中"提示 =====
    # 复杂任务关键词（可能需要较长处理时间）
    heavy_keywords = [
        "notion", "Notion", "方案", "计划", "报告", "文档", "PPT", "ppt",
        "Word", "word", "搜索", "查找", "分析", "升级", "日报", "周报",
        "邮件", "同步", "生成", "写一", "做一", "帮我写", "帮我做",
    ]
    needs_thinking_hint = any(kw in content for kw in heavy_keywords)
    
    if needs_thinking_hint:
        # 先给老板一个即时反馈，让他知道 Maria 在干活
        thinking_hints = [
            "收到，我来处理一下...",
            "好的，正在处理中...",
            "收到，让我想想怎么搞...",
        ]
        import random
        await send_text_message(user_id, random.choice(thinking_hints))
    
    try:
        # ===== 1. 调用 Maria ReAct 引擎 =====
        result = await clauwdbot_agent.process({
            "message": content,
            "user_id": user_id,
            "message_type": "text"
        })
        
        # ===== 2. 发送文本回复 =====
        response = result.get("response", "")
        if response:
            await send_text_message(user_id, response)
        
        # ===== 3. 发送文件（如有）=====
        filepath = result.get("filepath") or result.get("file")
        if filepath:
            logger.info(f"[Maria] 发送文件: {filepath}")
            await send_file_message(user_id, filepath)
        
        # ===== 4. 异步执行的后台任务（如任务分配）=====
        if result.get("async_execute") and result.get("task_id"):
            import asyncio
            asyncio.create_task(
                _execute_dispatched_task(user_id, result)
            )
        
    except Exception as e:
        logger.error(f"[Maria] 处理消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 详细错误信息
        error_msg = str(e)
        user_friendly = f"老板，你让我「{content[:30]}」的时候系统出了问题。\n\n错误：{error_msg[:150]}\n\n我已记录，你可以让我再试一次。"
        await send_text_message(user_id, user_friendly)


async def _execute_dispatched_task(user_id: str, dispatch_result: dict):
    """后台执行Clauwdbot分配的任务，结果翻译成人话再发"""
    from app.agents.base import AgentRegistry
    from app.models.conversation import AgentType
    
    try:
        target_agent_key = dispatch_result.get("target_agent")
        task_id = dispatch_result.get("task_id")
        
        if not target_agent_key:
            return
        
        from app.agents.assistant_agent import clauwdbot_agent
        agent_info = clauwdbot_agent.AGENT_INFO.get(target_agent_key)
        if not agent_info:
            return
        
        agent = AgentRegistry.get(agent_info["type"])
        if not agent:
            await send_text_message(user_id, f"{agent_info['name']}现在不在线，任务没法执行。")
            return
        
        # 提取任务描述
        task_desc = dispatch_result.get("response", "").split("📋 任务: ")[-1].split("\n")[0] if "📋 任务:" in dispatch_result.get("response", "") else ""
        
        if not task_desc:
            return
        
        logger.info(f"[Clauwdbot] 后台执行任务: {agent_info['name']} -> {task_desc[:50]}")
        
        raw_response = await agent.chat(task_desc)
        
        # 更新任务状态
        if task_id:
            from app.models.database import AsyncSessionLocal
            from sqlalchemy import text
            import json
            
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE ai_tasks SET status = 'completed', 
                        output_data = :output, completed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": task_id, "output": json.dumps({"response": raw_response[:2000]}, ensure_ascii=False)}
                )
                await db.commit()
        
        # ===== 关键：把原始结果翻译成人话 =====
        from app.core.llm import chat_completion
        
        summary_prompt = f"""你是郑总的私人助理。{agent_info['name']}刚完成了一个任务，以下是原始结果。
请用口语把结果简单告诉郑总，像微信聊天一样。不要贴JSON、不要贴代码、不要用markdown。
只说关键信息，3-5句话。

任务描述：{task_desc[:200]}
执行者：{agent_info['name']}
原始结果：{raw_response[:1500]}"""
        
        try:
            human_summary = await chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=500,
                temperature=0.7
            )
        except Exception:
            # LLM 翻译失败就用截断的原文
            human_summary = raw_response[:500] if len(raw_response) <= 500 else raw_response[:500] + "..."
        
        await send_text_message(user_id, human_summary)
        
    except Exception as e:
        logger.error(f"[Clauwdbot] 后台任务执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await send_text_message(user_id, f"任务执行遇到了点问题：{str(e)[:100]}")


async def process_voice_message(user_id: str, media_id: str):
    """处理语音消息"""
    logger.info(f"[Clauwdbot] 收到语音消息: user={user_id}, media_id={media_id}")
    
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
    from app.agents.assistant_agent import clauwdbot_agent
    from app.services.speech_recognition_service import speech_recognition_service
    from app.services.cos_storage_service import cos_storage_service
    
    logger.info(f"[Clauwdbot] 收到文件: user={user_id}, file={file_name}")
    
    # 检查是否是音频文件
    audio_extensions = [".mp3", ".m4a", ".wav", ".amr", ".ogg", ".aac"]
    is_audio = any(file_name.lower().endswith(ext) for ext in audio_extensions)
    
    if not is_audio:
        await send_text_message(user_id, f"收到文件: {file_name}\n\n目前我只能处理音频文件（mp3/m4a/wav等）。")
        return
    
    # 检查云存储和语音识别是否已配置
    if not cos_storage_service.is_configured:
        await send_text_message(user_id, f"📼 收到录音: {file_name}\n\n⚠️ 云存储未配置，请联系管理员配置腾讯云COS。")
        return
    
    if not speech_recognition_service.is_configured():
        await send_text_message(user_id, f"📼 收到录音: {file_name}\n\n⚠️ 语音识别未配置，请联系管理员配置腾讯云ASR。")
        return
    
    # 通知用户开始处理
    await send_text_message(user_id, f"📼 收到会议录音: {file_name}\n\n正在处理中，转写完成后会自动发送会议纪要。\n⏱ 预计需要2-5分钟")
    
    try:
        # 1. 下载音频文件
        logger.info(f"[Clauwdbot] 下载音频文件: {media_id}")
        audio_data = await download_media(media_id)
        if not audio_data:
            await send_text_message(user_id, "音频文件下载失败，请重新发送。")
            return
        
        logger.info(f"[Clauwdbot] 音频文件下载成功: {len(audio_data)} bytes")
        
        # 2. 上传到腾讯云COS
        logger.info(f"[Clauwdbot] 上传到COS...")
        success, result = await cos_storage_service.upload_bytes(
            data=audio_data,
            filename=file_name,
            folder="meeting_audio"
        )
        
        if not success:
            logger.error(f"[Clauwdbot] COS上传失败: {result}")
            await send_text_message(user_id, f"音频上传失败: {result}")
            return
        
        audio_url = result
        logger.info(f"[Clauwdbot] COS上传成功: {audio_url}")
        
        # 3. 创建会议记录
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO meeting_records (audio_file_url, transcription_status, created_by)
                    VALUES (:url, 'processing', :user_id)
                    RETURNING id
                """),
                {"url": audio_url, "user_id": user_id}
            )
            meeting_id = str(result.fetchone()[0])
            await db.commit()
        
        logger.info(f"[Clauwdbot] 创建会议记录: {meeting_id}")
        
        # 4. 调用语音识别服务
        ext = os.path.splitext(file_name)[1].lower().lstrip('.')
        audio_format = ext if ext in ['mp3', 'm4a', 'wav', 'amr', 'ogg'] else 'mp3'
        
        transcribe_result = await speech_recognition_service.transcribe_audio(
            audio_url=audio_url,
            meeting_id=meeting_id,
            audio_format=audio_format
        )
        
        if not transcribe_result.get("success"):
            error_msg = transcribe_result.get("error", "未知错误")
            logger.error(f"[Clauwdbot] 语音识别任务提交失败: {error_msg}")
            await send_text_message(user_id, f"语音识别启动失败: {error_msg}")
            return
        
        logger.info(f"[Clauwdbot] 语音识别任务已提交: {transcribe_result.get('tencent_task_id')}")
        
        # 5. 启动后台任务等待结果并发送给用户
        import asyncio
        asyncio.create_task(
            _wait_and_send_meeting_summary(user_id, meeting_id, transcribe_result.get('task_id'))
        )
        
    except Exception as e:
        logger.error(f"[Clauwdbot] 处理音频文件失败: {e}")
        await send_text_message(user_id, f"处理音频文件时出现问题：{str(e)}")


async def _wait_and_send_meeting_summary(user_id: str, meeting_id: str, task_id: str):
    """等待转写完成后发送会议纪要给用户"""
    import asyncio
    from app.models.database import AsyncSessionLocal
    from sqlalchemy import text
    
    max_wait_time = 600  # 最长等待10分钟
    poll_interval = 10  # 每10秒检查一次
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        await asyncio.sleep(poll_interval)
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT transcription_status, summary, raw_transcription, 
                               content_structured, action_items
                        FROM meeting_records
                        WHERE id = :meeting_id
                    """),
                    {"meeting_id": meeting_id}
                )
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"[Clauwdbot] 会议记录不存在: {meeting_id}")
                    return
                
                status = row[0]
                
                if status == 'completed':
                    # 转写完成，发送会议纪要
                    summary = row[1] or "无摘要"
                    transcription = row[2] or ""
                    
                    # 格式化会议纪要
                    lines = ["📋 会议纪要", "━" * 18]
                    lines.append(f"\n📝 摘要: {summary}")
                    
                    # 解析待办事项
                    try:
                        import json
                        action_items = json.loads(row[4]) if row[4] else []
                        if action_items:
                            lines.append("\n✅ 待办事项:")
                            for item in action_items[:5]:  # 最多显示5条
                                assignee = item.get('assignee', '待定')
                                task = item.get('task', '')
                                lines.append(f"  • {assignee}: {task}")
                    except:
                        pass
                    
                    # 添加部分转写内容
                    if transcription:
                        preview = transcription[:300] + "..." if len(transcription) > 300 else transcription
                        lines.append(f"\n📄 转写预览:\n{preview}")
                    
                    lines.append("\n━" * 18)
                    lines.append("完整内容可在系统中查看")
                    
                    await send_text_message(user_id, "\n".join(lines))
                    logger.info(f"[Clauwdbot] 会议纪要已发送: {meeting_id}")
                    return
                
                elif status == 'failed':
                    await send_text_message(user_id, "❌ 会议录音转写失败，请检查录音质量后重试。")
                    return
                    
        except Exception as e:
            logger.error(f"[Clauwdbot] 检查转写状态失败: {e}")
    
    # 超时
    await send_text_message(user_id, "⏰ 会议录音转写超时，请稍后在系统中查看结果。")


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
            logger.error("[Clauwdbot] 企业微信配置不完整")
            raise ValueError("企业微信配置不完整")
        
        decrypted = crypto.verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info(f"[Clauwdbot] URL验证成功")
        return PlainTextResponse(content=decrypted)
        
    except Exception as e:
        logger.error(f"[Clauwdbot] URL验证失败: {e}")
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
            logger.error("[Clauwdbot] 企业微信配置不完整")
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
        
        logger.info(f"[Clauwdbot] 收到消息: {message}")
        
        # 消息去重
        msg_id = message.get("MsgId")
        if msg_id and is_message_processed(msg_id):
            logger.info(f"[Clauwdbot] 跳过重复消息: {msg_id}")
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
        logger.error(f"[Clauwdbot] 处理消息异常: {e}")
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


