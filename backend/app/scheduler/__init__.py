"""
定时任务模块
使用APScheduler实现定时任务调度
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import settings


# 全局调度器实例
scheduler: AsyncIOScheduler = None


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
    
    global scheduler
    scheduler = get_scheduler()
    
    # 导入任务
    from app.scheduler.follow_tasks import (
        daily_follow_check,
        check_no_reply_customers,
        daily_summary_task,
        reset_daily_stats
    )
    
    # 每日跟进检查 - 每天早上9点
    scheduler.add_job(
        daily_follow_check,
        CronTrigger(hour=settings.DAILY_FOLLOW_CHECK_HOUR, minute=0),
        id="daily_follow_check",
        name="每日跟进检查",
        replace_existing=True
    )
    logger.info(f"📅 注册任务: 每日跟进检查 (每天 {settings.DAILY_FOLLOW_CHECK_HOUR}:00)")
    
    # 未回复检查 - 每4小时
    scheduler.add_job(
        check_no_reply_customers,
        IntervalTrigger(hours=4),
        id="check_no_reply",
        name="未回复客户检查",
        replace_existing=True
    )
    logger.info("📅 注册任务: 未回复客户检查 (每4小时)")
    
    # 每日汇总 - 每天下午6点
    scheduler.add_job(
        daily_summary_task,
        CronTrigger(hour=settings.DAILY_SUMMARY_HOUR, minute=0),
        id="daily_summary",
        name="每日工作汇总",
        replace_existing=True
    )
    logger.info(f"📅 注册任务: 每日工作汇总 (每天 {settings.DAILY_SUMMARY_HOUR}:00)")
    
    # 重置每日统计 - 每天凌晨0点
    scheduler.add_job(
        reset_daily_stats,
        CronTrigger(hour=0, minute=5),
        id="reset_daily_stats",
        name="重置每日统计",
        replace_existing=True
    )
    logger.info("📅 注册任务: 重置每日统计 (每天 00:05)")
    
    # 启动调度器
    scheduler.start()
    logger.info("✅ 定时任务调度器已启动")


async def shutdown_scheduler():
    """关闭定时任务"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("📅 定时任务调度器已关闭")


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


def get_jobs():
    """获取所有任务"""
    scheduler = get_scheduler()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        }
        for job in scheduler.get_jobs()
    ]
