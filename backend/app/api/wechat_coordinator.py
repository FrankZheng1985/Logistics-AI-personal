"""
小调 - 企业微信消息回调接口
功能：
1. 接收老板/管理员的任务指令
2. 智能分析并分配给对应AI员工
3. 汇报工作进展和日报
"""
import asyncio
from collections import OrderedDict
from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger
import hashlib
import base64
import struct
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from typing import Dict, Any, Optional
import httpx
import json
from datetime import datetime

from app.core.config import settings
from app.agents.coordinator import coordinator
from app.models.database import AsyncSessionLocal


router = APIRouter(prefix="/wechat/coordinator", tags=["企业微信-小调"])


class CoordinatorWeChatCrypto:
    """小调企业微信消息加解密"""
    
    def __init__(self):
        self.token = settings.WECHAT_COORDINATOR_TOKEN or ''
        self.encoding_aes_key = settings.WECHAT_COORDINATOR_ENCODING_AES_KEY or ''
        self.corp_id = settings.WECHAT_CORP_ID or ''
        
        if self.encoding_aes_key:
            self.aes_key = base64.b64decode(self.encoding_aes_key + "=")
        else:
            self.aes_key = None
    
    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """验证URL有效性并返回解密后的echostr"""
        if not self.token:
            raise ValueError("Token未配置")
        
        sort_list = sorted([self.token, timestamp, nonce, echostr])
        sha1 = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        
        logger.debug(f"[小调] 签名验证: calculated={sha1}, expected={msg_signature}")
        
        if sha1 != msg_signature:
            raise ValueError(f"签名验证失败")
        
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
            
            # 验证padding是否合法
            if pad_len < 1 or pad_len > 32:
                pad_len = 0
            
            content = decrypted[:-pad_len] if pad_len > 0 else decrypted
            
            if len(content) < 20:
                raise ValueError(f"解密后内容太短: {len(content)} bytes")
            
            msg_len = struct.unpack(">I", content[16:20])[0]
            msg = content[20:20+msg_len].decode("utf-8")
            
            return msg
        except Exception as e:
            logger.error(f"[小调] 解密失败: {e}")
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


# 消息去重缓存
_processed_messages = OrderedDict()
_MAX_CACHE_SIZE = 500


def is_message_processed(msg_id: str) -> bool:
    return msg_id in _processed_messages


def mark_message_processed(msg_id: str):
    _processed_messages[msg_id] = True
    while len(_processed_messages) > _MAX_CACHE_SIZE:
        _processed_messages.popitem(last=False)


def get_crypto() -> Optional[CoordinatorWeChatCrypto]:
    """获取小调专用的加解密实例"""
    crypto = CoordinatorWeChatCrypto()
    if crypto.token and crypto.aes_key and crypto.corp_id:
        return crypto
    return None


async def get_access_token() -> Optional[str]:
    """获取小调应用的access_token"""
    corp_id = settings.WECHAT_CORP_ID
    secret = settings.WECHAT_COORDINATOR_SECRET
    
    if not corp_id or not secret:
        return None
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": secret}
        )
        data = response.json()
        
        if data.get("errcode") == 0:
            return data.get("access_token")
        else:
            logger.error(f"[小调] 获取access_token失败: {data}")
            return None


async def send_text_message(user_ids: list, content: str) -> Dict[str, Any]:
    """发送文本消息"""
    access_token = await get_access_token()
    if not access_token:
        return {"success": False, "error": "无法获取access_token"}
    
    agent_id = settings.WECHAT_COORDINATOR_AGENT_ID
    
    payload = {
        "touser": "|".join(user_ids),
        "msgtype": "text",
        "agentid": agent_id,
        "text": {"content": content}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": access_token},
            json=payload
        )
        data = response.json()
        
        if data.get("errcode") == 0:
            return {"success": True}
        else:
            return {"success": False, "error": data}


async def send_markdown_message(user_ids: list, content: str) -> Dict[str, Any]:
    """发送Markdown消息"""
    access_token = await get_access_token()
    if not access_token:
        return {"success": False, "error": "无法获取access_token"}
    
    agent_id = settings.WECHAT_COORDINATOR_AGENT_ID
    
    payload = {
        "touser": "|".join(user_ids),
        "msgtype": "markdown",
        "agentid": agent_id,
        "markdown": {"content": content}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": access_token},
            json=payload
        )
        data = response.json()
        
        if data.get("errcode") == 0:
            return {"success": True}
        else:
            return {"success": False, "error": data}


def is_admin_user(user_id: str) -> bool:
    """检查是否是管理员用户"""
    admin_users = settings.WECHAT_COORDINATOR_ADMIN_USERS
    if not admin_users:
        return True  # 未配置管理员则所有人可用
    
    admin_list = [u.strip() for u in admin_users.split(",") if u.strip()]
    return user_id in admin_list


