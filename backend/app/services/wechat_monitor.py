"""
微信群监控服务
对接WeChatFerry实现个人微信群消息监控
注意：只监控不发言，最大程度降低风险
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.core.config import settings


class WeChatMonitorService:
    """
    微信群监控服务
    
    对接WeChatFerry实现消息监控
    WeChatFerry运行在Windows虚拟机中，通过HTTP API与本服务通信
    """
    
    def __init__(self):
        # WeChatFerry服务地址（VirtualBox虚拟机中）
        self.wcf_api_url = getattr(settings, 'WCF_API_URL', 'http://192.168.1.100:10086')
        self.is_connected = False
        self.message_handlers: List[Callable] = []
        self.monitored_groups: Dict[str, Dict] = {}
    
    async def connect(self) -> bool:
        """
        连接WeChatFerry服务
        """
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.wcf_api_url}/api/status", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    self.is_connected = data.get("is_login", False)
                    
                    if self.is_connected:
                        logger.info("✅ WeChatFerry连接成功，微信已登录")
                        # 加载监控群列表
                        await self._load_monitored_groups()
                    else:
                        logger.warning("⚠️ WeChatFerry已连接，但微信未登录，请扫码登录")
                    
                    return self.is_connected
                else:
                    logger.error(f"WeChatFerry连接失败: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"WeChatFerry连接异常: {e}")
            logger.info("提示: 请确保VirtualBox虚拟机正在运行，且WeChatFerry服务已启动")
            return False
    
    async def _load_monitored_groups(self):
        """加载监控的群列表"""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT group_id, group_name, group_type, keywords
                        FROM wechat_groups
                        WHERE is_monitored = true
                    """)
                )
                rows = result.fetchall()
                
                for row in rows:
                    self.monitored_groups[row[0]] = {
                        "name": row[1],
                        "type": row[2],
                        "keywords": row[3] or []
                    }
                
                logger.info(f"📱 已加载 {len(self.monitored_groups)} 个监控群")
                
        except Exception as e:
            logger.error(f"加载监控群列表失败: {e}")
    
    def add_message_handler(self, handler: Callable):
        """添加消息处理器"""
        self.message_handlers.append(handler)
    
    async def start_listening(self):
        """
        开始监听消息
        通过轮询WeChatFerry的消息队列
        """
        if not self.is_connected:
            logger.warning("未连接WeChatFerry，无法开始监听")
            return
        
        logger.info("📱 开始监听微信群消息...")
        
        import httpx
        
        while self.is_connected:
            try:
                async with httpx.AsyncClient() as client:
                    # 获取新消息
                    response = await client.get(
                        f"{self.wcf_api_url}/api/messages",
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        messages = response.json().get("messages", [])
                        
                        for msg in messages:
                            await self._handle_message(msg)
                
                # 短暂休眠
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("消息监听已停止")
                break
            except Exception as e:
                logger.error(f"消息监听异常: {e}")
                await asyncio.sleep(5)
    
    async def _handle_message(self, raw_message: Dict[str, Any]):
        """
        处理原始消息
        """
        try:
            msg_type = raw_message.get("type", 0)
            
            # 只处理群消息
            if not raw_message.get("is_group", False):
                return
            
            # 只处理文本消息 (type=1)
            if msg_type != 1:
                return
            
            group_id = raw_message.get("roomid", "")
            
            # 检查是否是监控的群
            if group_id not in self.monitored_groups and not self._should_auto_monitor(raw_message):
                return
            
            # 构建标准消息格式
            message = {
                "group_id": group_id,
                "group_name": self.monitored_groups.get(group_id, {}).get("name", "未知群"),
                "sender_id": raw_message.get("sender", ""),
                "sender_name": raw_message.get("sender_name", ""),
                "content": raw_message.get("content", ""),
                "message_type": "text",
                "timestamp": raw_message.get("timestamp", datetime.now().isoformat())
            }
            
            # 保存消息到数据库
            await self._save_message(message)
            
            # 调用所有处理器
            for handler in self.message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"消息处理器异常: {e}")
                    
        except Exception as e:
            logger.error(f"处理消息异常: {e}")
    
    def _should_auto_monitor(self, raw_message: Dict[str, Any]) -> bool:
        """
        判断是否应该自动监控这个群
        基于群名称关键词判断
        """
        group_name = raw_message.get("room_name", "")
        
        # 物流相关群名关键词
        logistics_keywords = [
            "物流", "货代", "清关", "报关", "外贸",
            "跨境", "电商", "FBA", "欧洲", "国际"
        ]
        
        for kw in logistics_keywords:
            if kw in group_name:
                return True
        
        return False
    
    async def _save_message(self, message: Dict[str, Any]):
        """保存消息到数据库"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO wechat_messages 
                        (group_id, sender_id, sender_name, content, message_type, created_at)
                        VALUES (:group_id, :sender_id, :sender_name, :content, :message_type, NOW())
                    """),
                    {
                        "group_id": message["group_id"],
                        "sender_id": message["sender_id"],
                        "sender_name": message["sender_name"],
                        "content": message["content"],
                        "message_type": message["message_type"]
                    }
                )
                
                # 更新群的最后消息时间
                await db.execute(
                    text("""
                        UPDATE wechat_groups
                        SET last_message_at = NOW(),
                            message_count = message_count + 1
                        WHERE group_id = :group_id
                    """),
                    {"group_id": message["group_id"]}
                )
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
    
    async def add_monitored_group(
        self,
        group_id: str,
        group_name: str,
        group_type: str = "logistics",
        keywords: List[str] = None
    ) -> bool:
        """
        添加监控群
        """
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO wechat_groups 
                        (group_id, group_name, group_type, keywords, is_monitored, created_at)
                        VALUES (:group_id, :group_name, :group_type, :keywords, true, NOW())
                        ON CONFLICT (group_id) DO UPDATE 
                        SET group_name = :group_name,
                            group_type = :group_type,
                            keywords = :keywords,
                            is_monitored = true
                    """),
                    {
                        "group_id": group_id,
                        "group_name": group_name,
                        "group_type": group_type,
                        "keywords": keywords or []
                    }
                )
                await db.commit()
            
            # 更新内存中的监控列表
            self.monitored_groups[group_id] = {
                "name": group_name,
                "type": group_type,
                "keywords": keywords or []
            }
            
            logger.info(f"📱 添加监控群: {group_name}")
            return True
            
        except Exception as e:
            logger.error(f"添加监控群失败: {e}")
            return False
    
    async def remove_monitored_group(self, group_id: str) -> bool:
        """
        移除监控群
        """
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE wechat_groups
                        SET is_monitored = false
                        WHERE group_id = :group_id
                    """),
                    {"group_id": group_id}
                )
                await db.commit()
            
            if group_id in self.monitored_groups:
                del self.monitored_groups[group_id]
            
            logger.info(f"📱 移除监控群: {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"移除监控群失败: {e}")
            return False
    
    async def get_group_list(self) -> List[Dict[str, Any]]:
        """
        获取微信群列表
        """
        if not self.is_connected:
            return []
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.wcf_api_url}/api/contacts", timeout=10.0)
                
                if response.status_code == 200:
                    contacts = response.json().get("contacts", [])
                    # 过滤出群聊
                    groups = [c for c in contacts if c.get("type") == "chatroom"]
                    return groups
                    
        except Exception as e:
            logger.error(f"获取群列表失败: {e}")
        
        return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取监控统计
        """
        try:
            async with async_session_maker() as db:
                # 今日消息统计
                result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_messages,
                            COUNT(DISTINCT group_id) as active_groups,
                            COUNT(*) FILTER (WHERE is_valuable = true) as valuable_messages
                        FROM wechat_messages
                        WHERE DATE(created_at) = CURRENT_DATE
                    """)
                )
                today_stats = result.fetchone()
                
                # 各群消息量
                result = await db.execute(
                    text("""
                        SELECT g.group_name, COUNT(m.id) as message_count
                        FROM wechat_groups g
                        LEFT JOIN wechat_messages m ON g.group_id = m.group_id
                            AND DATE(m.created_at) = CURRENT_DATE
                        WHERE g.is_monitored = true
                        GROUP BY g.group_id, g.group_name
                        ORDER BY message_count DESC
                        LIMIT 10
                    """)
                )
                group_stats = result.fetchall()
                
                return {
                    "is_connected": self.is_connected,
                    "monitored_groups": len(self.monitored_groups),
                    "today": {
                        "total_messages": today_stats[0] if today_stats else 0,
                        "active_groups": today_stats[1] if today_stats else 0,
                        "valuable_messages": today_stats[2] if today_stats else 0
                    },
                    "top_groups": [
                        {"name": row[0], "messages": row[1]}
                        for row in group_stats
                    ]
                }
                
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {"error": str(e)}


