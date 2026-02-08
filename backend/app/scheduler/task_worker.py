"""
TaskWorker - AI员工任务调度引擎

职责：
1. 定时扫描 ai_tasks 表中的 pending 任务
2. 按优先级顺序拉取任务，交给对应的 AI 员工执行
3. 更新任务状态（pending → processing → completed/failed）
4. 将执行结果通过企业微信发送给老板
5. 支持超时控制和错误重试

设计原则：
- 每次最多处理 3 个任务（避免长时间占用）
- 单任务超时 120 秒
- 失败任务最多重试 2 次
- 执行结果自动推送给发起人
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


# 每轮最多处理的任务数
MAX_TASKS_PER_ROUND = 3

# 单任务超时（秒）
TASK_TIMEOUT = 120

# 最大重试次数
MAX_RETRIES = 2


async def process_pending_tasks():
    """
    任务调度引擎主循环 - 由 APScheduler 每 30 秒调用一次
    
    流程：
    1. 从 ai_tasks 表拉取 pending 任务（按优先级 + 创建时间排序）
    2. 逐个执行（调用对应 Agent 的 process 方法）
    3. 更新状态并推送结果
    """
    try:
        # 1. 拉取待处理任务
        tasks = await _fetch_pending_tasks(limit=MAX_TASKS_PER_ROUND)
        
        if not tasks:
            return  # 没有待处理任务，静默退出
        
        logger.info(f"[TaskWorker] 发现 {len(tasks)} 个待处理任务，开始执行...")
        
        for task in tasks:
            task_id = str(task["id"])
            agent_type = task["agent_type"]
            input_data = task["input_data"]
            retry_count = task.get("retry_count", 0)
            
            try:
                # 2. 标记为 processing
                await _update_task_status(task_id, "processing")
                
                # 3. 执行任务
                logger.info(f"[TaskWorker] 开始执行任务 {task_id[:8]}... | 员工: {agent_type}")
                result = await asyncio.wait_for(
                    _execute_task(agent_type, input_data),
                    timeout=TASK_TIMEOUT
                )
                
                # 4. 标记为 completed，保存结果
                await _update_task_status(
                    task_id, "completed",
                    output_data=result
                )
                
                # 5. 推送结果给老板
                from_user = input_data.get("from_user", "")
                if from_user:
                    await _notify_user(from_user, agent_type, input_data, result)
                
                logger.info(f"[TaskWorker] 任务 {task_id[:8]} 执行成功 ✅")
                
            except asyncio.TimeoutError:
                logger.error(f"[TaskWorker] 任务 {task_id[:8]} 超时 ({TASK_TIMEOUT}s)")
                if retry_count < MAX_RETRIES:
                    await _update_task_status(task_id, "pending", retry_count=retry_count + 1)
                    logger.info(f"[TaskWorker] 任务 {task_id[:8]} 将重试 (第{retry_count + 1}次)")
                else:
                    await _update_task_status(task_id, "failed", error="执行超时")
                    from_user = input_data.get("from_user", "")
                    if from_user:
                        await _notify_failure(from_user, agent_type, input_data, "任务执行超时")
                
            except Exception as e:
                logger.error(f"[TaskWorker] 任务 {task_id[:8]} 执行失败: {e}")
                if retry_count < MAX_RETRIES:
                    await _update_task_status(task_id, "pending", retry_count=retry_count + 1)
                    logger.info(f"[TaskWorker] 任务 {task_id[:8]} 将重试 (第{retry_count + 1}次)")
                else:
                    await _update_task_status(task_id, "failed", error=str(e)[:500])
                    from_user = input_data.get("from_user", "")
                    if from_user:
                        await _notify_failure(from_user, agent_type, input_data, str(e)[:200])
                    
    except Exception as e:
        logger.error(f"[TaskWorker] 调度引擎异常: {e}")


async def _fetch_pending_tasks(limit: int = 3):
    """从数据库拉取待处理任务（按优先级 + 时间排序）"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, task_type, agent_type, status, priority,
                           input_data, retry_count, created_at
                    FROM ai_tasks
                    WHERE status = 'pending'
                    ORDER BY priority ASC, created_at ASC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            rows = result.fetchall()
        
        tasks = []
        for row in rows:
            input_data = row[5]
            if isinstance(input_data, str):
                input_data = json.loads(input_data)
            
            tasks.append({
                "id": row[0],
                "task_type": row[1],
                "agent_type": row[2],
                "status": row[3],
                "priority": row[4],
                "input_data": input_data or {},
                "retry_count": row[6] or 0,
                "created_at": row[7],
            })
        
        return tasks
        
    except Exception as e:
        logger.error(f"[TaskWorker] 拉取任务失败: {e}")
        return []


async def _update_task_status(task_id: str, status: str,
                               output_data: Dict = None,
                               error: str = None,
                               retry_count: int = None):
    """更新任务状态"""
    try:
        async with AsyncSessionLocal() as db:
            sets = ["status = :status", "updated_at = NOW()"]
            params = {"task_id": task_id, "status": status}
            
            if status == "processing":
                sets.append("started_at = NOW()")
            
            if status in ("completed", "failed"):
                sets.append("completed_at = NOW()")
            
            if output_data is not None:
                sets.append("output_data = :output_data")
                params["output_data"] = json.dumps(output_data, ensure_ascii=False, default=str)
            
            if error is not None:
                sets.append("error_message = :error")
                params["error"] = error
            
            if retry_count is not None:
                sets.append("retry_count = :retry_count")
                params["retry_count"] = retry_count
            
            await db.execute(
                text(f"UPDATE ai_tasks SET {', '.join(sets)} WHERE id = :task_id"),
                params
            )
            await db.commit()
            
    except Exception as e:
        logger.error(f"[TaskWorker] 更新任务状态失败: {e}")


