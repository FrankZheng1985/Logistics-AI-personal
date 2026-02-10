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


def _detect_document_type(file_name: str) -> str:
    """检测文档类型，返回中文描述"""
    file_name_lower = file_name.lower()
    
    contract_keywords = ["合同", "协议", "contract", "agreement", "代理", "运输", "物流", "委托"]
    if any(kw in file_name_lower for kw in contract_keywords):
        return "⚖️ 合同法律"
    
    finance_keywords = ["发票", "invoice", "财务", "报表", "账单", "bill", "费用", "报价", "quote"]
    if any(kw in file_name_lower for kw in finance_keywords):
        return "💰 财务会计"
    
    logistics_keywords = ["提单", "b/l", "报关", "海关", "customs", "shipping", "运单", "incoterms"]
    if any(kw in file_name_lower for kw in logistics_keywords):
        return "🚢 跨境贸易"
    
    return "📋 综合内容"


def _build_document_analysis_prompt(file_name: str, content: str) -> str:
    """
    根据文档类型智能构建分析提示词
    自动识别合同、简历、报告等类型，触发专家模式
    """
    file_name_lower = file_name.lower()
    
    # 合同类文档 - 启用法律顾问专家角色
    contract_keywords = ["合同", "协议", "contract", "agreement", "代理", "运输", "物流", "委托"]
    is_contract = any(kw in file_name_lower for kw in contract_keywords)
    
    # 财务类文档 - 启用财务会计专家角色
    finance_keywords = ["发票", "invoice", "财务", "报表", "账单", "bill", "费用", "报价", "quote"]
    is_finance = any(kw in file_name_lower for kw in finance_keywords)
    
    # 物流/贸易类文档 - 启用跨境贸易专家角色
    logistics_keywords = ["提单", "b/l", "报关", "海关", "customs", "shipping", "运单", "incoterms"]
    is_logistics = any(kw in file_name_lower for kw in logistics_keywords)
    
    # 构建专业分析提示词
    if is_contract:
        prompt = f"""【法律顾问模式】老板发送了一份合同文件需要你审核：

📄 文件名：{file_name}

📝 合同内容：
{content}

---
请以法律顾问的专业角度进行全面审核，包括：

1. **合同概述**：合同类型、签约双方、主要标的

2. **关键条款审查**：
   - 权利义务是否对等
   - 价款/费用条款是否清晰
   - 交付/验收标准是否明确
   - 违约责任是否合理

3. **风险提示** ⚠️：
   - 潜在法律风险
   - 不利条款/霸王条款
   - 模糊表述可能引发的争议

4. **修改建议**：需要补充或修改的条款

5. **总体评估**：是否建议签署，或需要进一步协商的要点"""

    elif is_finance:
        prompt = f"""【财务会计模式】老板发送了一份财务相关文件需要你分析：

📄 文件名：{file_name}

📝 文件内容：
{content}

---
请以财务专家的角度进行分析，包括：

1. **文件概述**：文件类型、涉及金额、相关方
2. **合规性检查**：发票/单据是否符合规范
3. **数据核验**：金额计算是否正确，有无异常
4. **税务风险**：潜在的税务问题
5. **建议事项**：需要注意的财务要点"""

    elif is_logistics:
        prompt = f"""【跨境贸易专家模式】老板发送了一份物流/贸易文件需要你分析：

📄 文件名：{file_name}

📝 文件内容：
{content}

---
请以跨境贸易专家的角度进行分析，包括：

1. **文件概述**：文件类型、贸易条款、涉及方
2. **Incoterms分析**：贸易术语下的风险转移点和费用承担
3. **合规检查**：海关申报、原产地规则等合规性
4. **物流风险**：运输方式、保险、交付风险
5. **建议事项**：需要关注的要点"""

    else:
        # 通用文档分析
        prompt = f"""老板发送了一个文件给你：{file_name}

📝 文件内容：
{content}

---
请阅读并分析这个文件：

1. **内容概述**：文件的主要内容和目的
2. **关键信息**：重要的数据、日期、金额等
3. **需要关注的要点**：潜在问题或需要注意的地方
4. **建议行动**：下一步应该做什么

如果这是合同类文件，请特别注意审核条款风险。"""

    return prompt


