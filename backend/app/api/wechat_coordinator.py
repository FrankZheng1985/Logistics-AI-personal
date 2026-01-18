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
            logger.debug(f"[小调] 加密数据长度: {len(encrypted_bytes)}, AES key长度: {len(self.aes_key)}")
            
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            decrypted = cipher.decrypt(encrypted_bytes)
            
            logger.debug(f"[小调] 解密后数据长度: {len(decrypted)}")
            
            # PKCS7去除补位
            pad = decrypted[-1]
            pad_len = pad if isinstance(pad, int) else ord(pad)
            
            logger.debug(f"[小调] Padding长度: {pad_len}")
            
            # 验证padding是否合法 (AES块大小是16)
            if pad_len < 1 or pad_len > 16:
                logger.warning(f"[小调] 非法padding: {pad_len}, 尝试不去除padding")
                content = decrypted
            else:
                content = decrypted[:-pad_len]
            
            logger.debug(f"[小调] 去除padding后长度: {len(content)}")
            
            if len(content) < 20:
                raise ValueError(f"解密后内容太短: {len(content)} bytes")
            
            # 解析内容: 16字节随机数 + 4字节消息长度 + 消息内容 + CorpId
            msg_len = struct.unpack(">I", content[16:20])[0]
            logger.debug(f"[小调] 消息长度: {msg_len}")
            
            if msg_len > len(content) - 20:
                logger.warning(f"[小调] 消息长度异常: msg_len={msg_len}, content_len={len(content)}")
                msg_len = len(content) - 20
            
            msg = content[20:20+msg_len].decode("utf-8")
            logger.debug(f"[小调] 解密消息: {msg}")
            
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
    4. "任务状态" / "进度" - 查询最近任务状态
    5. 其他消息 - 作为任务分析、分配并执行
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
        
        # 任务状态/追问识别
        if any(kw in content for kw in ["任务状态", "进度", "什么时候", "结果呢", "结果？", "给我结果", "完成了吗", "做完了吗", "怎么样了"]):
            await handle_task_status_query(user_id, content)
            return
        
        # 其他消息作为任务处理（分析→分配→执行→反馈结果）
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
• 任务状态 - 查看最近任务进度
• 帮助 - 显示本帮助信息

【任务分配】
直接发送任务描述，小调会智能分析、分配并执行，完成后自动返回结果。

示例：
• "帮我写一篇关于欧洲海运的推广文案"
  → 小文执行，返回文案内容

• "搜索一下深圳做跨境电商的公司"
  → 小猎执行，返回线索列表

• "分析一下最近的客户转化情况"
  → 小析执行，返回分析报告

• "ERP系统。我们的订单。上一周完成了多少？"
  → 小析执行，返回数据统计

【工作闭环】
小调现在会完成完整的工作流程：
1. 📥 接收任务
2. 🔍 分析并分配给合适的AI员工
3. ⚙️ 执行任务
4. 📤 返回执行结果

【小调管理的AI员工】
• 小影 - 视频创作
• 小文 - 文案策划
• 小销 - 销售客服
• 小跟 - 客户跟进
• 小析 - 数据分析
• 小猎 - 线索搜索"""
    
    await send_text_message([user_id], help_text)


async def handle_task_status_query(user_id: str, content: str):
    """处理任务状态查询/追问"""
    try:
        logger.info(f"[小调] 用户 {user_id} 查询任务状态: {content}")
        
        # 查询该用户最近的任务
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT id, task_type, agent_type, status, input_data, 
                           output_data, created_at, completed_at
                    FROM ai_tasks
                    WHERE input_data::text LIKE :user_pattern
                    ORDER BY created_at DESC
                    LIMIT 5
                """),
                {"user_pattern": f'%{user_id}%'}
            )
            tasks = result.fetchall()
        
        if not tasks:
            await send_text_message([user_id], "📋 暂无任务记录\n\n您还没有分配过任务，直接发送任务描述即可开始。")
            return
        
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
        
        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "completed": "✅",
            "failed": "❌"
        }
        
        msg_lines = [
            "📋 您最近的任务状态：",
            ""
        ]
        
        for task in tasks:
            task_id = str(task[0])[:8]
            task_type = task[1]
            agent_type = task[2]
            status = task[3]
            input_data = task[4] if isinstance(task[4], dict) else json.loads(task[4] or '{}')
            created_at = task[6]
            
            agent_name = agent_names.get(agent_type, agent_type)
            emoji = status_emoji.get(status, "❓")
            desc = input_data.get("description", "")[:30]
            
            time_str = created_at.strftime('%m-%d %H:%M') if created_at else ""
            
            msg_lines.append(f"{emoji} [{task_id}] {desc}...")
            msg_lines.append(f"   执行者: {agent_name} | 状态: {status} | {time_str}")
            msg_lines.append("")
        
        msg_lines.append("💡 如需详情，请回复「任务ID」查询")
        
        await send_text_message([user_id], "\n".join(msg_lines))
        
    except Exception as e:
        logger.error(f"[小调] 查询任务状态失败: {e}")
        await send_text_message([user_id], f"查询任务状态失败：{str(e)}")


