"""
网站在线客服API
提供WebSocket实时聊天和HTTP接口
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.agents.sales_agent import sales_agent

router = APIRouter(prefix="/webchat", tags=["网站客服"])


# 活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": datetime.now().isoformat(),
            "message_count": 0
        }
        logger.info(f"🌐 WebChat连接: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        logger.info(f"🌐 WebChat断开: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(session_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        for session_id in list(self.active_connections.keys()):
            await self.send_message(session_id, message)
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket聊天端点
    
    消息格式:
    发送: {"type": "message", "content": "用户消息"}
    接收: {"type": "message", "content": "AI回复", "sender": "ai"}
    """
    await manager.connect(websocket, session_id)
    
    try:
        # 发送欢迎消息
        await manager.send_message(session_id, {
            "type": "system",
            "content": "您好！我是小销，欧洲物流专家。有什么可以帮您的吗？",
            "sender": "ai",
            "timestamp": datetime.now().isoformat()
        })
        
        # 保存会话记录
        await _save_session(session_id)
        
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                user_message = data.get("content", "")
                
                if not user_message.strip():
                    continue
                
                # 保存用户消息
                await _save_message(session_id, user_message, "user")
                
                # 发送"正在输入"状态
                await manager.send_message(session_id, {
                    "type": "typing",
                    "sender": "ai"
                })
                
                # 调用小销处理
                try:
                    response = await sales_agent.process({
                        "customer_message": user_message,
                        "channel": "webchat",
                        "session_id": session_id
                    })
                    
                    ai_reply = response.get("reply", "抱歉，我没有理解您的意思。")
                    
                except Exception as e:
                    logger.error(f"AI处理失败: {e}")
                    ai_reply = "抱歉，系统暂时繁忙，请稍后再试。"
                
                # 保存AI回复
                await _save_message(session_id, ai_reply, "ai")
                
                # 发送AI回复
                await manager.send_message(session_id, {
                    "type": "message",
                    "content": ai_reply,
                    "sender": "ai",
                    "timestamp": datetime.now().isoformat()
                })
                
            elif data.get("type") == "ping":
                await manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        await _close_session(session_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(session_id)


async def _save_session(session_id: str):
    """保存会话记录"""
    try:
        async with async_session_maker() as db:
            await db.execute(
                text("""
                    INSERT INTO webchat_sessions 
                    (session_id, status, started_at, created_at)
                    VALUES (:session_id, 'active', NOW(), NOW())
                    ON CONFLICT (session_id) DO UPDATE 
                    SET status = 'active'
                """),
                {"session_id": session_id}
            )
            await db.commit()
    except Exception as e:
        logger.error(f"保存会话失败: {e}")


async def _close_session(session_id: str):
    """关闭会话"""
    try:
        async with async_session_maker() as db:
            await db.execute(
                text("""
                    UPDATE webchat_sessions
                    SET status = 'closed', ended_at = NOW()
                    WHERE session_id = :session_id
                """),
                {"session_id": session_id}
            )
            await db.commit()
    except Exception as e:
        logger.error(f"关闭会话失败: {e}")


async def _save_message(session_id: str, content: str, sender: str):
    """保存消息"""
    try:
        async with async_session_maker() as db:
            await db.execute(
                text("""
                    INSERT INTO webchat_messages 
                    (session_id, content, sender, created_at)
                    VALUES (:session_id, :content, :sender, NOW())
                """),
                {
                    "session_id": session_id,
                    "content": content,
                    "sender": sender
                }
            )
            await db.commit()
    except Exception as e:
        logger.error(f"保存消息失败: {e}")


@router.post("/session")
async def create_session():
    """
    创建新的聊天会话
    返回session_id供WebSocket连接使用
    """
    session_id = str(uuid4())
    await _save_session(session_id)
    
    return {
        "session_id": session_id,
        "websocket_url": f"/api/webchat/ws/{session_id}"
    }


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, limit: int = Query(50, le=200)):
    """获取会话历史消息"""
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT content, sender, created_at
                    FROM webchat_messages
                    WHERE session_id = :session_id
                    ORDER BY created_at ASC
                    LIMIT :limit
                """),
                {"session_id": session_id, "limit": limit}
            )
            messages = result.fetchall()
            
            return {
                "session_id": session_id,
                "messages": [
                    {
                        "content": row[0],
                        "sender": row[1],
                        "timestamp": row[2].isoformat() if row[2] else None
                    }
                    for row in messages
                ]
            }
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/message")
async def send_http_message(session_id: str, content: str):
    """
    HTTP方式发送消息（备选方案）
    用于不支持WebSocket的场景
    """
    if not content.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    
    # 保存用户消息
    await _save_message(session_id, content, "user")
    
    # 调用AI处理
    try:
        response = await sales_agent.process({
            "customer_message": content,
            "channel": "webchat",
            "session_id": session_id
        })
        
        ai_reply = response.get("reply", "抱歉，我没有理解您的意思。")
        
    except Exception as e:
        logger.error(f"AI处理失败: {e}")
        ai_reply = "抱歉，系统暂时繁忙，请稍后再试。"
    
    # 保存AI回复
    await _save_message(session_id, ai_reply, "ai")
    
    # 如果有WebSocket连接，也发送消息
    if session_id in manager.active_connections:
        await manager.send_message(session_id, {
            "type": "message",
            "content": ai_reply,
            "sender": "ai",
            "timestamp": datetime.now().isoformat()
        })
    
    return {
        "reply": ai_reply,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/stats")
async def get_webchat_stats():
    """获取网站客服统计"""
    try:
        async with async_session_maker() as db:
            # 今日统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(DISTINCT session_id) as sessions,
                        COUNT(*) as messages
                    FROM webchat_messages
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
            )
            today_stats = result.fetchone()
            
            # 活跃会话
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM webchat_sessions
                    WHERE status = 'active'
                """)
            )
            active_sessions = result.scalar()
            
            return {
                "active_connections": manager.get_connection_count(),
                "active_sessions_db": active_sessions or 0,
                "today": {
                    "sessions": today_stats[0] if today_stats else 0,
                    "messages": today_stats[1] if today_stats else 0
                }
            }
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
