"""
定时任务模块
使用APScheduler实现定时任务调度
支持7个AI员工的24小时自动化工作

注意：使用文件锁确保多worker模式下只有一个worker运行调度器，
避免定时任务被重复执行（如Serper API被调用多次）。
"""
import os
import fcntl
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import settings


# 全局调度器实例
scheduler: AsyncIOScheduler = None

# 调度器锁文件句柄（保持打开以维持锁）
_scheduler_lock_file = None
_is_scheduler_worker = False

SCHEDULER_LOCK_PATH = "/tmp/logistics_scheduler.lock"


def _try_acquire_scheduler_lock() -> bool:
    """
    尝试获取调度器独占锁。
    使用文件锁确保多个Gunicorn worker中只有一个启动调度器。
    锁在进程退出时自动释放。
    """
    global _scheduler_lock_file, _is_scheduler_worker
    try:
        _scheduler_lock_file = open(SCHEDULER_LOCK_PATH, 'w')
        fcntl.flock(_scheduler_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _scheduler_lock_file.write(str(os.getpid()))
        _scheduler_lock_file.flush()
        _is_scheduler_worker = True
        logger.info(f"🔒 调度器锁获取成功 (PID: {os.getpid()})，当前worker负责运行定时任务")
        return True
    except (IOError, OSError):
        # 锁已被其他worker持有
        if _scheduler_lock_file:
            _scheduler_lock_file.close()
            _scheduler_lock_file = None
        _is_scheduler_worker = False
        return False


def get_scheduler() -> AsyncIOScheduler:
    """获取调度器实例"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    return scheduler


async def init_scheduler():
    """初始化并启动定时任务"""
    if not settings.SCHEDULER_ENABLED:
        logger.info("📅 定时任务已禁用")
        return
    
    # 多worker模式下，只允许一个worker运行调度器
    if not _try_acquire_scheduler_lock():
        logger.info(f"📅 调度器已由其他worker启动，当前worker (PID: {os.getpid()}) 跳过定时任务初始化")
        return
    
    global scheduler
    scheduler = get_scheduler()
    
    # ==================== 导入任务（容错处理） ====================
    
    # 跟进任务
    try:
        from app.scheduler.follow_tasks import (
            daily_follow_check,
            check_no_reply_customers,
            daily_summary_task,
            reset_daily_stats
        )
    except ImportError as e:
        logger.warning(f"跟进任务导入失败: {e}")
        daily_follow_check = check_no_reply_customers = daily_summary_task = reset_daily_stats = None
    
    # 市场情报任务
    try:
        from app.scheduler.market_tasks import (
            collect_market_intelligence,
            send_boss_daily_report,
            send_boss_weekly_report,
            check_urgent_intel,
        )
    except ImportError as e:
        logger.warning(f"市场情报任务导入失败: {e}")
        collect_market_intelligence = send_boss_daily_report = send_boss_weekly_report = check_urgent_intel = None
    
    # 欧洲海关新闻采集（可选）
    try:
        from app.scheduler.market_tasks import collect_eu_customs_news
    except ImportError:
        logger.info("collect_eu_customs_news 未找到，跳过欧洲海关新闻采集任务")
        collect_eu_customs_news = None
    
    # 内容发布任务
    try:
        from app.scheduler.content_tasks import (
            lead_hunt_task,
            auto_video_generation,
            auto_content_publish,
            auto_xiaohongshu_publish,
            knowledge_base_update,
            daily_content_generation,
            batch_content_generation,
            content_publish_reminder
        )
    except ImportError as e:
        logger.warning(f"内容发布任务导入失败: {e}")
        lead_hunt_task = auto_video_generation = auto_content_publish = None
        auto_xiaohongshu_publish = knowledge_base_update = daily_content_generation = None
        batch_content_generation = content_publish_reminder = None
    
    # 素材采集任务
    try:
        from app.scheduler.asset_tasks import asset_collection_task
    except ImportError as e:
        logger.warning(f"素材采集任务导入失败: {e}")
        asset_collection_task = None
    
    # Maria 巡检任务
    try:
        from app.services.inspection_service import run_maria_inspection
    except ImportError as e:
        logger.warning(f"Maria巡检任务导入失败: {e}")
        run_maria_inspection = None
    
    # Maria 后台智能任务
    try:
        from app.scheduler.maria_tasks import (
            auto_sync_emails,
            auto_sync_calendar,
            maria_morning_brief
        )
    except ImportError as e:
        logger.warning(f"Maria后台任务导入失败: {e}")
        auto_sync_emails = auto_sync_calendar = maria_morning_brief = None
    
    # TaskWorker 任务调度引擎
    try:
        from app.scheduler.task_worker import process_pending_tasks, check_stale_tasks
    except ImportError as e:
        logger.warning(f"TaskWorker导入失败: {e}")
        process_pending_tasks = check_stale_tasks = None
    
    # Notion 知识库同步任务
    async def sync_notion_knowledge_task():
        """定时同步 Notion 知识库到向量数据库"""
        try:
            from app.services.vector_store import vector_store
            await vector_store.sync_notion_knowledge()
        except Exception as e:
            logger.warning(f"Notion知识库同步失败: {e}")
    
    # ==================== 辅助函数 ====================
    
    def _safe_add_job(func, trigger, job_id, name, **kwargs):
        """安全注册任务，跳过未成功导入的任务"""
        if func is None:
            logger.warning(f"⚠️ 跳过任务注册: {name} (函数未导入)")
            return
        scheduler.add_job(func, trigger, id=job_id, name=name, replace_existing=True, **kwargs)
        logger.info(f"📅 注册任务: {name}")
    
    # ==================== 小跟任务 ====================
    
    _safe_add_job(daily_follow_check, CronTrigger(hour=9, minute=0),
                  "daily_follow_check_morning", "[小跟] 每日跟进检查(上午)")
    
    _safe_add_job(daily_follow_check, CronTrigger(hour=14, minute=0),
                  "daily_follow_check_afternoon", "[小跟] 每日跟进检查(下午)")
    
    _safe_add_job(check_no_reply_customers, IntervalTrigger(hours=4),
                  "check_no_reply", "[小跟] 未回复客户检查")
    
    # ==================== 小调任务 ====================
    
    # 导入小调企业微信汇报任务
    try:
        from app.scheduler.coordinator_tasks import (
            coordinator_wechat_daily_report,
            coordinator_wechat_morning_greeting
        )
    except ImportError as e:
        logger.warning(f"小调任务导入失败: {e}")
        coordinator_wechat_daily_report = coordinator_wechat_morning_greeting = None
    
    _safe_add_job(daily_summary_task, CronTrigger(hour=settings.DAILY_SUMMARY_HOUR, minute=0),
                  "daily_summary", f"[小调] 每日工作汇总 - {settings.DAILY_SUMMARY_HOUR}:00")
    
    _safe_add_job(coordinator_wechat_daily_report, CronTrigger(hour=18, minute=30),
                  "coordinator_wechat_daily_report", "[小调] 企业微信日报推送 - 18:30")
    
    _safe_add_job(coordinator_wechat_morning_greeting, CronTrigger(hour=8, minute=30),
                  "coordinator_wechat_morning", "[小调] 企业微信早间问候 - 08:30")
    
    _safe_add_job(reset_daily_stats, CronTrigger(hour=0, minute=5),
                  "reset_daily_stats", "[系统] 重置每日统计 - 00:05")
    
    # ==================== 小猎任务 (24小时智能搜索) ====================
    
    # 导入加强搜索和夜间搜索任务
    try:
        from app.scheduler.content_tasks import (
            lead_hunt_intensive_task,
            lead_hunt_night_task
        )
    except ImportError as e:
        logger.warning(f"小猎加强搜索任务导入失败: {e}")
        lead_hunt_intensive_task = lead_hunt_night_task = None
    
    _safe_add_job(lead_hunt_task, CronTrigger(hour='7-23', minute=15),
                  "lead_hunt_regular", "[小猎] 常规线索搜索 - 每小时(7:15-23:15)")
    
    _safe_add_job(lead_hunt_intensive_task, CronTrigger(hour='9,10,14,15,16,19,20', minute=45),
                  "lead_hunt_intensive", "[小猎] 加强线索搜索 - 高峰时段")
    
    _safe_add_job(lead_hunt_night_task, CronTrigger(hour='0,2,4,6', minute=30),
                  "lead_hunt_night", "[小猎] 夜间轻量搜索 - 凌晨")
    
    # ==================== 小析任务 ====================
    
    _safe_add_job(collect_market_intelligence, CronTrigger(hour=6, minute=0),
                  "market_intel_collect", "[小析] 市场情报采集 - 06:00")
    
    _safe_add_job(send_boss_daily_report, CronTrigger(hour=8, minute=0),
                  "boss_daily_report", "[小析] 老板日报推送 - 08:00")
    
    _safe_add_job(send_boss_weekly_report, CronTrigger(day_of_week='mon', hour=8, minute=30),
                  "boss_weekly_report", "[小析] 老板周报推送 - 每周一 08:30")
    
    _safe_add_job(check_urgent_intel, IntervalTrigger(hours=1),
                  "urgent_intel_check", "[小析] 紧急情报检查 - 每小时")
    
    # ==================== 小欧间谍任务 ====================
    
    _safe_add_job(collect_eu_customs_news, CronTrigger(hour=6, minute=0),
                  "eu_customs_news_collect", "[小欧间谍] 欧洲海关新闻采集 - 06:00")
    
    # ==================== 小视任务 ====================
    
    _safe_add_job(auto_video_generation, CronTrigger(hour=10, minute=0),
                  "auto_video_generation", "[小视] 自动视频生成 - 10:00")
    
    # ==================== 小文任务 ====================
    
    _safe_add_job(auto_content_publish, CronTrigger(day_of_week='mon,wed,fri', hour=15, minute=0),
                  "auto_content_publish", "[小文] 企业微信文案发布 - 周一/三/五 15:00")
    
    _safe_add_job(auto_xiaohongshu_publish, CronTrigger(day_of_week='tue,thu,sat', hour=12, minute=0),
                  "auto_xiaohongshu_publish", "[小文] 小红书笔记发布 - 周二/四/六 12:00")
    
    # ==================== 小析2任务 ====================
    
    _safe_add_job(knowledge_base_update, CronTrigger(hour=23, minute=0),
                  "knowledge_base_update", "[小析2] 知识库更新 - 23:00")
    
    # ==================== 小媒任务 (内容营销) ====================
    
    _safe_add_job(daily_content_generation, CronTrigger(hour=5, minute=0),
                  "daily_content_generation", "[小媒] 每日内容生成 - 05:00")
    
    _safe_add_job(batch_content_generation, CronTrigger(day_of_week='sun', hour=4, minute=0),
                  "batch_content_generation", "[小媒] 批量内容生成 - 每周日 04:00")
    
    _safe_add_job(content_publish_reminder, CronTrigger(hour=9, minute=5),
                  "content_publish_reminder", "[小媒] 内容发布提醒 - 09:05")
    
    # ==================== 小采任务 ====================
    
    _safe_add_job(asset_collection_task, CronTrigger(hour=7, minute=0),
                  "asset_collection_morning", "[小采] 素材采集(上午) - 07:00")
    
    _safe_add_job(asset_collection_task, CronTrigger(hour=16, minute=0),
                  "asset_collection_afternoon", "[小采] 素材采集(下午) - 16:00")
    
    # ==================== Maria 巡检任务 ====================
    
    _safe_add_job(run_maria_inspection, CronTrigger(hour=9, minute=30),
                  "maria_inspection_morning", "[Maria] 早间系统巡检 - 09:30")
    
    _safe_add_job(run_maria_inspection, CronTrigger(hour=18, minute=0),
                  "maria_inspection_evening", "[Maria] 晚间系统巡检 - 18:00")
    
    # ==================== Maria 后台智能任务（速度优化）====================
    
    _safe_add_job(auto_sync_emails, IntervalTrigger(minutes=10),
                  "maria_auto_sync_emails", "[Maria] 邮件自动同步 - 每10分钟")
    
    _safe_add_job(auto_sync_calendar, IntervalTrigger(minutes=5),
                  "maria_auto_sync_calendar", "[Maria] 日历自动同步 - 每5分钟")
    
    _safe_add_job(maria_morning_brief, CronTrigger(hour=9, minute=0),
                  "maria_morning_brief", "[Maria] 早间智能简报 - 09:00")
    
    # ==================== Notion 知识库同步 ====================
    
    _safe_add_job(sync_notion_knowledge_task, CronTrigger(hour=23, minute=30),
                  "notion_knowledge_sync", "[Maria] Notion知识库同步 - 23:30")
    
    # ==================== TaskWorker 任务调度引擎 ====================
    
    _safe_add_job(process_pending_tasks, IntervalTrigger(seconds=30),
                  "task_worker", "[TaskWorker] AI员工任务调度 - 每30秒")
    
    _safe_add_job(check_stale_tasks, IntervalTrigger(minutes=5),
                  "task_stale_check", "[TaskWorker] 任务停滞预警 - 每5分钟")
    
    # ==================== 启动调度器 ====================
    
    scheduler.start()
    
    # 输出任务汇总
    jobs = scheduler.get_jobs()
    logger.info(f"✅ 定时任务调度器已启动，共注册 {len(jobs)} 个任务")
    logger.info("=" * 50)
    logger.info("📋 任务列表:")
    for job in jobs:
        logger.info(f"   • {job.name}")
    logger.info("=" * 50)


async def shutdown_scheduler():
    """关闭定时任务"""
    global scheduler, _scheduler_lock_file, _is_scheduler_worker
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("📅 定时任务调度器已关闭")
    
    # 释放调度器锁
    if _scheduler_lock_file:
        try:
            fcntl.flock(_scheduler_lock_file.fileno(), fcntl.LOCK_UN)
            _scheduler_lock_file.close()
            _scheduler_lock_file = None
            _is_scheduler_worker = False
            logger.info("🔓 调度器锁已释放")
        except Exception as e:
            logger.warning(f"释放调度器锁失败: {e}")


def add_job(func, trigger, job_id: str, name: str, **kwargs):
    """动态添加任务"""
    scheduler = get_scheduler()
    scheduler.add_job(
        func,
        trigger,
        id=job_id,
        name=name,
        replace_existing=True,
        **kwargs
    )
    logger.info(f"📅 添加任务: {name}")


def remove_job(job_id: str):
    """移除任务"""
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        logger.info(f"📅 移除任务: {job_id}")
    except Exception as e:
        logger.error(f"移除任务失败: {e}")


def pause_job(job_id: str):
    """暂停任务"""
    scheduler = get_scheduler()
    try:
        scheduler.pause_job(job_id)
        logger.info(f"📅 暂停任务: {job_id}")
    except Exception as e:
        logger.error(f"暂停任务失败: {e}")


def resume_job(job_id: str):
    """恢复任务"""
    scheduler = get_scheduler()
    try:
        scheduler.resume_job(job_id)
        logger.info(f"📅 恢复任务: {job_id}")
    except Exception as e:
        logger.error(f"恢复任务失败: {e}")


def get_jobs():
    """获取所有任务"""
    scheduler = get_scheduler()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "pending": job.pending
        }
        for job in scheduler.get_jobs()
    ]


def get_job_status(job_id: str):
    """获取单个任务状态"""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    if job:
        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "pending": job.pending
        }
    return None


async def run_job_now(job_id: str):
    """立即执行任务"""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    if job:
        logger.info(f"📅 手动触发任务: {job.name}")
        try:
            # 直接调用任务函数
            result = await job.func()
            logger.info(f"📅 任务执行完成: {job.name}")
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            return {"status": "error", "error": str(e)}
    return {"status": "error", "error": "任务不存在"}