async def process_file_message(user_id: str, media_id: str, file_name: str):
    """处理文件消息（会议录音、文档等）"""
    from app.agents.assistant_agent import clauwdbot_agent
    from app.services.speech_recognition_service import speech_recognition_service
    from app.services.cos_storage_service import cos_storage_service
    from app.services.document_service import document_service
    
    logger.info(f"[Clauwdbot] 收到文件: user={user_id}, file={file_name}")
    
    # 1. 下载文件（通用步骤）
    file_data = await download_media(media_id)
    if not file_data:
        await send_text_message(user_id, "文件下载失败，请重新发送。")
        return
    
    # 保存到临时文件
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file_name)
    
    try:
        with open(temp_path, "wb") as f:
            f.write(file_data)
            
        # 2. 判断文件类型
        ext = os.path.splitext(file_name)[1].lower()
        
        # --- 情况A：音频文件 (会议录音) ---
        audio_extensions = [".mp3", ".m4a", ".wav", ".amr", ".ogg", ".aac"]
        if ext in audio_extensions:
            await _handle_audio_file(user_id, file_name, file_data, cos_storage_service, speech_recognition_service)
            return

        # --- 情况B：文档文件 (Word, PDF, TXT) ---
        doc_extensions = [".docx", ".doc", ".pdf", ".txt", ".md", ".csv", ".json"]
        if ext in doc_extensions:
            # 立即反馈，让用户知道开始处理
            await send_text_message(user_id, f"📄 收到「{file_name}」\n⏳ 正在读取文档内容...")
            
            # 解析文档
            doc_result = await document_service.read_document(temp_path, file_name)
            
            if not doc_result["success"]:
                await send_text_message(user_id, f"❌ 文档读取失败: {doc_result['error']}")
                return
            
            content = doc_result["content"]
            file_name_lower = file_name.lower()
            
            # 发送进度更新
            doc_type = _detect_document_type(file_name_lower)
            await send_text_message(user_id, f"✅ 文档读取完成（{len(content)}字）\n🔍 正在进行{doc_type}分析...")
            
            # 智能识别文档类型，构建专业提示词
            prompt = _build_document_analysis_prompt(file_name_lower, content)
            
            # 使用快速直接调用 LLM，跳过复杂的 ReAct 循环
            try:
                from app.core.llm import chat_completion
                import asyncio
                
                # 设置超时，避免无限等待
                response = await asyncio.wait_for(
                    chat_completion(
                        messages=[{"role": "user", "content": prompt}],
                        system_prompt="你是Maria，老板的AI助理，具备法律、财务、物流等专业知识。请直接分析文档内容，给出专业建议。",
                        use_advanced=True,
                        agent_name="Maria",
                        task_type="document_analysis",
                        max_tokens=4000,  # 允许更长的回复
                    ),
                    timeout=120  # 2分钟超时
                )
                
                if response:
                    await send_text_message(user_id, response)
                else:
                    await send_text_message(user_id, "⚠️ 分析完成但未生成回复，请重试或换个方式提问。")
                    
            except asyncio.TimeoutError:
                await send_text_message(user_id, "⏰ 分析时间较长，我会继续处理。如有结果会立即通知您。")
            except Exception as e:
                logger.error(f"[Maria] 文档分析失败: {e}")
                await send_text_message(user_id, f"⚠️ 分析出现问题: {str(e)[:100]}\n请稍后重试。")
            return

        # --- 情况C：其他文件 ---
        await send_text_message(user_id, f"收到文件: {file_name}\n\n目前我支持处理：\n1. 音频文件 (转写会议纪要)\n2. 文档 (Word, PDF, TXT)")
        
    except Exception as e:
        logger.error(f"[Clauwdbot] 处理文件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await send_text_message(user_id, f"处理文件时出现系统错误: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


async def _handle_audio_file(user_id, file_name, audio_data, cos_service, asr_service):
    """处理音频文件的具体逻辑"""
    # 检查配置
    if not cos_service.is_configured:
        await send_text_message(user_id, f"📼 收到录音: {file_name}\n\n⚠️ 云存储未配置，请联系管理员配置腾讯云COS。")
        return
    
    if not asr_service.is_configured():
        await send_text_message(user_id, f"📼 收到录音: {file_name}\n\n⚠️ 语音识别未配置，请联系管理员配置腾讯云ASR。")
        return
    
    # 通知用户
    await send_text_message(user_id, f"📼 收到会议录音: {file_name}\n\n正在处理中，转写完成后会自动发送会议纪要。\n⏱ 预计需要2-5分钟")
    
    # 上传到COS
    success, result = await cos_service.upload_bytes(
        data=audio_data,
        filename=file_name,
        folder="meeting_audio"
    )
    
    if not success:
        await send_text_message(user_id, f"音频上传失败: {result}")
        return
    
    audio_url = result
    
    # 创建会议记录
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
    
    # 调用语音识别
    ext = os.path.splitext(file_name)[1].lower().lstrip('.')
    audio_format = ext if ext in ['mp3', 'm4a', 'wav', 'amr', 'ogg'] else 'mp3'
    
    transcribe_result = await asr_service.transcribe_audio(
        audio_url=audio_url,
        meeting_id=meeting_id,
        audio_format=audio_format
    )
    
    if not transcribe_result.get("success"):
        await send_text_message(user_id, f"语音识别启动失败: {transcribe_result.get('error')}")
        return
    
    # 启动后台等待
    import asyncio
    asyncio.create_task(
        _wait_and_send_meeting_summary(user_id, meeting_id, transcribe_result.get('task_id'))
    )


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
            # Link 消息字段
            "Title": msg_root.find("Title").text if msg_root.find("Title") is not None else None,
            "Description": msg_root.find("Description").text if msg_root.find("Description") is not None else None,
            "Url": msg_root.find("Url").text if msg_root.find("Url") is not None else None,
            "PicUrl": msg_root.find("PicUrl").text if msg_root.find("PicUrl") is not None else None,
        }
        
        logger.info(f"[Clauwdbot] 收到消息: type={message.get('MsgType')}, from={message.get('FromUserName')}, media_id={message.get('MediaId')}, file_name={message.get('FileName')}")
        logger.debug(f"[Clauwdbot] 完整消息: {message}")
        
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
            logger.info(f"[Clauwdbot] 📁 收到文件: {file_name}, media_id={media_id}")
            if media_id:
                background_tasks.add_task(process_file_message, user_id, media_id, file_name)
            else:
                logger.warning(f"[Clauwdbot] 文件消息缺少 MediaId")
        
        elif msg_type == "image":
            logger.info(f"[Clauwdbot] 🖼️ 收到图片消息")
            await send_text_message(user_id, "收到图片。目前我支持处理文本、文档和音频文件。")
        
        elif msg_type == "link":
            # Link 消息（可能是分享的文档、网页等）
            title = message.get("Title", "")
            description = message.get("Description", "")
            url = message.get("Url", "")
            logger.info(f"[Clauwdbot] 🔗 收到链接消息: title={title}, url={url}")
            
            # 如果有描述内容，当作文本处理
            if description and len(description) > 50:
                # 描述内容较长，可能是文档内容
                content = f"【{title}】\n\n{description}"
                background_tasks.add_task(process_text_message, user_id, content)
            elif url and "doc.weixin.qq.com" in url:
                # 腾讯文档/企业微信微盘链接
                reply = f"""📄 收到微盘文档：**{title}**

由于企业微信微盘的限制，我无法直接读取文档内容。

📋 **请这样操作：**
1. 点击文档链接打开
2. 在腾讯文档页面按 **Ctrl+A** 全选
3. **Ctrl+C** 复制
4. 回到聊天窗口 **Ctrl+V** 粘贴发给我

或者：直接把 Word/PDF 原文件拖拽发送给我（不要通过微盘）"""
                await send_text_message(user_id, reply)
            elif url:
                # 其他链接
                await send_text_message(user_id, f"收到链接：{title}\n\n如果您想让我分析文档内容，请直接复制粘贴文档文字发给我。")
            else:
                await send_text_message(user_id, "收到链接消息，但无法获取内容。请直接复制粘贴文档文字发给我。")
        
        else:
            # 记录未知消息类型
            logger.warning(f"[Clauwdbot] ⚠️ 未处理的消息类型: {msg_type}")
        
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


