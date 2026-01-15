"""
素材采集员Agent - 小采
负责从社交媒体平台收集物流相关素材
"""
import httpx
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from app.agents.base import BaseAgent
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from app.core.config import settings
from sqlalchemy import text


class AssetCollectorAgent(BaseAgent):
    """素材采集员 - 从社交媒体收集物流相关素材"""
    
    agent_type = AgentType.ASSET_COLLECTOR
    name = "小采"
    description = "负责从社交媒体和素材网站自动收集物流相关视频、图片和音频素材"
    enable_logistics_expertise = False  # 素材采集不需要物流专业知识
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是小采，一位专业的素材采集员。
你的职责是从各种平台搜索和采集高质量的物流相关素材（视频、图片、音频）。

工作原则：
1. 只采集与物流、仓储、运输相关的素材
2. 优先选择高清、专业的素材
3. 确保素材版权合规
4. 自动去重，避免重复采集
"""
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理采集任务"""
        platforms = input_data.get("platforms", ["pexels", "pixabay"])
        keywords = input_data.get("keywords", self.SEARCH_KEYWORDS[:3])
        
        assets = await self.run_collection_task(platforms=platforms, keywords=keywords)
        
        return {
            "status": "success",
            "found": len(assets),
            "assets": assets
        }
    
    # 支持的平台
    PLATFORMS = {
        "xiaohongshu": "小红书",
        "douyin": "抖音",
        "bilibili": "B站",
        "weixin_video": "微信视频号",
        "pexels": "Pexels",  # 免版权素材网站
        "pixabay": "Pixabay"  # 免版权素材网站
    }
    
    # 搜索关键词
    SEARCH_KEYWORDS = [
        "物流仓库",
        "港口集装箱",
        "货车运输",
        "快递分拣",
        "跨境电商物流",
        "FBA头程",
        "海运集装箱",
        "空运货物",
        "物流科技",
        "智能仓储"
    ]
    
    async def collect_from_platform(
        self, 
        platform: str, 
        keyword: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """从指定平台采集素材"""
        logger.info(f"[小采] 从 {self.PLATFORMS.get(platform, platform)} 搜索: {keyword}")
        
        results = []
        
        try:
            if platform == "pexels":
                results = await self._search_pexels(keyword, max_results)
            elif platform == "pixabay":
                results = await self._search_pixabay(keyword, max_results)
            else:
                # 其他平台需要相应的API或爬虫
                logger.warning(f"[小采] 平台 {platform} 暂未实现自动采集")
                
        except Exception as e:
            logger.error(f"[小采] 采集失败: {e}")
            
        return results
    
    async def _search_pexels(self, keyword: str, max_results: int) -> List[Dict[str, Any]]:
        """从Pexels搜索视频素材"""
        results = []
        
        # Pexels API需要API Key
        api_key = settings.PEXELS_API_KEY if hasattr(settings, 'PEXELS_API_KEY') else None
        if not api_key:
            logger.warning("[小采] 未配置Pexels API Key")
            return results
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.pexels.com/videos/search",
                    params={"query": keyword, "per_page": max_results},
                    headers={"Authorization": api_key},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for video in data.get("videos", []):
                        # 获取最佳质量的视频文件
                        video_files = video.get("video_files", [])
                        best_file = max(video_files, key=lambda x: x.get("width", 0)) if video_files else None
                        
                        if best_file:
                            results.append({
                                "name": f"Pexels_{video['id']}",
                                "platform": "pexels",
                                "source_url": video.get("url"),
                                "file_url": best_file.get("link"),
                                "thumbnail_url": video.get("image"),
                                "type": "video",
                                "duration": video.get("duration"),
                                "width": best_file.get("width"),
                                "height": best_file.get("height"),
                                "tags": [keyword],
                                "author": video.get("user", {}).get("name")
                            })
            except Exception as e:
                logger.error(f"[小采] Pexels搜索失败: {e}")
                
        return results
    
    async def _search_pixabay(self, keyword: str, max_results: int) -> List[Dict[str, Any]]:
        """从Pixabay搜索素材"""
        results = []
        
        api_key = settings.PIXABAY_API_KEY if hasattr(settings, 'PIXABAY_API_KEY') else None
        if not api_key:
            logger.warning("[小采] 未配置Pixabay API Key")
            return results
            
        async with httpx.AsyncClient() as client:
            try:
                # 搜索视频
                response = await client.get(
                    "https://pixabay.com/api/videos/",
                    params={
                        "key": api_key,
                        "q": keyword,
                        "per_page": max_results
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for video in data.get("hits", []):
                        videos = video.get("videos", {})
                        large = videos.get("large", {})
                        
                        if large.get("url"):
                            results.append({
                                "name": f"Pixabay_{video['id']}",
                                "platform": "pixabay",
                                "source_url": video.get("pageURL"),
                                "file_url": large.get("url"),
                                "thumbnail_url": video.get("pictureId"),
                                "type": "video",
                                "duration": video.get("duration"),
                                "width": large.get("width"),
                                "height": large.get("height"),
                                "tags": video.get("tags", "").split(", "),
                                "author": video.get("user")
                            })
            except Exception as e:
                logger.error(f"[小采] Pixabay搜索失败: {e}")
                
        return results
    
    async def save_collected_assets(self, assets: List[Dict[str, Any]]) -> int:
        """保存采集到的素材到数据库"""
        saved_count = 0
        
        async with AsyncSessionLocal() as db:
            for asset in assets:
                try:
                    # 检查是否已存在（通过source_url判断）
                    result = await db.execute(
                        text("SELECT id FROM assets WHERE file_url = :url"),
                        {"url": asset.get("file_url")}
                    )
                    if result.fetchone():
                        logger.debug(f"[小采] 素材已存在，跳过: {asset.get('name')}")
                        continue
                    
                    # 插入新素材
                    await db.execute(
                        text("""
                            INSERT INTO assets (name, type, category, file_url, thumbnail_url, duration)
                            VALUES (:name, :type, :category, :file_url, :thumbnail_url, :duration)
                        """),
                        {
                            "name": asset.get("name"),
                            "type": asset.get("type", "video"),
                            "category": asset.get("platform"),
                            "file_url": asset.get("file_url"),
                            "thumbnail_url": asset.get("thumbnail_url"),
                            "duration": asset.get("duration")
                        }
                    )
                    saved_count += 1
                    logger.info(f"[小采] 保存素材: {asset.get('name')}")
                    
                except Exception as e:
                    logger.error(f"[小采] 保存素材失败: {e}")
                    
            await db.commit()
            
        return saved_count
    
    async def run_collection_task(self, platforms: List[str] = None, keywords: List[str] = None):
        """执行采集任务"""
        platforms = platforms or ["pexels", "pixabay"]
        keywords = keywords or self.SEARCH_KEYWORDS[:3]  # 默认取前3个关键词
        
        logger.info(f"[小采] 开始素材采集任务，平台: {platforms}, 关键词: {keywords}")
        
        all_assets = []
        
        for platform in platforms:
            for keyword in keywords:
                try:
                    assets = await self.collect_from_platform(platform, keyword, max_results=5)
                    all_assets.extend(assets)
                except Exception as e:
                    logger.error(f"[小采] 采集异常: {e}")
        
        # 保存到数据库
        if all_assets:
            saved = await self.save_collected_assets(all_assets)
            logger.info(f"[小采] 采集完成，共发现 {len(all_assets)} 个素材，保存 {saved} 个新素材")
            
            # 记录工作日志
            await self.log_work(
                task_type="素材采集",
                status="success",
                output_data={
                    "platforms": platforms,
                    "keywords": keywords,
                    "found": len(all_assets),
                    "saved": saved
                }
            )
        else:
            logger.warning("[小采] 本次采集未发现新素材")
            
        return all_assets
    
    async def log_work(self, task_type: str, status: str, output_data: dict = None, error_message: str = None):
        """记录工作日志"""
        try:
            async with AsyncSessionLocal() as db:
                # 获取agent ID
                result = await db.execute(
                    text("SELECT id FROM ai_agents WHERE agent_type = :type"),
                    {"type": self.agent_type.value}
                )
                row = result.fetchone()
                if not row:
                    return
                    
                agent_id = row[0]
                
                # 插入工作日志
                await db.execute(
                    text("""
                        INSERT INTO work_logs (agent_id, task_type, status, started_at, completed_at, output_data, error_message)
                        VALUES (:agent_id, :task_type, :status, :started_at, :completed_at, :output_data, :error_message)
                    """),
                    {
                        "agent_id": agent_id,
                        "task_type": task_type,
                        "status": status,
                        "started_at": datetime.utcnow(),
                        "completed_at": datetime.utcnow(),
                        "output_data": json.dumps(output_data) if output_data else None,
                        "error_message": error_message
                    }
                )
                
                # 更新任务计数
                await db.execute(
                    text("""
                        UPDATE ai_agents 
                        SET tasks_completed_today = tasks_completed_today + 1,
                            total_tasks_completed = total_tasks_completed + 1,
                            last_active_at = :now
                        WHERE id = :id
                    """),
                    {"id": agent_id, "now": datetime.utcnow()}
                )
                
                await db.commit()
        except Exception as e:
            logger.error(f"[小采] 记录工作日志失败: {e}")


# 创建全局实例
asset_collector = AssetCollectorAgent()
