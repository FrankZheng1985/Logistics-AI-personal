"""
任务队列服务
基于Redis和数据库的混合任务队列系统
支持任务优先级、重试、延迟执行
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy import text

from app.core.config import settings
from app.models.database import async_session_maker

# 尝试导入Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，任务队列将使用数据库模式")


class TaskQueue:
    """任务队列服务"""
    
    def __init__(self):
        self.redis_client = None
        self.use_redis = False
        self.task_handlers: Dict[str, Callable] = {}
        self.is_running = False
    
    async def init(self):
        """初始化任务队列"""
        if REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                await self.redis_client.ping()
                self.use_redis = True
                logger.info("✅ Redis任务队列已连接")
            except Exception as e:
                logger.warning(f"Redis连接失败，使用数据库模式: {e}")
                self.use_redis = False
        else:
            logger.info("📦 任务队列使用数据库模式")
    
    async def close(self):
        """关闭连接"""
        self.is_running = False
        if self.redis_client:
            await self.redis_client.close()
    
    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        logger.info(f"📦 注册任务处理器: {task_type}")
    
    async def enqueue(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 5,
        delay_seconds: int = 0,
        assigned_to: Optional[str] = None
    ) -> str:
        """
        添加任务到队列
        
        Args:
            task_type: 任务类型
            task_data: 任务数据
            priority: 优先级 (1-10, 10最高)
            delay_seconds: 延迟执行秒数
            assigned_to: 分配给哪个AI员工
        
        Returns:
            任务ID
        """
        task_id = str(uuid4())
        scheduled_at = datetime.now() + timedelta(seconds=delay_seconds) if delay_seconds > 0 else None
        
        task = {
            "id": task_id,
            "task_type": task_type,
            "task_data": task_data,
            "priority": priority,
            "assigned_to": assigned_to,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            "created_at": datetime.now().isoformat()
        }
        
        if self.use_redis and delay_seconds == 0:
            # 立即执行的任务使用Redis队列
            queue_name = f"task_queue:{priority}"
            await self.redis_client.lpush(queue_name, json.dumps(task))
            logger.info(f"📦 任务入队(Redis): {task_type}, 优先级: {priority}")
        else:
            # 延迟任务或无Redis时使用数据库
            await self._save_to_db(task, scheduled_at)
            logger.info(f"📦 任务入队(DB): {task_type}, 计划时间: {scheduled_at}")
        
        return task_id
    
    async def _save_to_db(self, task: Dict[str, Any], scheduled_at: Optional[datetime] = None):
        """保存任务到数据库"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO task_queue 
                        (id, task_type, task_data, priority, status, assigned_to, 
                         scheduled_at, created_at)
                        VALUES (:id, :task_type, :task_data, :priority, 'pending', 
                                :assigned_to, :scheduled_at, NOW())
                    """),
                    {
                        "id": task["id"],
                        "task_type": task["task_type"],
                        "task_data": json.dumps(task["task_data"]),
                        "priority": task["priority"],
                        "assigned_to": task.get("assigned_to"),
                        "scheduled_at": scheduled_at
                    }
                )
                await db.commit()
        except Exception as e:
            logger.error(f"保存任务到数据库失败: {e}")
    
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        从队列获取任务（优先级高的先出）
        """
        if self.use_redis:
            # 按优先级从高到低检查队列
            for priority in range(10, 0, -1):
                queue_name = f"task_queue:{priority}"
                task_json = await self.redis_client.rpop(queue_name)
                if task_json:
                    return json.loads(task_json)
        
        # 从数据库获取
        return await self._get_from_db()
    
    async def _get_from_db(self) -> Optional[Dict[str, Any]]:
        """从数据库获取待执行的任务"""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        UPDATE task_queue
                        SET status = 'processing', started_at = NOW()
                        WHERE id = (
                            SELECT id FROM task_queue
                            WHERE status = 'pending'
                            AND (scheduled_at IS NULL OR scheduled_at <= NOW())
                            ORDER BY priority DESC, created_at ASC
                            LIMIT 1
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING id, task_type, task_data, priority, assigned_to, retry_count
                    """)
                )
                row = result.fetchone()
                await db.commit()
                
                if row:
                    return {
                        "id": str(row[0]),
                        "task_type": row[1],
                        "task_data": row[2] if isinstance(row[2], dict) else json.loads(row[2]),
                        "priority": row[3],
                        "assigned_to": row[4],
                        "retry_count": row[5]
                    }
                return None
        except Exception as e:
            logger.error(f"从数据库获取任务失败: {e}")
            return None
    
    async def complete_task(self, task_id: str, result: Optional[Dict] = None):
        """标记任务完成"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE task_queue
                        SET status = 'completed', 
                            completed_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"task_id": task_id}
                )
                await db.commit()
        except Exception as e:
            logger.error(f"标记任务完成失败: {e}")
    
    async def fail_task(self, task_id: str, error_message: str, retry: bool = True):
        """标记任务失败"""
        try:
            async with async_session_maker() as db:
                if retry:
                    # 检查是否可以重试
                    result = await db.execute(
                        text("""
                            SELECT retry_count, max_retries FROM task_queue
                            WHERE id = :task_id
                        """),
                        {"task_id": task_id}
                    )
                    row = result.fetchone()
                    
                    if row and row[0] < row[1]:
                        # 可以重试，重新入队
                        await db.execute(
                            text("""
                                UPDATE task_queue
                                SET status = 'pending',
                                    retry_count = retry_count + 1,
                                    error_message = :error,
                                    scheduled_at = NOW() + INTERVAL '5 minutes'
                                WHERE id = :task_id
                            """),
                            {"task_id": task_id, "error": error_message}
                        )
                        logger.info(f"📦 任务将在5分钟后重试: {task_id}")
                    else:
                        # 超过重试次数
                        await db.execute(
                            text("""
                                UPDATE task_queue
                                SET status = 'failed',
                                    error_message = :error,
                                    completed_at = NOW()
                                WHERE id = :task_id
                            """),
                            {"task_id": task_id, "error": error_message}
                        )
                else:
                    # 直接标记失败
                    await db.execute(
                        text("""
                            UPDATE task_queue
                            SET status = 'failed',
                                error_message = :error,
                                completed_at = NOW()
                            WHERE id = :task_id
                        """),
                        {"task_id": task_id, "error": error_message}
                    )
                
                await db.commit()
        except Exception as e:
            logger.error(f"标记任务失败失败: {e}")
    
    async def process_task(self, task: Dict[str, Any]) -> bool:
        """处理单个任务"""
        task_id = task["id"]
        task_type = task["task_type"]
        task_data = task["task_data"]
        
        handler = self.task_handlers.get(task_type)
        if not handler:
            logger.warning(f"未找到任务处理器: {task_type}")
            await self.fail_task(task_id, f"未找到处理器: {task_type}", retry=False)
            return False
        
        try:
            logger.info(f"📦 开始处理任务: {task_type} ({task_id})")
            result = await handler(task_data)
            await self.complete_task(task_id, result)
            logger.info(f"📦 任务完成: {task_type} ({task_id})")
            return True
        except Exception as e:
            logger.error(f"📦 任务执行失败: {task_type} ({task_id}): {e}")
            await self.fail_task(task_id, str(e))
            return False
    
    async def start_worker(self, worker_count: int = 1):
        """启动任务工作线程"""
        self.is_running = True
        logger.info(f"📦 启动 {worker_count} 个任务工作线程")
        
        async def worker():
            while self.is_running:
                try:
                    task = await self.dequeue()
                    if task:
                        await self.process_task(task)
                    else:
                        # 没有任务，等待一下
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"任务工作线程异常: {e}")
                    await asyncio.sleep(5)
        
        # 启动多个工作协程
        workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
        await asyncio.gather(*workers)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT 
                            status,
                            COUNT(*) as count
                        FROM task_queue
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                        GROUP BY status
                    """)
                )
                status_counts = {row[0]: row[1] for row in result.fetchall()}
                
                result = await db.execute(
                    text("""
                        SELECT 
                            task_type,
                            COUNT(*) as count
                        FROM task_queue
                        WHERE status = 'pending'
                        GROUP BY task_type
                    """)
                )
                pending_by_type = {row[0]: row[1] for row in result.fetchall()}
                
                return {
                    "status_counts": status_counts,
                    "pending_by_type": pending_by_type,
                    "redis_enabled": self.use_redis
                }
        except Exception as e:
            logger.error(f"获取队列统计失败: {e}")
            return {}
    
    async def get_pending_tasks(
        self,
        task_type: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取待处理任务列表"""
        try:
            async with async_session_maker() as db:
                query = """
                    SELECT id, task_type, task_data, priority, status, 
                           assigned_to, scheduled_at, created_at
                    FROM task_queue
                    WHERE status = 'pending'
                """
                params = {"limit": limit}
                
                if task_type:
                    query += " AND task_type = :task_type"
                    params["task_type"] = task_type
                
                if assigned_to:
                    query += " AND assigned_to = :assigned_to"
                    params["assigned_to"] = assigned_to
                
                query += " ORDER BY priority DESC, created_at ASC LIMIT :limit"
                
                result = await db.execute(text(query), params)
                
                return [
                    {
                        "id": str(row[0]),
                        "task_type": row[1],
                        "task_data": row[2],
                        "priority": row[3],
                        "status": row[4],
                        "assigned_to": row[5],
                        "scheduled_at": row[6].isoformat() if row[6] else None,
                        "created_at": row[7].isoformat() if row[7] else None
                    }
                    for row in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"获取待处理任务失败: {e}")
            return []