# 创建单例
wechat_monitor = WeChatMonitorService()


async def setup_wechat_monitor():
    """
    设置微信监控
    在应用启动时调用
    """
    from app.agents.analyst2 import analyst2_agent
    
    # 连接WeChatFerry
    connected = await wechat_monitor.connect()
    
    if not connected:
        logger.warning("微信监控未启动：WeChatFerry未连接")
        logger.info("请按以下步骤启动微信监控：")
        logger.info("1. 启动VirtualBox中的Windows虚拟机")
        logger.info("2. 在虚拟机中启动WeChatFerry")
        logger.info("3. 在PC微信中扫码登录")
        logger.info("4. 重启本服务")
        return
    
    # 添加消息处理器
    async def process_message(message: Dict[str, Any]):
        """处理收到的微信消息"""
        # 使用小析2分析消息
        analysis = await analyst2_agent.process(message)
        
        if analysis.get("is_valuable"):
            # 更新消息的分析结果
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE wechat_messages
                        SET is_valuable = true,
                            analysis_result = :analysis
                        WHERE group_id = :group_id
                        AND content = :content
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {
                        "group_id": message["group_id"],
                        "content": message["content"],
                        "analysis": json.dumps(analysis, ensure_ascii=False)
                    }
                )
                await db.commit()
            
            # 如果是潜在线索，通知小调分配
            if analysis.get("category") == "lead":
                from app.services.task_queue import task_queue
                
                await task_queue.enqueue(
                    task_type="analyze",
                    task_data={
                        "source": "wechat_group",
                        "content": message["content"],
                        "analysis": analysis,
                        "action": "dispatch_lead"
                    },
                    priority=7
                )
    
    wechat_monitor.add_message_handler(process_message)
    
    # 启动监听（在后台运行）
    asyncio.create_task(wechat_monitor.start_listening())
    
    logger.info("✅ 微信群监控已启动")
