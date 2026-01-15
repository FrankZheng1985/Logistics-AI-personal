"""
企业微信回调API
支持：
1. 外部客户消息 - 小销自动回复
2. 内部员工消息 - 小销协助模式
3. 群聊消息 - 小析2分析并存入知识库
"""
import asyncio
from collections import OrderedDict
from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.services.wechat import wechat_service
from app.services.conversation_service import conversation_service
from app.agents.sales_agent import SalesAgent
from app.agents.analyst2 import analyst2_agent
from app.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/wechat", tags=["企业微信"])

# 消息去重缓存 - 存储已处理的消息ID，最多保留1000条
_processed_messages = OrderedDict()
_MAX_CACHE_SIZE = 1000


def is_message_processed(msg_id: str) -> bool:
    """检查消息是否已处理过"""
    if msg_id in _processed_messages:
        return True
    return False


def mark_message_processed(msg_id: str):
    """标记消息为已处理"""
    _processed_messages[msg_id] = True
    # 超过最大缓存数量时，删除最早的记录
    while len(_processed_messages) > _MAX_CACHE_SIZE:
        _processed_messages.popitem(last=False)


@router.get("/config-status")
async def get_wechat_config_status():
    """
    获取企业微信配置状态
    """
    return {
        "is_configured": wechat_service.is_configured,
        "is_callback_configured": wechat_service.is_callback_configured,
        "corp_id_masked": wechat_service.corp_id[:6] + "****" if wechat_service.corp_id else None,
        "agent_id": wechat_service.agent_id,
        "status": "configured" if wechat_service.is_configured else "pending"
    }