# 创建单例
task_queue = TaskQueue()


# ==================== 注册默认任务处理器 ====================

async def handle_follow_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理跟进任务"""
    from app.agents.follow_agent import follow_agent
    
    customer_id = data.get("customer_id")
    purpose = data.get("purpose", "日常跟进")
    
    result = await follow_agent.process({
        "customer_id": customer_id,
        "purpose": purpose
    })
    
    return result


async def handle_analyze_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理分析任务"""
    from app.agents.analyst import analyst_agent
    
    result = await analyst_agent.process(data)
    return result


async def handle_hunt_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理线索搜索任务"""
    from app.agents.lead_hunter import lead_hunter_agent
    
    result = await lead_hunter_agent.process({
        "action": "hunt",
        **data
    })
    return result


async def handle_video_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理视频生成任务"""
    from app.agents.video_creator import video_creator_agent
    
    result = await video_creator_agent.process(data)
    return result


async def handle_copywriting_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理文案任务"""
    from app.agents.copywriter import copywriter_agent
    
    result = await copywriter_agent.process(data)
    return result


async def init_task_handlers():
    """初始化任务处理器"""
    task_queue.register_handler("follow", handle_follow_task)
    task_queue.register_handler("analyze", handle_analyze_task)
    task_queue.register_handler("hunt", handle_hunt_task)
    task_queue.register_handler("video", handle_video_task)
    task_queue.register_handler("copywriting", handle_copywriting_task)
