"""
WebSocket管理器 - 用于AI员工实时工作直播
"""
from typing import Dict, List, Optional
from fastapi import WebSocket
from loguru import logger
import json
import asyncio


class WebSocketManager:
    """WebSocket连接管理器
    
    管理所有客户端的WebSocket连接，支持按员工类型订阅和广播消息
    """
    
    def __init__(self):
        # agent_type -> [websocket_connections]
        # "all" 表示订阅所有员工
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, agent_type: str = "all"):
        """建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            agent_type: 订阅的员工类型，"all"表示所有员工
        """
        await websocket.accept()
        async with self._lock:
            if agent_type not in self.active_connections:
                self.active_connections[agent_type] = []
            self.active_connections[agent_type].append(websocket)
        logger.info(f"WebSocket连接已建立: agent_type={agent_type}, 当前连接数={self.get_connection_count()}")
    
    async def disconnect(self, websocket: WebSocket, agent_type: str = "all"):
        """断开WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            agent_type: 订阅的员工类型
        """
        async with self._lock:
            if agent_type in self.active_connections:
                if websocket in self.active_connections[agent_type]:
                    self.active_connections[agent_type].remove(websocket)
                # 清理空列表
                if not self.active_connections[agent_type]:
                    del self.active_connections[agent_type]
        logger.info(f"WebSocket连接已断开: agent_type={agent_type}, 当前连接数={self.get_connection_count()}")
    
    async def broadcast_step(self, step: dict):
        """广播工作步骤到所有相关订阅者
        
        Args:
            step: 工作步骤数据
        """
        agent_type = step.get("agent_type", "")
        message = json.dumps(step, ensure_ascii=False, default=str)
        
        # 收集需要发送的连接
        connections_to_send = []
        
        async with self._lock:
            # 发送给订阅特定员工的客户端
            if agent_type in self.active_connections:
                connections_to_send.extend(self.active_connections[agent_type])
            
            # 发送给订阅所有员工的客户端
            if "all" in self.active_connections:
                connections_to_send.extend(self.active_connections["all"])
        
        # 去重
        connections_to_send = list(set(connections_to_send))
        
        # 发送消息
        disconnected = []
        for websocket in connections_to_send:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"发送WebSocket消息失败: {e}")
                disconnected.append(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            await self._remove_connection(ws)
    
    async def send_to_agent(self, agent_type: str, message: dict):
        """发送消息给订阅特定员工的客户端
        
        Args:
            agent_type: 员工类型
            message: 消息数据
        """
        message_str = json.dumps(message, ensure_ascii=False, default=str)
        
        async with self._lock:
            connections = self.active_connections.get(agent_type, []).copy()
        
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.warning(f"发送WebSocket消息失败: {e}")
                disconnected.append(websocket)
        
        for ws in disconnected:
            await self._remove_connection(ws)
    
    async def _remove_connection(self, websocket: WebSocket):
        """从所有订阅列表中移除连接"""
        async with self._lock:
            for agent_type in list(self.active_connections.keys()):
                if websocket in self.active_connections[agent_type]:
                    self.active_connections[agent_type].remove(websocket)
                if not self.active_connections[agent_type]:
                    del self.active_connections[agent_type]
    
    def get_connection_count(self) -> int:
        """获取当前总连接数"""
        count = 0
        for connections in self.active_connections.values():
            count += len(connections)
        return count
    
    def get_subscribers(self, agent_type: str) -> int:
        """获取特定员工的订阅者数量"""
        direct = len(self.active_connections.get(agent_type, []))
        all_subscribers = len(self.active_connections.get("all", []))
        return direct + all_subscribers
    
    async def stream_content(self, agent_type: str, session_id: str, content: str, 
                             title: str = "正在生成内容", chunk_size: int = 3, delay: float = 0.02):
        """流式传输内容（打字机效果）
        
        Args:
            agent_type: 员工类型
            session_id: 任务会话ID
            content: 要流式传输的完整内容
            title: 标题
            chunk_size: 每次发送的字符数
            delay: 每次发送之间的延迟（秒）
        """
        subscribers = self.get_subscribers(agent_type)
        logger.info(f"📺 开始流式传输: agent={agent_type}, subscribers={subscribers}, content_length={len(content)}")
        
        if subscribers == 0:
            logger.info(f"⚠️ 没有WebSocket订阅者，跳过流式传输")
            return
        
        # 首先发送开始流式传输的消息
        start_msg = {
            "type": "stream_start",
            "agent_type": agent_type,
            "session_id": session_id,
            "title": title,
            "total_length": len(content)
        }
        await self.broadcast_step(start_msg)
        
        # 逐块发送内容
        current_content = ""
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            current_content += chunk
            
            stream_msg = {
                "type": "stream_content",
                "agent_type": agent_type,
                "session_id": session_id,
                "chunk": chunk,
                "current_content": current_content,
                "progress": min(100, int((i + chunk_size) / len(content) * 100))
            }
            await self.broadcast_step(stream_msg)
            await asyncio.sleep(delay)
        
        # 发送流式传输结束消息
        end_msg = {
            "type": "stream_end",
            "agent_type": agent_type,
            "session_id": session_id,
            "title": title,
            "final_content": content,
            "total_length": len(content)
        }
        await self.broadcast_step(end_msg)


# 创建全局实例
websocket_manager = WebSocketManager()