async def handle_task_assignment(user_id: str, content: str):
    """处理任务分配请求 - 完整闭环：分析→分配→执行→反馈结果"""
    try:
        await send_text_message([user_id], f"🤔 收到任务，正在分析...\n\n「{content}」")
        
        # 1. 调用小调分析任务
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
        
        # 2. 分配任务（记录到数据库）
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
        
        task_id = dispatch_result.get("task_id", "")
        task_id_short = task_id[:8] if task_id else ""
        
        # 通知用户任务已分配
        reply_lines = [
            "✅ 任务已分配",
            "",
            f"📋 任务: {content[:50]}{'...' if len(content) > 50 else ''}",
            f"👤 分配给: {agent_name}",
            f"📌 类型: {task_type}",
            f"{priority_emoji} 优先级: {priority}",
            f"🔖 任务ID: {task_id_short}",
            "",
            f"💡 分配原因: {reason}" if reason else "",
            "",
            "⏳ 正在执行任务，请稍候..."
        ]
        
        await send_text_message([user_id], "\n".join([l for l in reply_lines if l]))
        
        # 记录交互
        await record_coordinator_interaction(user_id, content, "task_dispatch", dispatch_result)
        
        # 3. 真正执行任务并获取结果
        execution_result = await execute_task_and_get_result(
            user_id=user_id,
            task_id=task_id,
            task_type=task_type,
            recommended_agent=recommended_agent,
            task_description=content,
            agent_name=agent_name
        )
        
        # 4. 将执行结果反馈给用户
        if execution_result:
            await send_task_result_to_user(user_id, task_id_short, agent_name, execution_result)
        
    except Exception as e:
        logger.error(f"[小调] 任务处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await send_text_message([user_id], f"任务处理失败：{str(e)}")


async def execute_task_and_get_result(
    user_id: str,
    task_id: str,
    task_type: str,
    recommended_agent: str,
    task_description: str,
    agent_name: str
) -> Optional[Dict[str, Any]]:
    """执行任务并获取结果"""
    try:
        from app.agents.base import AgentRegistry
        from app.models.conversation import AgentType
        
        # 获取对应的Agent实例（支持英文类型和中文名称）
        agent_type_map = {
            # 英文类型
            "analyst": AgentType.ANALYST,
            "video_creator": AgentType.VIDEO_CREATOR,
            "copywriter": AgentType.COPYWRITER,
            "sales": AgentType.SALES,
            "follow": AgentType.FOLLOW,
            "lead_hunter": AgentType.LEAD_HUNTER,
            # 中文名称
            "小析": AgentType.ANALYST,
            "小影": AgentType.VIDEO_CREATOR,
            "小文": AgentType.COPYWRITER,
            "小销": AgentType.SALES,
            "小跟": AgentType.FOLLOW,
            "小猎": AgentType.LEAD_HUNTER,
        }
        
        # 标准化agent类型（统一转为英文）
        agent_key = recommended_agent.lower() if recommended_agent else ""
        agent_type = agent_type_map.get(recommended_agent) or agent_type_map.get(agent_key)
        
        if not agent_type:
            logger.warning(f"[小调] 未知的Agent类型: {recommended_agent}")
            return {"error": f"未知的执行者类型: {recommended_agent}"}
        
        agent = AgentRegistry.get(agent_type)
        if not agent:
            logger.warning(f"[小调] 未找到Agent实例: {agent_type}")
            return {"error": f"未找到执行者: {agent_name}"}
        
        logger.info(f"[小调] 开始执行任务，执行者: {agent_name}, 任务: {task_description[:50]}")
        
        # 根据不同Agent类型构建输入数据（基于agent_type枚举判断，支持中英文输入）
        result = None
        
        if agent_type == AgentType.ANALYST:
            # 小析 - 数据分析任务
            result = await execute_analyst_task(agent, task_description)
            
        elif agent_type == AgentType.COPYWRITER:
            # 小文 - 文案任务
            result = await execute_copywriter_task(agent, task_description)
            
        elif agent_type == AgentType.LEAD_HUNTER:
            # 小猎 - 线索搜索任务
            result = await execute_lead_hunter_task(agent, task_description)
            
        elif agent_type == AgentType.SALES:
            # 小销 - 销售咨询回复任务
            result = await execute_sales_task(agent, task_description)
            
        elif agent_type == AgentType.FOLLOW:
            # 小跟 - 跟进任务
            result = await execute_follow_task(agent, task_description)
            
        elif agent_type == AgentType.VIDEO_CREATOR:
            # 小影 - 视频创作任务（后台执行，会自动通知用户）
            result = await execute_video_task(agent, task_description, user_id, task_id)
        
        else:
            # 通用处理：尝试调用agent的chat方法
            logger.info(f"[小调] 使用通用方式执行任务: {agent_type}")
            response = await agent.chat(task_description)
            result = {
                "task_type": "general",
                "description": task_description,
                "response": response,
                "executor": agent_name
            }
        
        # 更新任务状态
        if task_id and result:
            # 视频任务是后台执行的，状态设为processing，完成后会自动更新
            if result.get("task_type") == "video_creation":
                await update_task_status(task_id, "processing", result)
            else:
                await update_task_status(task_id, "completed", result)
        
        return result
        
    except Exception as e:
        logger.error(f"[小调] 执行任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 更新任务状态为失败
        if task_id:
            await update_task_status(task_id, "failed", {"error": str(e)})
        
        return {"error": str(e)}


async def execute_analyst_task(agent, task_description: str) -> Dict[str, Any]:
    """执行小析的数据分析任务"""
    # 使用AI来理解任务并生成分析
    analysis_prompt = f"""请作为数据分析师，分析以下任务需求并给出结果：

任务描述：{task_description}

请根据任务需求：
1. 如果是ERP数据查询类任务（如订单统计、业务数据等），请说明需要查询哪些数据
2. 如果是客户分析类任务，请提供分析框架
3. 给出具体的分析结果或建议

注意：如果任务涉及具体数据统计，请说明查询逻辑，并提示需要访问实际数据库获取准确数据。
"""
    
    response = await agent.think([{"role": "user", "content": analysis_prompt}])
    
    return {
        "task_type": "data_analysis",
        "description": task_description,
        "analysis_result": response,
        "executor": "小析"
    }


async def execute_copywriter_task(agent, task_description: str) -> Dict[str, Any]:
    """执行小文的文案任务"""
    # 使用通用文案创作模式
    result = await agent.process({
        "task_type": "general",  # 使用通用模式
        "requirement": task_description,
        "topic": task_description
    })
    
    return {
        "task_type": "copywriting",
        "description": task_description,
        "content": result.get("content", result.get("copy", str(result))),
        "executor": "小文"
    }


async def execute_lead_hunter_task(agent, task_description: str) -> Dict[str, Any]:
    """执行小猎的线索搜索任务"""
    result = await agent.process({
        "action": "smart_hunt",
        "keywords": task_description,
        "query": task_description
    })
    
    return {
        "task_type": "lead_hunting",
        "description": task_description,
        "leads_found": result.get("leads", []),
        "summary": result.get("summary", str(result)),
        "executor": "小猎"
    }


async def execute_sales_task(agent, task_description: str) -> Dict[str, Any]:
    """执行小销的销售咨询回复任务"""
    response = await agent.chat(task_description)
    
    return {
        "task_type": "sales_response",
        "description": task_description,
        "response": response,
        "executor": "小销"
    }


async def execute_follow_task(agent, task_description: str) -> Dict[str, Any]:
    """执行小跟的跟进任务"""
    response = await agent.chat(task_description)
    
    return {
        "task_type": "follow_up",
        "description": task_description,
        "suggestion": response,
        "executor": "小跟"
    }


async def execute_video_task(agent, task_description: str, user_id: str = None, task_id: str = None) -> Dict[str, Any]:
    """执行小影的视频创作任务
    
    视频创作是一个耗时任务，会启动后台任务执行：
    1. 先返回"正在生成中"的状态
    2. 后台任务完成后通过企业微信通知用户
    """
    # 启动后台视频生成任务
    asyncio.create_task(
        _execute_video_generation_background(agent, task_description, user_id, task_id)
    )
    
    return {
        "task_type": "video_creation",
        "description": task_description,
        "status": "视频创作任务已创建，正在后台生成中...\n这类任务通常需要2-5分钟，完成后会通知您。",
        "executor": "小影"
    }


async def _execute_video_generation_background(agent, task_description: str, user_id: str = None, task_id: str = None):
    """后台执行视频生成任务"""
    try:
        logger.info(f"[小影] 开始后台视频生成任务: {task_description[:50]}...")
        
        # 解析任务描述，提取视频参数
        # 使用AI解析任务描述获取标题和脚本
        parse_prompt = f"""请从以下任务描述中提取视频创作信息：

任务描述：{task_description}

请以JSON格式返回：
{{
    "title": "视频标题",
    "script": "视频脚本内容（如果任务描述中包含脚本或文摘，提取完整内容）",
    "keywords": ["关键词1", "关键词2"],
    "mode": "quick",
    "video_type": "ad"
}}

注意：
1. 如果任务描述中包含文摘或脚本内容，将其作为script
2. 如果没有明确标题，根据内容生成一个合适的标题
3. 对于简单任务使用"quick"模式（生成短视频），复杂任务用"movie"模式
"""
        
        parse_response = await agent.think([{"role": "user", "content": parse_prompt}])
        
        # 解析JSON
        video_params = {
            "title": "AI生成视频",
            "script": task_description,
            "keywords": [],
            "mode": "quick",
            "video_type": "ad"
        }
        
        try:
            json_start = parse_response.find("{")
            json_end = parse_response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                parsed = json.loads(parse_response[json_start:json_end])
                video_params.update(parsed)
        except json.JSONDecodeError:
            logger.warning("[小影] 无法解析视频参数，使用默认值")
        
        logger.info(f"[小影] 视频参数: title={video_params['title']}, mode={video_params['mode']}")
        
        # 调用视频生成
        result = await agent.process(video_params)
        
        logger.info(f"[小影] 视频生成完成: status={result.get('status')}")
        
        # 更新任务状态
        if task_id:
            await update_task_status(task_id, "completed", {
                "task_type": "video_creation",
                "description": task_description,
                "video_result": result,
                "executor": "小影"
            })
        
        # 通知用户
        if user_id:
            await _notify_video_completion(user_id, task_id, result)
            
    except Exception as e:
        logger.error(f"[小影] 后台视频生成失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 更新任务状态为失败
        if task_id:
            await update_task_status(task_id, "failed", {"error": str(e)})
        
        # 通知用户失败
        if user_id:
            await send_text_message([user_id], f"""❌ 视频生成失败

🔖 任务ID: {task_id[:8] if task_id else '未知'}
👤 执行者: 小影
⚠️ 错误: {str(e)}

请检查任务描述后重试。""")


async def _notify_video_completion(user_id: str, task_id: str, result: Dict[str, Any]):
    """通知用户视频生成完成"""
    try:
        task_id_short = task_id[:8] if task_id else ""
        status = result.get("status", "unknown")
        video_url = result.get("video_url", "")
        message = result.get("message", "")
        
        if status == "success" and video_url:
            msg = f"""🎬 视频生成成功！

🔖 任务ID: {task_id_short}
👤 执行者: 小影
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📹 视频链接：
{video_url}

💡 {message}"""
        elif status == "api_not_configured":
            msg = f"""⚠️ 视频脚本已生成

🔖 任务ID: {task_id_short}
👤 执行者: 小影

📝 视频脚本已准备好，但可灵AI API未配置，无法生成视频文件。

请联系技术人员配置可灵AI API后重试。"""
        elif status == "processing":
            msg = f"""⏳ 视频仍在生成中

🔖 任务ID: {task_id_short}
👤 执行者: 小影

视频正在AI云端生成，可能需要更长时间。
请稍后使用「查任务」命令查询状态。"""
        else:
            error_msg = result.get("error", message or "未知错误")
            msg = f"""❌ 视频生成失败

🔖 任务ID: {task_id_short}
👤 执行者: 小影
⚠️ 状态: {status}
⚠️ 原因: {error_msg}

请检查任务描述后重试。"""
        
        await send_text_message([user_id], msg)
        
    except Exception as e:
        logger.error(f"[小影] 发送视频完成通知失败: {e}")


async def update_task_status(task_id: str, status: str, output_data: Dict[str, Any]):
    """更新任务状态"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            await db.execute(
                text("""
                    UPDATE ai_tasks 
                    SET status = :status, 
                        output_data = :output_data,
                        completed_at = CASE WHEN :status IN ('completed', 'failed') THEN NOW() ELSE completed_at END
                    WHERE id = :task_id
                """),
                {
                    "task_id": task_id,
                    "status": status,
                    "output_data": json.dumps(output_data, ensure_ascii=False, default=str)
                }
            )
            await db.commit()
    except Exception as e:
        logger.error(f"[小调] 更新任务状态失败: {e}")


async def send_task_result_to_user(user_id: str, task_id: str, agent_name: str, result: Dict[str, Any]):
    """将任务执行结果发送给用户"""
    try:
        if "error" in result:
            msg = f"""❌ 任务执行失败

🔖 任务ID: {task_id}
👤 执行者: {agent_name}
⚠️ 错误: {result['error']}

请检查任务描述后重试。"""
            await send_text_message([user_id], msg)
            return
        
        # 根据任务类型格式化结果
        task_type = result.get("task_type", "")
        executor = result.get("executor", agent_name)
        
        if task_type == "data_analysis":
            analysis = result.get("analysis_result", "")
            # 截取前2000字符，避免消息过长
            if len(analysis) > 1800:
                analysis = analysis[:1800] + "\n...(内容过长已截断)"
            
            msg = f"""📊 数据分析结果

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 分析结果：
{analysis}"""
            
        elif task_type == "copywriting":
            content = result.get("content", "")
            if len(content) > 1800:
                content = content[:1800] + "\n...(内容过长已截断)"
            
            msg = f"""✍️ 文案创作完成

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📝 文案内容：
{content}"""
            
        elif task_type == "lead_hunting":
            leads = result.get("leads_found", [])
            summary = result.get("summary", "")
            
            leads_text = ""
            if leads and len(leads) > 0:
                for i, lead in enumerate(leads[:5], 1):  # 最多显示5个
                    leads_text += f"\n{i}. {lead.get('company', lead.get('name', '未知'))}"
            else:
                leads_text = "\n暂无新线索"
            
            msg = f"""🔍 线索搜索完成

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 搜索结果：{leads_text}

💡 摘要：{summary[:500] if summary else '无'}"""
            
        elif task_type == "sales_response":
            response = result.get("response", "")
            if len(response) > 1800:
                response = response[:1800] + "\n...(内容过长已截断)"
            
            msg = f"""💬 销售咨询回复

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 回复建议：
{response}"""
            
        elif task_type == "follow_up":
            suggestion = result.get("suggestion", "")
            if len(suggestion) > 1800:
                suggestion = suggestion[:1800] + "\n...(内容过长已截断)"
            
            msg = f"""📞 跟进建议

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 跟进建议：
{suggestion}"""
            
        elif task_type == "video_creation":
            status = result.get("status", "")
            msg = f"""🎬 视频创作任务

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 状态：
{status}"""
            
        else:
            # 通用格式
            content = json.dumps(result, ensure_ascii=False, indent=2, default=str)
            if len(content) > 1800:
                content = content[:1800] + "\n...(内容过长已截断)"
            
            msg = f"""✅ 任务完成

🔖 任务ID: {task_id}
👤 执行者: {executor}
⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📋 执行结果：
{content}"""
        
        await send_text_message([user_id], msg)
        
        # 通知任务完成（可选：也通知其他管理员）
        # await notify_task_completion(task_id, executor, str(result)[:200])
        
    except Exception as e:
        logger.error(f"[小调] 发送任务结果失败: {e}")
        await send_text_message([user_id], f"任务已完成，但发送结果时出错：{str(e)}")


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
