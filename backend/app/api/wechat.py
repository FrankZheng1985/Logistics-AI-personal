"""
企业微信回调API
"""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.services.wechat import wechat_service
from app.agents.sales_agent import SalesAgent

router = APIRouter(prefix="/wechat", tags=["企业微信"])


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


@router.post("/callback")
async def receive_message(
    request: Request,
    msg_signature: str = Query(..., description="签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数")
):
    """
    接收企业微信消息
    企业微信服务器会发送POST请求推送消息
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
            user_id = message.get("FromUserName")
            content = message.get("Content")
            
            logger.info(f"收到用户 {user_id} 的消息: {content}")
            
            # 使用AI销售客服回复
            try:
                sales_agent = SalesAgent()
                
                # 生成AI回复
                response = await sales_agent.process({
                    "customer_id": user_id,
                    "message": content,
                    "context": {}
                })
                
                reply_content = response.get("reply", "感谢您的咨询，我们会尽快回复您！")
                
                # 发送回复
                await wechat_service.send_text_message([user_id], reply_content)
                
                logger.info(f"已回复用户 {user_id}: {reply_content[:50]}...")
                
            except Exception as e:
                logger.error(f"AI回复失败: {e}")
                # 发送默认回复
                await wechat_service.send_text_message(
                    [user_id], 
                    "感谢您的咨询！我是物流AI客服，正在为您查询，请稍候..."
                )
        
        # 返回success表示消息已接收
        return PlainTextResponse(content="success")
        
    except Exception as e:
        logger.error(f"❌ 处理企业微信消息失败: {e}")
        return PlainTextResponse(content="success")  # 仍返回success避免重试
