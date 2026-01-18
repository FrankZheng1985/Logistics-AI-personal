"""
WebSocket API端点 - AI员工实时工作直播
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger
from typing import Optional
from datetime import datetime

from app.services.websocket_manager import websocket_manager
from app.models import get_db
from app.models.database import AsyncSessionLocal

router = APIRouter()


@router.websocket("/ws/agent-live/{agent_type}")
async def agent_live_websocket(websocket: WebSocket, agent_type: str = "all"):
    """AI员工实时工作直播WebSocket端点
    
    Args:
        websocket: WebSocket连接
        agent_type: 要订阅的员工类型，"all"表示订阅所有员工
    """
    await websocket_manager.connect(websocket, agent_type)
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "agent_type": agent_type,
            "message": f"已连接到{'所有员工' if agent_type == 'all' else agent_type}的工作直播",
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持连接
        while True:
            try:
                # 接收客户端消息（心跳或命令）
                data = await websocket.receive_text()
                
                # 处理ping消息
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket接收消息错误: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        await websocket_manager.disconnect(websocket, agent_type)


@router.get("/live/{agent_type}/steps")
async def get_agent_live_steps(
    agent_type: str,
    limit: int = Query(50, ge=1, le=200),
    session_id: Optional[str] = None
):
    """获取AI员工最近的工作步骤
    
    Args:
        agent_type: 员工类型
        limit: 返回数量限制
        session_id: 可选的任务会话ID，用于获取特定任务的步骤
    """
    try:
        async with AsyncSessionLocal() as db:
            if session_id:
                # 获取特定会话的步骤
                result = await db.execute(
                    text("""
                        SELECT id, agent_type, agent_name, session_id, step_type,
                               step_title, step_content, step_data, status, created_at
                        FROM agent_live_steps
                        WHERE session_id = :session_id
                        ORDER BY created_at ASC
                        LIMIT :limit
                    """),
                    {"session_id": session_id, "limit": limit}
                )
            elif agent_type == "all":
                # 获取所有员工的最近步骤
                result = await db.execute(
                    text("""
                        SELECT id, agent_type, agent_name, session_id, step_type,
                               step_title, step_content, step_data, status, created_at
                        FROM agent_live_steps
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            else:
                # 获取特定员工的最近步骤
                result = await db.execute(
                    text("""
                        SELECT id, agent_type, agent_name, session_id, step_type,
                               step_title, step_content, step_data, status, created_at
                        FROM agent_live_steps
                        WHERE agent_type = :agent_type
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"agent_type": agent_type, "limit": limit}
                )
            
            rows = result.fetchall()
            
            steps = [
                {
                    "id": str(row[0]),
                    "agent_type": row[1],
                    "agent_name": row[2],
                    "session_id": str(row[3]) if row[3] else None,
                    "step_type": row[4],
                    "step_title": row[5],
                    "step_content": row[6],
                    "step_data": row[7],
                    "status": row[8],
                    "created_at": row[9].isoformat() if row[9] else None
                }
                for row in rows
            ]
            
            # 如果不是按会话查询，需要反转顺序（因为是DESC查询的）
            if not session_id:
                steps.reverse()
            
            return {
                "steps": steps,
                "count": len(steps),
                "agent_type": agent_type
            }
            
    except Exception as e:
        logger.error(f"获取工作步骤失败: {e}")
        return {"steps": [], "count": 0, "error": str(e)}


@router.get("/live/{agent_type}/sessions")
async def get_agent_task_sessions(
    agent_type: str,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """获取AI员工的任务会话列表
    
    Args:
        agent_type: 员工类型
        limit: 返回数量限制
        status: 可选的状态过滤
    """
    try:
        async with AsyncSessionLocal() as db:
            if agent_type == "all":
                if status:
                    result = await db.execute(
                        text("""
                            SELECT id, agent_type, agent_name, task_type, task_description,
                                   status, started_at, completed_at, duration_ms, result_summary
                            FROM agent_task_sessions
                            WHERE status = :status
                            ORDER BY created_at DESC
                            LIMIT :limit
                        """),
                        {"status": status, "limit": limit}
                    )
                else:
                    result = await db.execute(
                        text("""
                            SELECT id, agent_type, agent_name, task_type, task_description,
                                   status, started_at, completed_at, duration_ms, result_summary
                            FROM agent_task_sessions
                            ORDER BY created_at DESC
                            LIMIT :limit
                        """),
                        {"limit": limit}
                    )
            else:
                if status:
                    result = await db.execute(
                        text("""
                            SELECT id, agent_type, agent_name, task_type, task_description,
                                   status, started_at, completed_at, duration_ms, result_summary
                            FROM agent_task_sessions
                            WHERE agent_type = :agent_type AND status = :status
                            ORDER BY created_at DESC
                            LIMIT :limit
                        """),
                        {"agent_type": agent_type, "status": status, "limit": limit}
                    )
                else:
                    result = await db.execute(
                        text("""
                            SELECT id, agent_type, agent_name, task_type, task_description,
                                   status, started_at, completed_at, duration_ms, result_summary
                            FROM agent_task_sessions
                            WHERE agent_type = :agent_type
                            ORDER BY created_at DESC
                            LIMIT :limit
                        """),
                        {"agent_type": agent_type, "limit": limit}
                    )
            
            rows = result.fetchall()
            
            sessions = [
                {
                    "id": str(row[0]),
                    "agent_type": row[1],
                    "agent_name": row[2],
                    "task_type": row[3],
                    "task_description": row[4],
                    "status": row[5],
                    "started_at": row[6].isoformat() if row[6] else None,
                    "completed_at": row[7].isoformat() if row[7] else None,
                    "duration_ms": row[8],
                    "result_summary": row[9]
                }
                for row in rows
            ]
            
            return {
                "sessions": sessions,
                "count": len(sessions),
                "agent_type": agent_type
            }
            
    except Exception as e:
        logger.error(f"获取任务会话失败: {e}")
        return {"sessions": [], "count": 0, "error": str(e)}


@router.get("/websocket/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return {
        "total_connections": websocket_manager.get_connection_count(),
        "subscriptions": {
            agent_type: len(connections)
            for agent_type, connections in websocket_manager.active_connections.items()
        }
    }