@router.get("/callback")
async def verify_callback(
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="加密的随机字符串")
):
    """
    验证企业微信回调URL
    """
    try:
        crypto = get_crypto()
        if not crypto:
            logger.error("[小调] 企业微信配置不完整")
            raise HTTPException(status_code=500, detail="小调企业微信配置未完成")
        
        logger.info(f"[小调] 收到URL验证请求: timestamp={timestamp}")
        
        decrypted = crypto.verify_signature(msg_signature, timestamp, nonce, echostr)
        
        logger.info("✅ [小调] 企业微信URL验证成功")
        return PlainTextResponse(content=decrypted)
        
    except Exception as e:
        logger.error(f"❌ [小调] URL验证失败: {e}")
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
    接收企业微信消息 - 小调
    """
    try:
        crypto = get_crypto()
        if not crypto:
            logger.error("[小调] 企业微信配置不完整")
            return PlainTextResponse(content="success")
        
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
        }
        
        logger.info(f"[小调] 收到消息: {message}")
        
        # 处理文本消息
        if message.get("MsgType") == "text":
            msg_id = message.get("MsgId")
            user_id = message.get("FromUserName")
            content = message.get("Content", "").strip()
            
            # 消息去重
            if msg_id and is_message_processed(msg_id):
                logger.info(f"[小调] 跳过重复消息: {msg_id}")
                return PlainTextResponse(content="success")
            
            if msg_id:
                mark_message_processed(msg_id)
            
            # 检查权限
            if not is_admin_user(user_id):
                logger.warning(f"[小调] 非管理员用户尝试发送消息: {user_id}")
                background_tasks.add_task(
                    send_text_message,
                    [user_id],
                    "抱歉，您没有权限使用小调。请联系管理员添加权限。"
                )
                return PlainTextResponse(content="success")
            
            # 后台处理消息
            background_tasks.add_task(process_coordinator_message, user_id, content)
        
        return PlainTextResponse(content="success")
        
    except Exception as e:
        logger.error(f"❌ [小调] 处理消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return PlainTextResponse(content="success")


async def process_coordinator_message(user_id: str, content: str):
    """
    处理发给小调的消息
    
    支持的指令：
    1. "日报" / "报告" / "工作汇报" - 获取今日工作报告
    2. "系统状态" / "健康检查" - 获取系统健康状态
    3. "员工状态" / "团队状态" - 获取AI员工工作状态
    4. 其他消息 - 作为任务分析并分配
    """
    try:
        logger.info(f"[小调] 处理用户 {user_id} 的消息: {content}")
        
        content_lower = content.lower()
        
        # 日报/报告指令
        if any(kw in content for kw in ["日报", "报告", "工作汇报", "今日汇报"]):
            await handle_daily_report(user_id)
            return
        
        # 系统状态指令
        if any(kw in content for kw in ["系统状态", "健康检查", "系统健康"]):
            await handle_system_status(user_id)
            return
        
        # 员工状态指令
        if any(kw in content for kw in ["员工状态", "团队状态", "AI状态"]):
            await handle_team_status(user_id)
            return
        
        # 帮助指令
        if any(kw in content for kw in ["帮助", "help", "指令", "命令"]):
            await handle_help(user_id)
            return
        
        # 其他消息作为任务处理
        await handle_task_assignment(user_id, content)
        
    except Exception as e:
        logger.error(f"[小调] 处理消息异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await send_text_message([user_id], f"抱歉，处理您的消息时出现错误：{str(e)}")


async def handle_daily_report(user_id: str):
    """处理日报请求"""
    try:
        await send_text_message([user_id], "📊 正在生成今日工作报告，请稍候...")
        
        # 调用小调生成报告
        result = await coordinator.process({
            "action": "report",
            "report_type": "daily"
        })
        
        readable_report = result.get("readable_report", "报告生成失败")
        
        # 企业微信消息有长度限制，需要分段发送
        if len(readable_report) > 2000:
            parts = split_message(readable_report, 2000)
            for i, part in enumerate(parts):
                await send_text_message([user_id], f"📊 工作日报 ({i+1}/{len(parts)})\n\n{part}")
                await asyncio.sleep(0.5)  # 避免发送太快
        else:
            await send_text_message([user_id], readable_report)
        
        # 记录到数据库
        await record_coordinator_interaction(user_id, "日报", "report", result)
        
    except Exception as e:
        logger.error(f"[小调] 生成日报失败: {e}")
        await send_text_message([user_id], f"生成日报失败：{str(e)}")


async def handle_system_status(user_id: str):
    """处理系统状态请求"""
    try:
        await send_text_message([user_id], "🔍 正在检查系统状态...")
        
        result = await coordinator.process({
            "action": "monitor",
            "check_type": "all"
        })
        
        health = result.get("result", {})
        overall_status = health.get("overall_status", "unknown")
        
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "🔴",
            "unknown": "❓"
        }.get(overall_status, "❓")
        
        # 构建状态消息
        msg_lines = [
            f"🖥️ 系统健康状态报告",
            f"",
            f"整体状态: {status_emoji} {overall_status.upper()}",
            f"检查时间: {result.get('checked_at', '未知')}",
        ]
        
        # 添加问题列表
        issues = health.get("issues", [])
        if issues:
            msg_lines.append("")
            msg_lines.append("⚠️ 发现的问题:")
            for issue in issues[:5]:  # 最多显示5个
                msg_lines.append(f"  • {issue}")
        else:
            msg_lines.append("")
            msg_lines.append("✅ 系统运行正常，无异常")
        
        await send_text_message([user_id], "\n".join(msg_lines))
        
    except Exception as e:
        logger.error(f"[小调] 检查系统状态失败: {e}")
        await send_text_message([user_id], f"检查系统状态失败：{str(e)}")


async def handle_team_status(user_id: str):
    """处理团队状态请求"""
    try:
        await send_text_message([user_id], "👥 正在获取AI团队状态...")
        
        # 查询各AI员工今日任务情况
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT 
                        agent_type,
                        COUNT(*) as total_tasks,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                        MAX(created_at) as last_active
                    FROM ai_tasks
                    WHERE created_at >= CURRENT_DATE
                    GROUP BY agent_type
                """)
            )
            stats = result.fetchall()
        
        # AI员工名称映射
        agent_names = {
            "coordinator": "小调",
            "video_creator": "小影",
            "copywriter": "小文",
            "sales": "小销",
            "follow": "小跟",
            "analyst": "小析",
            "lead_hunter": "小猎"
        }
        
        msg_lines = [
            "👥 AI团队今日工作状态",
            "",
        ]
        
        if stats:
            for row in stats:
                agent_type = row[0]
                total = row[1]
                completed = row[2]
                failed = row[3]
                
                name = agent_names.get(agent_type, agent_type)
                success_rate = (completed / total * 100) if total > 0 else 0
                
                status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "🔴"
                
                msg_lines.append(f"{status_emoji} {name}: {completed}/{total} 完成 ({success_rate:.0f}%)")
        else:
            msg_lines.append("今日暂无任务记录")
        
        msg_lines.append("")
        msg_lines.append(f"📊 统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        await send_text_message([user_id], "\n".join(msg_lines))
        
    except Exception as e:
        logger.error(f"[小调] 获取团队状态失败: {e}")
        await send_text_message([user_id], f"获取团队状态失败：{str(e)}")


async def handle_help(user_id: str):
    """处理帮助请求"""
    help_text = """📋 小调使用指南

【查询指令】
• 日报 / 报告 - 获取今日工作报告
• 系统状态 - 检查系统健康状态
• 员工状态 - 查看AI团队工作情况
• 帮助 - 显示本帮助信息

【任务分配】
直接发送任务描述，小调会智能分析并分配：

示例：
• "帮我写一篇关于欧洲海运的推广文案"
  → 分配给小文

• "搜索一下深圳做跨境电商的公司"
  → 分配给小猎

• "分析一下最近的客户转化情况"
  → 分配给小析

• "给客户xxx发一条跟进消息"
  → 分配给小跟

【小调管理的AI员工】
• 小影 - 视频创作
• 小文 - 文案策划
• 小销 - 销售客服
• 小跟 - 客户跟进
• 小析 - 客户分析
• 小猎 - 线索搜索"""
    
    await send_text_message([user_id], help_text)


async def handle_task_assignment(user_id: str, content: str):
    """处理任务分配请求"""
    try:
        await send_text_message([user_id], f"🤔 收到任务，正在分析...\n\n「{content}」")
        
        # 调用小调分析任务
        result = await coordinator.process({
            "action": "analyze",
            "task_description": content
        })
        
        recommended_agent = result.get("recommended_agent", "unknown")
        task_type = result.get("task_type", "general")
        priority = result.get("priority", "medium")
        reason = result.get("reason", "")
        
        # AI员工名称映射
        agent_names = {
            "coordinator": "小调",
            "video_creator": "小影",
            "copywriter": "小文",
            "sales": "小销",
            "follow": "小跟",
            "analyst": "小析",
            "lead_hunter": "小猎"
        }
        
        agent_name = agent_names.get(recommended_agent, recommended_agent)
        
        priority_emoji = {
            "urgent": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(priority, "⚪")
        
        # 分配任务
        dispatch_result = await coordinator.process({
            "action": "dispatch",
            "task_type": task_type,
            "target_agent": recommended_agent,
            "task_data": {
                "description": content,
                "from_user": user_id,
                "source": "wechat_coordinator"
            },
            "priority": priority
        })
        
        task_id = dispatch_result.get("task_id", "")[:8]  # 只显示前8位
        
        # 回复用户
        reply_lines = [
            "✅ 任务已分配",
            "",
            f"📋 任务: {content[:50]}{'...' if len(content) > 50 else ''}",
            f"👤 分配给: {agent_name}",
            f"📌 类型: {task_type}",
            f"{priority_emoji} 优先级: {priority}",
            f"🔖 任务ID: {task_id}",
            "",
            f"💡 分配原因: {reason}" if reason else "",
        ]
        
        await send_text_message([user_id], "\n".join([l for l in reply_lines if l]))
        
        # 记录到数据库
        await record_coordinator_interaction(user_id, content, "task_dispatch", dispatch_result)
        
    except Exception as e:
        logger.error(f"[小调] 任务分配失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await send_text_message([user_id], f"任务分配失败：{str(e)}")


async def record_coordinator_interaction(
    user_id: str,
    content: str,
    interaction_type: str,
    result: Dict[str, Any]
):
    """记录小调的交互记录"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            import uuid
            
            await db.execute(
                text("""
                    INSERT INTO coordinator_interactions 
                    (id, user_id, content, interaction_type, result, created_at)
                    VALUES (:id, :user_id, :content, :interaction_type, :result, NOW())
                """),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "content": content,
                    "interaction_type": interaction_type,
                    "result": json.dumps(result, ensure_ascii=False, default=str)
                }
            )
            await db.commit()
    except Exception as e:
        logger.error(f"[小调] 记录交互失败: {e}")


def split_message(text: str, max_length: int) -> list:
    """将长消息分割成多段"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    lines = text.split("\n")
    current_part = ""
    
    for line in lines:
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + "\n"
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = line + "\n"
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts


# ============ 主动推送功能 ============

async def send_daily_report_to_admins():
    """
    向管理员发送每日工作报告
    由定时任务调用
    """
    try:
        admin_users = settings.WECHAT_COORDINATOR_ADMIN_USERS
        if not admin_users:
            logger.info("[小调] 未配置管理员，跳过日报推送")
            return
        
        admin_list = [u.strip() for u in admin_users.split(",") if u.strip()]
        
        logger.info(f"[小调] 开始向 {len(admin_list)} 位管理员发送日报")
        
        # 生成报告
        result = await coordinator.process({
            "action": "report",
            "report_type": "daily"
        })
        
        readable_report = result.get("readable_report", "报告生成失败")
        
        # 发送给每位管理员
        for user_id in admin_list:
            try:
                if len(readable_report) > 2000:
                    parts = split_message(readable_report, 2000)
                    for i, part in enumerate(parts):
                        await send_text_message([user_id], f"📊 每日工作日报 ({i+1}/{len(parts)})\n\n{part}")
                        await asyncio.sleep(0.5)
                else:
                    await send_text_message([user_id], f"📊 每日工作日报\n\n{readable_report}")
                
                logger.info(f"[小调] 已向 {user_id} 发送日报")
            except Exception as e:
                logger.error(f"[小调] 向 {user_id} 发送日报失败: {e}")
        
    except Exception as e:
        logger.error(f"[小调] 发送每日报告失败: {e}")


async def notify_task_completion(task_id: str, agent_name: str, result: str):
    """
    通知管理员任务完成
    """
    try:
        admin_users = settings.WECHAT_COORDINATOR_ADMIN_USERS
        if not admin_users:
            return
        
        admin_list = [u.strip() for u in admin_users.split(",") if u.strip()]
        
        msg = f"""✅ 任务完成通知

🔖 任务ID: {task_id[:8]}
👤 执行者: {agent_name}
📋 结果: {result[:200]}{'...' if len(result) > 200 else ''}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        await send_text_message(admin_list, msg)
        
    except Exception as e:
        logger.error(f"[小调] 通知任务完成失败: {e}")


@router.get("/config-status")
async def get_coordinator_config_status():
    """获取小调企业微信配置状态"""
    return {
        "is_configured": bool(
            settings.WECHAT_CORP_ID and 
            settings.WECHAT_COORDINATOR_SECRET and
            settings.WECHAT_COORDINATOR_AGENT_ID
        ),
        "is_callback_configured": bool(
            settings.WECHAT_COORDINATOR_TOKEN and 
            settings.WECHAT_COORDINATOR_ENCODING_AES_KEY and
            settings.WECHAT_CORP_ID
        ),
        "agent_id": settings.WECHAT_COORDINATOR_AGENT_ID,
        "admin_users_count": len([
            u.strip() for u in settings.WECHAT_COORDINATOR_ADMIN_USERS.split(",") 
            if u.strip()
        ]) if settings.WECHAT_COORDINATOR_ADMIN_USERS else 0
    }
