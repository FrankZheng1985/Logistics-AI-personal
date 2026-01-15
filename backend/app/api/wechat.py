"""
企业微信回调API
"""
import asyncio
from collections import OrderedDict
from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.services.wechat import wechat_service
from app.services.conversation_service import conversation_service
from app.agents.sales_agent import SalesAgent

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


async def process_wechat_message(message: dict):
    """
    后台异步处理企业微信消息
    """
    try:
        user_id = message.get("FromUserName")
        content = message.get("Content")
        
        logger.info(f"[后台处理] 开始处理用户 {user_id} 的消息: {content}")
        
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
                "context": {}
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
            
            logger.info(f"[后台处理] 已回复用户 {user_id}: {reply_content[:50]}...")
            
        except Exception as e:
            logger.error(f"[后台处理] AI回复失败: {e}")
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
        logger.error(f"[后台处理] 处理消息失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


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
            
            # 消息去重检查
            if msg_id and is_message_processed(msg_id):
                logger.info(f"⏭️ 跳过重复消息: MsgId={msg_id}, 用户={user_id}")
                return PlainTextResponse(content="success")
            
            # 标记消息为已处理
            if msg_id:
                mark_message_processed(msg_id)
            
            # 判断用户类型
            user_type = wechat_service.get_user_type(user_id)
            logger.info(f"收到用户 {user_id} ({user_type}) 的消息: {content} (MsgId={msg_id})")
            
            # 只处理外部客户的消息，内部员工不自动回复
            if user_type == "external":
                # 在后台异步处理消息，立即返回success
                background_tasks.add_task(process_wechat_message, message)
            else:
                logger.info(f"⏭️ 跳过内部员工消息: 用户={user_id}")
        
        # 立即返回success，避免企业微信重试
        return PlainTextResponse(content="success")
        
    except Exception as e:
        logger.error(f"❌ 处理企业微信消息失败: {e}")
        return PlainTextResponse(content="success")  # 仍返回success避免重试
