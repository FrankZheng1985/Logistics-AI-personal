"""
统一消息路由服务
将各渠道消息转换为统一格式，分发给AI员工处理，再将回复路由回原渠道
"""
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.agents.coordinator import coordinator
from app.agents.sales_agent import sales_agent
from app.agents.follow_agent import follow_agent
from app.agents.analyst import analyst_agent
from app.services.conversation_service import conversation_service
from app.services.notification import notification_service


class MessageType(str, Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    LINK = "link"
    EVENT = "event"  # 事件消息（如关注、菜单点击等）


class ChannelType(str, Enum):
    """渠道类型"""
    WECHAT_WORK = "wechat_work"      # 企业微信
    WECHAT_MP = "wechat_mp"          # 微信公众号
    WEBSITE = "website"              # 网站在线客服
    DOUYIN = "douyin"                # 抖音私信
    XIAOHONGSHU = "xiaohongshu"      # 小红书
    API = "api"                      # API直接调用
    TEST = "test"                    # 测试


@dataclass
class UnifiedMessage:
    """统一消息格式"""
    # 渠道信息
    channel: ChannelType
    channel_user_id: str              # 渠道用户唯一标识
    channel_message_id: Optional[str] = None  # 渠道消息ID
    
    # 系统关联
    customer_id: Optional[str] = None  # 系统客户ID（可能为空，首次接入时）
    
    # 消息内容
    message_type: MessageType = MessageType.TEXT
    content: str = ""
    
    # 媒体信息（如果是图片/语音/视频）
    media_url: Optional[str] = None
    media_id: Optional[str] = None
    
    # 元数据（各渠道特有数据）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "channel_user_id": self.channel_user_id,
            "channel_message_id": self.channel_message_id,
            "customer_id": self.customer_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "media_url": self.media_url,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class UnifiedReply:
    """统一回复格式"""
    content: str
    message_type: MessageType = MessageType.TEXT
    media_url: Optional[str] = None
    
    # 处理信息
    agent_type: str = "sales"
    intent_delta: int = 0
    intent_score: int = 0
    intent_level: str = "C"
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        # 渠道回复处理器注册表
        self._reply_handlers: Dict[ChannelType, Callable] = {}
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认的渠道回复处理器"""
        # 企业微信
        self._reply_handlers[ChannelType.WECHAT_WORK] = self._reply_wechat_work
        # 网站
        self._reply_handlers[ChannelType.WEBSITE] = self._reply_website
        # API
        self._reply_handlers[ChannelType.API] = self._reply_api
        # 测试
        self._reply_handlers[ChannelType.TEST] = self._reply_test
    
    def register_reply_handler(
        self, 
        channel: ChannelType, 
        handler: Callable
    ):
        """注册渠道回复处理器"""
        self._reply_handlers[channel] = handler
        logger.info(f"注册渠道处理器: {channel.value}")
    
    async def process_message(
        self, 
        message: UnifiedMessage
    ) -> UnifiedReply:
        """
        处理统一格式的消息
        
        流程:
        1. 匹配/创建客户
        2. 保存入站消息
        3. 判断分配给哪个AI员工
        4. AI员工处理消息
        5. 意向分析
        6. 保存出站消息
        7. 更新客户信息
        8. 触发通知（如需要）
        9. 路由回复到原渠道
        """
        logger.info(f"收到消息: 渠道={message.channel.value}, 用户={message.channel_user_id[:8]}...")
        
        # 1. 匹配/创建客户
        customer = await self._get_or_create_customer(message)
        message.customer_id = customer.get("id")
        customer_id = message.customer_id
        
        if not customer_id:
            logger.error("无法获取或创建客户")
            return UnifiedReply(
                content="抱歉，系统出现问题，请稍后再试。",
                agent_type="system"
            )
        
        # 1.5 自动检测客户语言（如果还是auto状态）
        customer_language = customer.get("language", "auto")
        if customer_language == "auto":
            from app.services.language_detector import language_detector
            detected_lang = language_detector.detect_customer_language(
                name=customer.get("name"),
                email=customer.get("email"),
                company=customer.get("company"),
                message=message.content
            )
            if detected_lang != "auto":
                # 更新客户语言
                await self._update_customer_language(customer_id, detected_lang)
                customer["language"] = detected_lang
                logger.info(f"自动检测到客户语言: {detected_lang}")
        
        # 2. 保存入站消息
        session_id = f"session_{customer_id}_{datetime.utcnow().strftime('%Y%m%d')}"
        await conversation_service.save_message(
            customer_id=customer_id,
            agent_type="sales",
            message_type="inbound",
            content=message.content,
            session_id=session_id
        )
        
        # 3. 判断分配给哪个AI员工
        is_new = customer.get("is_new", False)
        follow_count = customer.get("follow_count", 0)
        
        if is_new or follow_count == 0:
            target_agent = sales_agent
            agent_type = "sales"
            agent_name = "小销"
        else:
            target_agent = follow_agent
            agent_type = "follow"
            agent_name = "小跟"
        
        logger.info(f"分配给 {agent_name} 处理")
        
        # 4. 获取对话历史
        chat_history = await conversation_service.get_chat_history(customer_id, limit=10)
        history_text = "\n".join([
            f"[{'客户' if h['message_type'] == 'inbound' else 'AI'}] {h['content']}"
            for h in chat_history
        ])
        
        # 5. AI员工处理消息
        try:
            customer_info = f"姓名: {customer.get('name', '未知')}, 意向等级: {customer.get('intent_level', 'C')}"
            
            response = await target_agent.process({
                "customer_id": customer_id,
                "message": message.content,
                "customer_info": customer_info,
                "chat_history": history_text if history_text else "无历史对话"
            })
            
            reply_content = response.get("reply", "感谢您的咨询，我们会尽快回复您！")
            intent_signals = response.get("intent_signals", [])
            
        except Exception as e:
            logger.error(f"AI员工处理失败: {e}")
            reply_content = "感谢您的咨询！我是物流AI客服，请问有什么可以帮您的？"
            intent_signals = []
        
        # 6. 意向分析
        old_score = customer.get("intent_score", 0)
        old_level = customer.get("intent_level", "C")
        
        try:
            analysis_result = await analyst_agent.process({
                "customer_info": {
                    "name": customer.get("name"),
                    "current_score": old_score,
                    "current_level": old_level
                },
                "conversations": [
                    {"type": "inbound", "content": message.content},
                    {"type": "outbound", "content": reply_content}
                ],
                "intent_signals": intent_signals,
                "current_score": old_score
            })
            
            intent_delta = analysis_result.get("score_delta", 0)
            new_score = analysis_result.get("intent_score", old_score)
            new_level = analysis_result.get("intent_level", old_level)
            should_notify = analysis_result.get("should_notify", False)
            
        except Exception as e:
            logger.error(f"意向分析失败: {e}")
            intent_delta = 5
            new_score = max(0, old_score + intent_delta)
            new_level = old_level
            should_notify = False
        
        # 7. 保存出站消息
        await conversation_service.save_message(
            customer_id=customer_id,
            agent_type=agent_type,
            message_type="outbound",
            content=reply_content,
            intent_delta=intent_delta,
            session_id=session_id
        )
        
        # 8. 更新客户信息
        update_result = await conversation_service.update_customer_intent(
            customer_id=customer_id,
            intent_delta=intent_delta,
            new_score=new_score
        )
        await conversation_service.update_customer_contact(customer_id)
        
        # 9. 触发通知（如果升级为高意向）
        if should_notify or update_result.get("upgraded_to_high", False):
            try:
                await notification_service.notify_high_intent_customer(
                    customer_id=customer_id,
                    customer_name=customer.get("name", "未知客户"),
                    intent_score=new_score,
                    intent_level=new_level,
                    key_signals=intent_signals,
                    last_message=message.content
                )
            except Exception as e:
                logger.error(f"发送通知失败: {e}")
        
        # 构建回复
        reply = UnifiedReply(
            content=reply_content,
            agent_type=agent_type,
            intent_delta=intent_delta,
            intent_score=new_score,
            intent_level=new_level,
            metadata={
                "customer_id": customer_id,
                "session_id": session_id,
                "agent_name": agent_name
            }
        )
        
        # 10. 路由回复到原渠道
        await self._route_reply(message, reply)
        
        logger.info(f"消息处理完成: 客户={customer.get('name')}, 意向={old_level}->{new_level}")
        
        return reply
    
    async def _get_or_create_customer(
        self, 
        message: UnifiedMessage
    ) -> Dict[str, Any]:
        """根据渠道信息获取或创建客户"""
        # 根据不同渠道构建唯一标识
        channel_id = f"{message.channel.value}:{message.channel_user_id}"
        
        return await conversation_service.get_or_create_customer(
            wechat_id=channel_id,
            name=message.metadata.get("user_name"),
            channel=message.channel.value
        )
    
    async def _update_customer_language(self, customer_id: str, language: str):
        """更新客户语言偏好"""
        from app.models.database import async_session_maker
        from sqlalchemy import text
        
        async with async_session_maker() as db:
            try:
                await db.execute(
                    text("UPDATE customers SET language = :language, updated_at = NOW() WHERE id = :id"),
                    {"language": language, "id": customer_id}
                )
                await db.commit()
                logger.info(f"更新客户语言: {customer_id} -> {language}")
            except Exception as e:
                logger.error(f"更新客户语言失败: {e}")
    
    async def _route_reply(
        self, 
        message: UnifiedMessage, 
        reply: UnifiedReply
    ):
        """路由回复到原渠道"""
        handler = self._reply_handlers.get(message.channel)
        
        if handler:
            try:
                await handler(message, reply)
            except Exception as e:
                logger.error(f"渠道回复失败 [{message.channel.value}]: {e}")
        else:
            logger.warning(f"未找到渠道处理器: {message.channel.value}")
    
    async def _reply_wechat_work(
        self, 
        message: UnifiedMessage, 
        reply: UnifiedReply
    ):
        """企业微信回复"""
        try:
            from app.services.wechat import wechat_service
            await wechat_service.send_text_message(
                user_ids=[message.channel_user_id],
                content=reply.content
            )
            logger.info(f"企业微信回复发送成功")
        except Exception as e:
            logger.error(f"企业微信回复失败: {e}")
    
    async def _reply_website(
        self, 
        message: UnifiedMessage, 
        reply: UnifiedReply
    ):
        """网站在线客服回复（通过WebSocket或回调）"""
        # TODO: 实现网站客服回复逻辑
        # 可以通过WebSocket推送，或者等待前端轮询
        logger.info(f"网站客服回复准备就绪，等待前端获取")
    
    async def _reply_api(
        self, 
        message: UnifiedMessage, 
        reply: UnifiedReply
    ):
        """API调用直接返回，无需额外处理"""
        pass
    
    async def _reply_test(
        self, 
        message: UnifiedMessage, 
        reply: UnifiedReply
    ):
        """测试渠道，仅记录日志"""
        logger.info(f"[TEST] 回复: {reply.content[:50]}...")
    
    # =====================================================
    # 渠道适配器：将各渠道原始消息转换为统一格式
    # =====================================================
    
    @staticmethod
    def from_wechat_work(raw_message: Dict[str, Any]) -> UnifiedMessage:
        """从企业微信消息转换"""
        return UnifiedMessage(
            channel=ChannelType.WECHAT_WORK,
            channel_user_id=raw_message.get("FromUserName", ""),
            channel_message_id=raw_message.get("MsgId"),
            message_type=MessageType.TEXT if raw_message.get("MsgType") == "text" else MessageType.EVENT,
            content=raw_message.get("Content", ""),
            metadata={
                "agent_id": raw_message.get("AgentID"),
                "create_time": raw_message.get("CreateTime"),
                "msg_type": raw_message.get("MsgType")
            }
        )
    
    @staticmethod
    def from_website(
        user_id: str,
        content: str,
        session_id: Optional[str] = None
    ) -> UnifiedMessage:
        """从网站客服消息转换"""
        return UnifiedMessage(
            channel=ChannelType.WEBSITE,
            channel_user_id=user_id,
            channel_message_id=session_id,
            message_type=MessageType.TEXT,
            content=content,
            metadata={
                "session_id": session_id
            }
        )
    
    @staticmethod
    def from_api(
        customer_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> UnifiedMessage:
        """从API调用转换"""
        return UnifiedMessage(
            channel=ChannelType.API,
            channel_user_id=customer_id,
            customer_id=customer_id,
            message_type=MessageType.TEXT,
            content=content,
            metadata=metadata or {}
        )


# 创建单例
message_router = MessageRouter()
