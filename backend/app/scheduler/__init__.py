"""
定时任务模块
使用APScheduler实现定时任务调度
支持7个AI员工的24小时自动化工作
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
    
    # ==================== 导入任务 ====================
    
    # 跟进任务
    from app.scheduler.follow_tasks import (
        daily_follow_check,
        check_no_reply_customers,
        daily_summary_task,
        reset_daily_stats
    )
    
    # 市场情报任务
    from app.scheduler.market_tasks import (
        collect_market_intelligence,
        send_boss_daily_report,
        send_boss_weekly_report,
        check_urgent_intel,
        collect_eu_customs_news
    )
    
    # 内容发布任务
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
    
    # 素材采集任务
    from app.scheduler.asset_tasks import asset_collection_task
    
    # ==================== 小跟任务 ====================
    
    # 每日跟进检查 - 每天早上9点（第一批）
    scheduler.add_job(
        daily_follow_check,
        CronTrigger(hour=9, minute=0),
        id="daily_follow_check_morning",
        name="[小跟] 每日跟进检查(上午)",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小跟] 每日跟进检查(上午) - 09:00")
    
    # 每日跟进检查 - 每天下午14点（第二批）
    scheduler.add_job(
        daily_follow_check,
        CronTrigger(hour=14, minute=0),
        id="daily_follow_check_afternoon",
        name="[小跟] 每日跟进检查(下午)",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小跟] 每日跟进检查(下午) - 14:00")
    
    # 未回复检查 - 每4小时
    scheduler.add_job(
        check_no_reply_customers,
        IntervalTrigger(hours=4),
        id="check_no_reply",
        name="[小跟] 未回复客户检查",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小跟] 未回复客户检查 - 每4小时")
    
    # ==================== 小调任务 ====================
    
    # 导入小调企业微信汇报任务
    from app.scheduler.coordinator_tasks import (
        coordinator_wechat_daily_report,
        coordinator_wechat_morning_greeting
    )
    
    # 每日汇总 - 每天下午6点
    scheduler.add_job(
        daily_summary_task,
        CronTrigger(hour=settings.DAILY_SUMMARY_HOUR, minute=0),
        id="daily_summary",
        name="[小调] 每日工作汇总",
        replace_existing=True
    )
    logger.info(f"📅 注册任务: [小调] 每日工作汇总 - {settings.DAILY_SUMMARY_HOUR}:00")
    
    # 企业微信日报 - 每天下午6点30分发送给管理员
    scheduler.add_job(
        coordinator_wechat_daily_report,
        CronTrigger(hour=18, minute=30),
        id="coordinator_wechat_daily_report",
        name="[小调] 企业微信日报推送",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小调] 企业微信日报推送 - 18:30")
    
    # 早间问候 - 每天早上8点30分
    scheduler.add_job(
        coordinator_wechat_morning_greeting,
        CronTrigger(hour=8, minute=30),
        id="coordinator_wechat_morning",
        name="[小调] 企业微信早间问候",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小调] 企业微信早间问候 - 08:30")
    
    # 重置每日统计 - 每天凌晨0点
    scheduler.add_job(
        reset_daily_stats,
        CronTrigger(hour=0, minute=5),
        id="reset_daily_stats",
        name="[系统] 重置每日统计",
        replace_existing=True
    )
    logger.info("📅 注册任务: [系统] 重置每日统计 - 00:05")
    
    # ==================== 小猎任务 (24小时智能搜索) ====================
    
    # 导入加强搜索和夜间搜索任务
    from app.scheduler.content_tasks import (
        lead_hunt_intensive_task,
        lead_hunt_night_task
    )
    
    # 常规线索搜索 - 每小时执行（工作时间 7-23点）
    scheduler.add_job(
        lead_hunt_task,
        CronTrigger(hour='7-23', minute=15),
        id="lead_hunt_regular",
        name="[小猎] 常规线索搜索",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小猎] 常规线索搜索 - 每小时(7:15-23:15)")
    
    # 加强线索搜索 - 高峰时段（上午9-11点、下午14-17点、晚间19-21点）
    scheduler.add_job(
        lead_hunt_intensive_task,
        CronTrigger(hour='9,10,14,15,16,19,20', minute=45),
        id="lead_hunt_intensive",
        name="[小猎] 加强线索搜索",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小猎] 加强线索搜索 - 高峰时段(9/10/14/15/16/19/20点)")
    
    # 夜间轻量搜索 - 凌晨时段（0-6点，每2小时）
    scheduler.add_job(
        lead_hunt_night_task,
        CronTrigger(hour='0,2,4,6', minute=30),
        id="lead_hunt_night",
        name="[小猎] 夜间轻量搜索",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小猎] 夜间轻量搜索 - 凌晨(0/2/4/6点)")
    
    # ==================== 小析任务 ====================
    
    # 市场情报采集 - 每日早上6点
    scheduler.add_job(
        collect_market_intelligence,
        CronTrigger(hour=6, minute=0),
        id="market_intel_collect",
        name="[小析] 市场情报采集",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小析] 市场情报采集 - 06:00")
    
    # 老板日报 - 每日早上8点
    scheduler.add_job(
        send_boss_daily_report,
        CronTrigger(hour=8, minute=0),
        id="boss_daily_report",
        name="[小析] 老板日报推送",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小析] 老板日报推送 - 08:00")
    
    # 老板周报 - 每周一早上8点
    scheduler.add_job(
        send_boss_weekly_report,
        CronTrigger(day_of_week='mon', hour=8, minute=30),
        id="boss_weekly_report",
        name="[小析] 老板周报推送",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小析] 老板周报推送 - 每周一 08:30")
    
    # 紧急情报检查 - 每小时
    scheduler.add_job(
        check_urgent_intel,
        IntervalTrigger(hours=1),
        id="urgent_intel_check",
        name="[小析] 紧急情报检查",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小析] 紧急情报检查 - 每小时")
    
    # ==================== 小欧间谍任务 ====================
    
    # 欧洲海关新闻采集 - 每日早上6点
    scheduler.add_job(
        collect_eu_customs_news,
        CronTrigger(hour=6, minute=0),
        id="eu_customs_news_collect",
        name="[小欧间谍] 欧洲海关新闻采集",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小欧间谍] 欧洲海关新闻采集 - 06:00")
    
    # ==================== 小视任务 ====================
    
    # 自动视频生成 - 每日上午10点
    scheduler.add_job(
        auto_video_generation,
        CronTrigger(hour=10, minute=0),
        id="auto_video_generation",
        name="[小视] 自动视频生成",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小视] 自动视频生成 - 10:00")
    
    # ==================== 小文任务 ====================
    
    # 自动内容发布(企业微信) - 每周一/三/五下午3点
    scheduler.add_job(
        auto_content_publish,
        CronTrigger(day_of_week='mon,wed,fri', hour=15, minute=0),
        id="auto_content_publish",
        name="[小文] 企业微信文案发布",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小文] 企业微信文案发布 - 周一/三/五 15:00")
    
    # 小红书内容发布 - 每周二/四/六中午12点（小红书高峰时段）
    scheduler.add_job(
        auto_xiaohongshu_publish,
        CronTrigger(day_of_week='tue,thu,sat', hour=12, minute=0),
        id="auto_xiaohongshu_publish",
        name="[小文] 小红书笔记发布",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小文] 小红书笔记发布 - 周二/四/六 12:00")
    
    # ==================== 小析2任务 ====================
    
    # 知识库更新 - 每日23点
    scheduler.add_job(
        knowledge_base_update,
        CronTrigger(hour=23, minute=0),
        id="knowledge_base_update",
        name="[小析2] 知识库更新",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小析2] 知识库更新 - 23:00")
    
    # ==================== 小媒任务 (内容营销) ====================
    
    # 每日内容生成 - 凌晨5点生成明天的内容
    scheduler.add_job(
        daily_content_generation,
        CronTrigger(hour=5, minute=0),
        id="daily_content_generation",
        name="[小媒] 每日内容生成",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小媒] 每日内容生成 - 05:00")
    
    # 批量内容生成 - 每周日凌晨4点生成下周内容
    scheduler.add_job(
        batch_content_generation,
        CronTrigger(day_of_week='sun', hour=4, minute=0),
        id="batch_content_generation",
        name="[小媒] 批量内容生成",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小媒] 批量内容生成 - 每周日 04:00")
    
    # 内容发布提醒 - 每天上午9点
    scheduler.add_job(
        content_publish_reminder,
        CronTrigger(hour=9, minute=5),
        id="content_publish_reminder",
        name="[小媒] 内容发布提醒",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小媒] 内容发布提醒 - 09:05")
    
    # ==================== 小采任务 ====================
    
    # 素材采集 - 每日上午7点和下午16点
    scheduler.add_job(
        asset_collection_task,
        CronTrigger(hour=7, minute=0),
        id="asset_collection_morning",
        name="[小采] 素材采集(上午)",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小采] 素材采集(上午) - 07:00")
    
    scheduler.add_job(
        asset_collection_task,
        CronTrigger(hour=16, minute=0),
        id="asset_collection_afternoon",
        name="[小采] 素材采集(下午)",
        replace_existing=True
    )
    logger.info("📅 注册任务: [小采] 素材采集(下午) - 16:00")
    
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