@router.get("/callback")
async def verify_callback(
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="加密的随机字符串")
):
    """
    企业微信回调URL验证
    企业微信服务器会发送GET请求验证URL有效性
    """
    try:
        logger.info(f"收到企业微信URL验证请求: timestamp={timestamp}, nonce={nonce}")
        logger.info(f"msg_signature={msg_signature}")
        logger.info(f"echostr={echostr[:50]}...")
        
        # 验证签名并解密echostr
        decrypted = wechat_service.verify_url(msg_signature, timestamp, nonce, echostr)
        
        logger.info("✅ 企业微信URL验证成功")
        return PlainTextResponse(content=decrypted)
        
    except Exception as e:
        logger.error(f"❌ 企业微信URL验证失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=403, detail=str(e))


async def process_external_message(message: dict):
    """
    处理外部客户消息 - 使用销售客服模式
    """
    try:
        user_id = message.get("FromUserName")
        content = message.get("Content")
        
        logger.info(f"[外部客户] 开始处理用户 {user_id} 的消息: {content}")
        
        # 1. 获取或创建客户记录
        customer = await conversation_service.get_or_create_customer(user_id)
        customer_id = customer.get("id")
        
        # 2. 保存用户消息到数据库
        if customer_id:
            await conversation_service.save_message(
                customer_id=customer_id,
                agent_type="sales",
                message_type="inbound",
                content=content,
                intent_delta=5  # 每次咨询+5分
            )
            # 更新客户意向分数
            await conversation_service.update_customer_intent(customer_id, 5)
        
        # 3. 使用AI销售客服回复
        try:
            sales_agent = SalesAgent()
            
            # 生成AI回复
            response = await sales_agent.process({
                "customer_id": user_id,
                "message": content,
                "context": {"user_type": "external"}
            })
            
            reply_content = response.get("reply", "感谢您的咨询，我们会尽快回复您！")
            
            # 4. 保存AI回复到数据库
            if customer_id:
                await conversation_service.save_message(
                    customer_id=customer_id,
                    agent_type="sales",
                    message_type="outbound",
                    content=reply_content
                )
            
            # 5. 发送回复给用户
            await wechat_service.send_text_message([user_id], reply_content)
            
            # 6. 记录AI员工任务完成
            await conversation_service.record_agent_task("sales", success=True)
            
            logger.info(f"[外部客户] 已回复用户 {user_id}: {reply_content[:50]}...")
            
        except Exception as e:
            logger.error(f"[外部客户] AI回复失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 发送默认回复
            default_reply = "感谢您的咨询！我是物流AI客服，正在为您查询，请稍候..."
            if customer_id:
                await conversation_service.save_message(
                    customer_id=customer_id,
                    agent_type="sales",
                    message_type="outbound",
                    content=default_reply
                )
            await wechat_service.send_text_message([user_id], default_reply)
            
    except Exception as e:
        logger.error(f"[外部客户] 处理消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def process_internal_message(message: dict):
    """
    处理内部员工消息 - 使用同事协助模式
    """
    try:
        user_id = message.get("FromUserName")
        content = message.get("Content")
        
        logger.info(f"[内部同事] 开始处理同事 {user_id} 的消息: {content}")
        
        # 使用AI回复，但使用同事模式
        try:
            sales_agent = SalesAgent()
            
            # 生成AI回复 - 传递内部用户标识
            response = await sales_agent.process({
                "customer_id": user_id,
                "message": content,
                "context": {"user_type": "internal"}
            })
            
            reply_content = response.get("reply", "收到，我来处理一下~")
            
            # 发送回复给同事
            await wechat_service.send_text_message([user_id], reply_content)
            
            logger.info(f"[内部同事] 已回复同事 {user_id}: {reply_content[:50]}...")
            
        except Exception as e:
            logger.error(f"[内部同事] AI回复失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 发送默认回复
            default_reply = "收到，稍等我看看~"
            await wechat_service.send_text_message([user_id], default_reply)
            
    except Exception as e:
        logger.error(f"[内部同事] 处理消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def process_group_message(message: dict):
    """
    处理企业微信群消息 - 小析2分析并存入知识库
    注意：小析2只分析不回复
    """
    try:
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        
        chat_id = message.get("ChatId", "")  # 企业微信群ID
        user_id = message.get("FromUserName", "")
        content = message.get("Content", "")
        msg_id = message.get("MsgId", "")
        
        # 获取群名称（从缓存或API）
        group_name = await wechat_service.get_group_name(chat_id)
        
        # 获取发送者名称
        sender_name = await wechat_service.get_user_name(user_id)
        
        logger.info(f"[群消息] 群:{group_name} 发送者:{sender_name} 内容:{content[:50]}...")
        
        # 调用小析2分析消息
        analysis = await analyst2_agent.process({
            "group_id": chat_id,
            "group_name": group_name,
            "sender_name": sender_name,
            "content": content,
            "message_type": "text"
        })
        
        # 保存消息和分析结果到数据库
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO wechat_messages 
                    (group_id, sender_id, sender_name, content, is_valuable, 
                     analysis_result, created_at)
                    VALUES (:group_id, :sender_id, :sender_name, :content, :is_valuable,
                            :analysis_result, NOW())
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
        
        # 如果是有价值的信息，根据类别处理
        if analysis.get("is_valuable"):
            category = analysis.get("category", "")
            summary = analysis.get("summary", "")
            
            logger.info(f"[群消息] 发现有价值信息: {category} - {summary}")
            
            # 记录小析2的任务完成
            await conversation_service.record_agent_task("analyst2", success=True)
            
            if category == "lead":
                # 线索类 - 创建线索记录
                await _create_lead_from_group(analysis, chat_id, content)
                
            elif category == "intel":
                # 情报类 - 存入知识库
                await _save_intel_to_knowledge(analysis, group_name, content)
                
            elif category == "knowledge":
                # 知识类 - 存入知识库
                await _save_knowledge_from_group(analysis, group_name, content)
        
    except Exception as e:
        logger.error(f"[群消息] 处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def _create_lead_from_group(analysis: dict, group_id: str, content: str):
    """从群消息创建线索"""
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
                            :contact_info, 'new', :quality_score, NOW())
                """),
                {
                    "id": lead_id,
                    "source_url": f"wechat://group/{group_id}",
                    "title": analysis.get("summary", "微信群线索")[:100],
                    "content": content,
                    "contact_info": contact_info,
                    "quality_score": analysis.get("confidence", 50)
                }
            )
            await db.commit()
            
            logger.info(f"[群消息] 已创建线索: {lead_id}")
            
    except Exception as e:
        logger.error(f"[群消息] 创建线索失败: {e}")


async def _save_intel_to_knowledge(analysis: dict, group_name: str, content: str):
    """将情报存入知识库"""
    try:
        key_info = analysis.get("key_info", {})
        
        # 提取关键词
        keywords = []
        if key_info.get("price_info"):
            keywords.append("运价")
        if key_info.get("policy_info"):
            keywords.append("政策")
        
        await knowledge_service.add_knowledge(
            category="market_intel",
            title=f"[群情报] {analysis.get('summary', '行业动态')[:50]}",
            content=content,
            summary=analysis.get("summary"),
            keywords=keywords + analysis.get("keyword_matches", []),
            source=f"企业微信群: {group_name}"
        )
        
        logger.info(f"[群消息] 情报已存入知识库")
        
    except Exception as e:
        logger.error(f"[群消息] 保存情报失败: {e}")


async def _save_knowledge_from_group(analysis: dict, group_name: str, content: str):
    """将知识存入知识库"""
    try:
        await knowledge_service.add_knowledge(
            category="case",  # 案例经验
            title=f"[群分享] {analysis.get('summary', '经验分享')[:50]}",
            content=content,
            summary=analysis.get("summary"),
            keywords=analysis.get("keyword_matches", []),
            source=f"企业微信群: {group_name}",
            experience_level="intermediate"
        )
        
        logger.info(f"[群消息] 知识已存入知识库")
        
    except Exception as e:
        logger.error(f"[群消息] 保存知识失败: {e}")


@router.post("/callback")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数")
):
    """
    接收企业微信消息
    企业微信服务器会发送POST请求推送消息
    
    重要：必须在3秒内返回success，否则企业微信会重试
    因此先返回success，然后在后台异步处理消息
    """
    try:
        # 获取XML数据
        xml_data = await request.body()
        xml_str = xml_data.decode("utf-8")
        
        logger.info(f"收到企业微信消息: timestamp={timestamp}")
        
        # 解析消息
        message = wechat_service.parse_message(msg_signature, timestamp, nonce, xml_str)
        
        logger.info(f"解析消息: {message}")
        
        # 处理文本消息
        if message.get("MsgType") == "text":
            msg_id = message.get("MsgId")
            user_id = message.get("FromUserName")
            content = message.get("Content")
            chat_id = message.get("ChatId")  # 群聊ID（如果是群消息）
            
            # 消息去重检查
            if msg_id and is_message_processed(msg_id):
                logger.info(f"⏭️ 跳过重复消息: MsgId={msg_id}, 用户={user_id}")
                return PlainTextResponse(content="success")
            
            # 标记消息为已处理
            if msg_id:
                mark_message_processed(msg_id)
            
            # 判断消息类型：群消息 vs 私聊消息
            if chat_id:
                # 群消息 - 交给小析2分析（不回复）
                logger.info(f"收到群消息: 群ID={chat_id}, 用户={user_id}, 内容={content[:30]}...")
                background_tasks.add_task(process_group_message, message)
            else:
                # 私聊消息 - 根据用户类型处理
                user_type = wechat_service.get_user_type(user_id)
                logger.info(f"收到私聊消息: 用户={user_id} ({user_type}), 内容={content} (MsgId={msg_id})")
                
                if user_type == "external":
                    # 外部客户 - 使用销售客服模式
                    background_tasks.add_task(process_external_message, message)
                else:
                    # 内部员工 - 使用同事协助模式
                    background_tasks.add_task(process_internal_message, message)
        
        # 立即返回success，避免企业微信重试
        return PlainTextResponse(content="success")
        
    except Exception as e:
        logger.error(f"❌ 处理企业微信消息失败: {e}")
        return PlainTextResponse(content="success")  # 仍返回success避免重试