async def _execute_task(agent_type: str, input_data: Dict) -> Dict[str, Any]:
    """
    执行任务 - 调用对应 AI 员工的 process 方法
    
    不同员工有不同的输入格式，这里做统一适配
    """
    from app.agents.base import AgentRegistry
    from app.models.conversation import AgentType
    
    # agent_type 字符串 -> AgentType 枚举
    try:
        agent_type_enum = AgentType(agent_type)
    except ValueError:
        return {"success": False, "error": f"未知的员工类型: {agent_type}"}
    
    # 获取 Agent 实例
    agent = AgentRegistry.get(agent_type_enum)
    if not agent:
        return {"success": False, "error": f"{agent_type} 未上线，无法执行任务"}
    
    # 构建输入
    description = input_data.get("description", "")
    
    # 根据不同 agent_type 构建合适的输入
    process_input = _build_agent_input(agent_type, description, input_data)
    
    # 调用 Agent 的 process 方法
    result = await agent.process(process_input)
    
    return result


def _build_agent_input(agent_type: str, description: str, input_data: Dict) -> Dict[str, Any]:
    """根据不同 AI 员工类型构建合适的输入格式"""
    
    # 通用格式（大多数 Agent 都接受这种格式）
    base_input = {
        "message": description,
        "task_description": description,
        "source": "task_worker",
        "from_user": input_data.get("from_user", ""),
    }
    
    # 特殊 Agent 的输入适配
    if agent_type == "lead_hunter":
        # 小猎：线索搜索
        base_input["action"] = "search"
        base_input["query"] = description
        
    elif agent_type == "copywriter":
        # 小文：文案创作
        base_input["action"] = "create"
        base_input["topic"] = description
        
    elif agent_type == "analyst":
        # 小析：数据分析
        base_input["action"] = "analyze"
        base_input["query"] = description
        
    elif agent_type == "video_creator":
        # 小影：视频创作
        base_input["action"] = "create"
        base_input["topic"] = description
        
    elif agent_type == "sales":
        # 小销：营销策略
        base_input["action"] = "plan"
        base_input["topic"] = description
        
    elif agent_type == "coordinator":
        # 小调：调度报告
        base_input["action"] = "report"
        
    elif agent_type == "eu_customs_monitor":
        # 小欧：海关监控
        base_input["action"] = "monitor"
        base_input["query"] = description
    
    return base_input


async def _notify_user(user_id: str, agent_type: str, input_data: Dict, result: Dict):
    """将执行结果推送给老板"""
    try:
        from app.api.wechat_assistant import send_text_message
        
        # 获取员工名
        agent_names = {
            "coordinator": "小调", "video_creator": "小影",
            "copywriter": "小文", "sales": "小销",
            "follow": "小跟", "analyst": "小析",
            "lead_hunter": "小猎", "analyst2": "小析2",
            "eu_customs_monitor": "小欧间谍",
        }
        agent_name = agent_names.get(agent_type, agent_type)
        task_desc = input_data.get("description", "")[:50]
        
        # 提取结果摘要
        if isinstance(result, dict):
            response = result.get("response") or result.get("readable_report") or result.get("result", "")
            if isinstance(response, dict):
                response = json.dumps(response, ensure_ascii=False)[:500]
            elif isinstance(response, str) and len(response) > 500:
                response = response[:500] + "..."
        else:
            response = str(result)[:500]
        
        # 构建推送消息
        msg = f"【{agent_name}完成任务】\n"
        msg += f"任务：{task_desc}\n"
        msg += f"结果：{response if response else '任务已完成，无文本输出'}"
        
        await send_text_message(user_id, msg)
        logger.info(f"[TaskWorker] 结果已推送给 {user_id}")
        
    except Exception as e:
        logger.error(f"[TaskWorker] 推送结果失败: {e}")


async def _notify_failure(user_id: str, agent_type: str, input_data: Dict, error: str):
    """将失败信息推送给老板"""
    try:
        from app.api.wechat_assistant import send_text_message
        
        agent_names = {
            "coordinator": "小调", "video_creator": "小影",
            "copywriter": "小文", "sales": "小销",
            "follow": "小跟", "analyst": "小析",
            "lead_hunter": "小猎", "analyst2": "小析2",
            "eu_customs_monitor": "小欧间谍",
        }
        agent_name = agent_names.get(agent_type, agent_type)
        task_desc = input_data.get("description", "")[:50]
        
        msg = f"【{agent_name}任务失败】\n"
        msg += f"任务：{task_desc}\n"
        msg += f"原因：{error}\n"
        msg += f"已重试{MAX_RETRIES}次仍然失败，需要你看一下。"
        
        await send_text_message(user_id, msg)
        
    except Exception as e:
        logger.error(f"[TaskWorker] 推送失败通知失败: {e}")
