"""
素材采集定时任务 - 小采执行
"""
from loguru import logger


async def asset_collection_task():
    """
    素材采集任务
    从Pexels、Pixabay等平台采集物流相关素材
    """
    logger.info("[小采] 开始执行素材采集任务...")
    
    try:
        from app.agents.asset_collector import asset_collector
        
        # 执行采集
        assets = await asset_collector.run_collection_task()
        
        logger.info(f"[小采] 素材采集任务完成，发现 {len(assets)} 个素材")
        return {
            "status": "success",
            "found": len(assets)
        }
        
    except Exception as e:
        logger.error(f"[小采] 素材采集任务失败: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
