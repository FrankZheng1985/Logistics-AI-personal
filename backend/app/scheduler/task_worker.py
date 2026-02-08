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
            notion_page_id = task.get("notion_page_id")
            
            try:
                # 2. 标记为 processing + 更新 Notion 看板
                await _update_task_status(task_id, "processing")
                notion_page_id = await _update_notion_board(task_id, {
                    "status": "进行中",
                    "started_at": datetime.now().isoformat(),
                    "notion_page_id": notion_page_id,
                })
                
                # 3. 执行任务
                started = datetime.now()
                logger.info(f"[TaskWorker] 开始执行任务 {task_id[:8]}... | 员工: {agent_type}")
                result = await asyncio.wait_for(
                    _execute_task(agent_type, input_data),
                    timeout=TASK_TIMEOUT
                )
                
                # 4. 标记为 completed + 更新 Notion 看板
                completed = datetime.now()
                duration = _calc_duration(started, completed)
                
                await _update_task_status(
                    task_id, "completed",
                    output_data=result
                )
                
                # 提取结果摘要
                output_summary = _extract_output_summary(result)
                await _update_notion_board(task_id, {
                    "status": "已完成",
                    "completed_at": completed.isoformat(),
                    "duration": duration,
                    "output": output_summary,
                    "notion_page_id": notion_page_id,
                })
                
                # 5. 推送结果给老板
                from_user = input_data.get("from_user", "")
                if from_user:
                    await _notify_user(from_user, agent_type, input_data, result)
                
                logger.info(f"[TaskWorker] 任务 {task_id[:8]} 执行成功 ✅ ({duration})")
                
            except asyncio.TimeoutError:
                logger.error(f"[TaskWorker] 任务 {task_id[:8]} 超时 ({TASK_TIMEOUT}s)")
                if retry_count < MAX_RETRIES:
                    await _update_task_status(task_id, "pending", retry_count=retry_count + 1)
                    logger.info(f"[TaskWorker] 任务 {task_id[:8]} 将重试 (第{retry_count + 1}次)")
                else:
                    await _update_task_status(task_id, "failed", error="执行超时")
                    await _update_notion_board(task_id, {
                        "status": "失败",
                        "completed_at": datetime.now().isoformat(),
                        "output": f"执行超时（{TASK_TIMEOUT}秒）",
                        "notion_page_id": notion_page_id,
                    })
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
                    await _update_notion_board(task_id, {
                        "status": "失败",
                        "completed_at": datetime.now().isoformat(),
                        "output": f"错误：{str(e)[:200]}",
                        "notion_page_id": notion_page_id,
                    })
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
                           input_data, retry_count, created_at, notion_page_id
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
                "notion_page_id": row[8] if len(row) > 8 else None,
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


# ==================== Notion 看板辅助函数 ====================

async def _update_notion_board(task_id: str, data: Dict[str, Any]) -> Optional[str]:
    """更新 Notion 任务看板（容错，失败不影响主流程）"""
    try:
        from app.skills.notion import get_notion_skill
        skill = await get_notion_skill()
        notion_page_id = await skill.upsert_task_row(task_id, data)
        
        # 如果是新创建的行，把 notion_page_id 存回数据库
        if notion_page_id and not data.get("notion_page_id"):
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("UPDATE ai_tasks SET notion_page_id = :npid WHERE id = :tid"),
                    {"npid": notion_page_id, "tid": task_id}
                )
                await db.commit()
        
        return notion_page_id
    except Exception as e:
        logger.warning(f"[TaskWorker] Notion看板更新失败（不影响任务执行）: {e}")
        return data.get("notion_page_id")


def _calc_duration(started: datetime, completed: datetime) -> str:
    """计算任务耗时，返回可读字符串"""
    delta = completed - started
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}秒"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}分{seconds}秒"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}小时{minutes}分"


def _extract_output_summary(result: Dict) -> str:
    """从任务结果中提取摘要"""
    if not isinstance(result, dict):
        return str(result)[:200]
    
    response = (
        result.get("response")
        or result.get("readable_report")
        or result.get("result")
        or ""
    )
    
    if isinstance(response, dict):
        response = json.dumps(response, ensure_ascii=False)
    
    if isinstance(response, str) and len(response) > 200:
        return response[:200] + "..."
    
    return str(response) if response else "任务完成，无文本输出"
