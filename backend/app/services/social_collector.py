"""
社交媒体素材采集服务
使用 Playwright 实现小红书、抖音、B站的素材采集
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 未安装，社交媒体采集功能不可用")

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class SocialMediaCollector:
    """社交媒体素材采集器"""
    
    # 平台配置
    PLATFORMS = {
        "xiaohongshu": {
            "name": "小红书",
            "login_url": "https://www.xiaohongshu.com",
            "search_url": "https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes",
            "cookie_domain": ".xiaohongshu.com"
        },
        "douyin": {
            "name": "抖音",
            "login_url": "https://www.douyin.com",
            "search_url": "https://www.douyin.com/search/{keyword}?type=video",
            "cookie_domain": ".douyin.com"
        },
        "bilibili": {
            "name": "B站",
            "login_url": "https://www.bilibili.com",
            "search_url": "https://search.bilibili.com/all?keyword={keyword}&order=totalrank",
            "cookie_domain": ".bilibili.com"
        }
    }
    
    # 物流相关搜索关键词
    SEARCH_KEYWORDS = [
        "物流仓库",
        "跨境物流",
        "亚马逊FBA",
        "海运集装箱",
        "空运货代",
        "国际快递",
        "物流科技",
        "智能仓储"
    ]
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.browser_state_dir = Path("/tmp/browser_states")
        self.browser_state_dir.mkdir(parents=True, exist_ok=True)
        
    async def init_browser(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")
            
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
        return self.browser
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
    
    def _get_state_path(self, platform: str) -> str:
        """获取平台状态文件路径"""
        return str(self.browser_state_dir / f"{platform}_state.json")
    
    async def get_login_page_url(self, platform: str) -> Dict[str, Any]:
        """获取登录页面URL（用于前端展示二维码）"""
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.PLATFORMS[platform]
        return {
            "platform": platform,
            "name": config["name"],
            "login_url": config["login_url"],
            "instructions": f"请使用 {config['name']} App 扫码登录"
        }
    
    async def start_login_session(self, platform: str) -> Dict[str, Any]:
        """启动登录会话，返回WebSocket连接信息供前端连接"""
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        try:
            browser = await self.init_browser()
            config = self.PLATFORMS[platform]
            
            # 创建新的浏览器上下文
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            await page.goto(config["login_url"], wait_until="networkidle", timeout=30000)
            
            # 截图当前页面（包含二维码）
            screenshot_path = f"/tmp/{platform}_login.png"
            await page.screenshot(path=screenshot_path)
            
            return {
                "status": "waiting_scan",
                "platform": platform,
                "screenshot_path": screenshot_path,
                "message": f"请使用 {config['name']} App 扫描二维码登录"
            }
            
        except Exception as e:
            logger.error(f"启动登录会话失败: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def check_login_status(self, platform: str) -> Dict[str, Any]:
        """检查登录状态"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT is_logged_in, login_username, login_avatar_url, 
                               cookies_expire_at, last_login_at, total_collected, today_collected
                        FROM social_platform_auth 
                        WHERE platform = :platform
                    """),
                    {"platform": platform}
                )
                row = result.fetchone()
                
                if not row:
                    return {
                        "platform": platform,
                        "is_logged_in": False,
                        "message": "平台未配置"
                    }
                
                is_logged_in = row[0]
                cookies_expire_at = row[3]
                
                # 检查Cookie是否过期
                if is_logged_in and cookies_expire_at:
                    if datetime.now(cookies_expire_at.tzinfo) > cookies_expire_at:
                        is_logged_in = False
                        # 更新数据库状态
                        await db.execute(
                            text("UPDATE social_platform_auth SET is_logged_in = FALSE WHERE platform = :platform"),
                            {"platform": platform}
                        )
                        await db.commit()
                
                return {
                    "platform": platform,
                    "name": self.PLATFORMS.get(platform, {}).get("name", platform),
                    "is_logged_in": is_logged_in,
                    "username": row[1],
                    "avatar_url": row[2],
                    "expires_at": row[3].isoformat() if row[3] else None,
                    "last_login_at": row[4].isoformat() if row[4] else None,
                    "total_collected": row[5] or 0,
                    "today_collected": row[6] or 0
                }
                
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return {
                "platform": platform,
                "is_logged_in": False,
                "error": str(e)
            }
    
    async def save_login_state(
        self, 
        platform: str, 
        cookies: List[Dict],
        username: str = None,
        avatar_url: str = None
    ) -> bool:
        """保存登录状态到数据库"""
        try:
            async with AsyncSessionLocal() as db:
                # 计算Cookie过期时间（默认7天）
                expire_at = datetime.utcnow() + timedelta(days=7)
                
                await db.execute(
                    text("""
                        UPDATE social_platform_auth 
                        SET is_logged_in = TRUE,
                            login_username = :username,
                            login_avatar_url = :avatar_url,
                            cookies_data = :cookies,
                            cookies_expire_at = :expire_at,
                            last_login_at = NOW(),
                            browser_state_path = :state_path,
                            error_message = NULL,
                            updated_at = NOW()
                        WHERE platform = :platform
                    """),
                    {
                        "platform": platform,
                        "username": username,
                        "avatar_url": avatar_url,
                        "cookies": json.dumps(cookies),
                        "expire_at": expire_at,
                        "state_path": self._get_state_path(platform)
                    }
                )
                await db.commit()
                logger.info(f"[小采] {platform} 登录状态已保存")
                return True
                
        except Exception as e:
            logger.error(f"保存登录状态失败: {e}")
            return False
    
    async def load_login_state(self, platform: str) -> Optional[List[Dict]]:
        """从数据库加载登录状态"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT cookies_data FROM social_platform_auth WHERE platform = :platform AND is_logged_in = TRUE"),
                    {"platform": platform}
                )
                row = result.fetchone()
                
                if row and row[0]:
                    return json.loads(row[0])
                return None
                
        except Exception as e:
            logger.error(f"加载登录状态失败: {e}")
            return None
    
    async def collect_from_xiaohongshu(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """从小红书采集素材"""
        results = []
        
        try:
            cookies = await self.load_login_state("xiaohongshu")
            if not cookies:
                logger.warning("[小采] 小红书未登录，跳过采集")
                return results
            
            browser = await self.init_browser()
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            # 加载Cookie
            await context.add_cookies(cookies)
            
            page = await context.new_page()
            search_url = self.PLATFORMS["xiaohongshu"]["search_url"].format(keyword=keyword)
            
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # 等待动态加载
            
            # 解析搜索结果
            notes = await page.query_selector_all('section.note-item')
            
            for i, note in enumerate(notes[:max_results]):
                try:
                    # 获取标题
                    title_el = await note.query_selector('.title span')
                    title = await title_el.inner_text() if title_el else f"小红书笔记_{i}"
                    
                    # 获取封面图
                    img_el = await note.query_selector('img')
                    cover_url = await img_el.get_attribute('src') if img_el else None
                    
                    # 获取链接
                    link_el = await note.query_selector('a')
                    link = await link_el.get_attribute('href') if link_el else None
                    
                    if cover_url:
                        results.append({
                            "name": title[:50],
                            "platform": "xiaohongshu",
                            "source_url": f"https://www.xiaohongshu.com{link}" if link else None,
                            "file_url": cover_url,
                            "thumbnail_url": cover_url,
                            "type": "image",
                            "tags": [keyword, "小红书"],
                            "description": title
                        })
                except Exception as e:
                    logger.debug(f"解析小红书笔记失败: {e}")
                    continue
            
            await context.close()
            logger.info(f"[小采] 从小红书采集到 {len(results)} 个素材")
            
        except Exception as e:
            logger.error(f"[小采] 小红书采集失败: {e}")
        
        return results
    
    async def collect_from_bilibili(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """从B站采集素材（B站API相对开放，可以不登录采集）"""
        results = []
        
        try:
            import httpx
            
            # 使用B站搜索API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.bilibili.com/x/web-interface/search/type",
                    params={
                        "keyword": keyword,
                        "search_type": "video",
                        "page": 1,
                        "pagesize": max_results
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://www.bilibili.com"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        for video in data.get("data", {}).get("result", []):
                            # 清理标题中的HTML标签
                            title = video.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", "")
                            
                            results.append({
                                "name": title[:50],
                                "platform": "bilibili",
                                "source_url": f"https://www.bilibili.com/video/{video.get('bvid')}",
                                "file_url": f"https:{video.get('pic')}" if video.get('pic') else None,
                                "thumbnail_url": f"https:{video.get('pic')}" if video.get('pic') else None,
                                "type": "video",
                                "duration": video.get("duration", "0:00"),
                                "tags": [keyword, "B站"],
                                "author": video.get("author"),
                                "play_count": video.get("play"),
                                "description": video.get("description", "")[:200]
                            })
            
            logger.info(f"[小采] 从B站采集到 {len(results)} 个素材")
            
        except Exception as e:
            logger.error(f"[小采] B站采集失败: {e}")
        
        return results
    
    async def collect_from_douyin(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """从抖音采集素材"""
        results = []
        
        try:
            cookies = await self.load_login_state("douyin")
            if not cookies:
                logger.warning("[小采] 抖音未登录，跳过采集")
                return results
            
            browser = await self.init_browser()
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            await context.add_cookies(cookies)
            page = await context.new_page()
            
            search_url = self.PLATFORMS["douyin"]["search_url"].format(keyword=keyword)
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            # 解析视频列表
            videos = await page.query_selector_all('[class*="video-card"]')
            
            for i, video in enumerate(videos[:max_results]):
                try:
                    # 获取封面
                    img_el = await video.query_selector('img')
                    cover_url = await img_el.get_attribute('src') if img_el else None
                    
                    # 获取标题
                    title_el = await video.query_selector('[class*="title"]')
                    title = await title_el.inner_text() if title_el else f"抖音视频_{i}"
                    
                    if cover_url:
                        results.append({
                            "name": title[:50],
                            "platform": "douyin",
                            "source_url": None,
                            "file_url": cover_url,
                            "thumbnail_url": cover_url,
                            "type": "video",
                            "tags": [keyword, "抖音"],
                            "description": title
                        })
                except Exception as e:
                    logger.debug(f"解析抖音视频失败: {e}")
                    continue
            
            await context.close()
            logger.info(f"[小采] 从抖音采集到 {len(results)} 个素材")
            
        except Exception as e:
            logger.error(f"[小采] 抖音采集失败: {e}")
        
        return results
    
    async def run_collection(
        self, 
        platforms: List[str] = None, 
        keywords: List[str] = None,
        max_per_platform: int = 5
    ) -> Dict[str, Any]:
        """运行采集任务"""
        platforms = platforms or ["bilibili"]  # 默认只采集B站（不需要登录）
        keywords = keywords or self.SEARCH_KEYWORDS[:2]
        
        all_results = []
        platform_stats = {}
        
        for platform in platforms:
            platform_results = []
            
            for keyword in keywords:
                try:
                    if platform == "xiaohongshu":
                        results = await self.collect_from_xiaohongshu(keyword, max_per_platform)
                    elif platform == "bilibili":
                        results = await self.collect_from_bilibili(keyword, max_per_platform)
                    elif platform == "douyin":
                        results = await self.collect_from_douyin(keyword, max_per_platform)
                    else:
                        logger.warning(f"[小采] 不支持的平台: {platform}")
                        continue
                    
                    platform_results.extend(results)
                    
                except Exception as e:
                    logger.error(f"[小采] {platform} 采集 {keyword} 失败: {e}")
            
            all_results.extend(platform_results)
            platform_stats[platform] = len(platform_results)
        
        # 保存到数据库
        saved_count = 0
        if all_results:
            saved_count = await self._save_results(all_results)
        
        # 更新采集统计
        await self._update_stats(platform_stats)
        
        return {
            "total_found": len(all_results),
            "saved": saved_count,
            "platforms": platform_stats,
            "keywords": keywords
        }
    
    async def _save_results(self, results: List[Dict]) -> int:
        """保存采集结果到数据库"""
        saved = 0
        
        for item in results:
            try:
                async with AsyncSessionLocal() as db:
                    # 检查是否已存在
                    check = await db.execute(
                        text("SELECT id FROM assets WHERE file_url = :url"),
                        {"url": item.get("file_url")}
                    )
                    if check.fetchone():
                        continue
                    
                    # 插入新素材
                    await db.execute(
                        text("""
                            INSERT INTO assets (name, type, category, file_url, thumbnail_url, description)
                            VALUES (:name, :type, :category, :file_url, :thumbnail_url, :description)
                        """),
                        {
                            "name": item.get("name", "未命名")[:100],
                            "type": item.get("type", "image"),
                            "category": item.get("platform", "unknown"),
                            "file_url": item.get("file_url"),
                            "thumbnail_url": item.get("thumbnail_url"),
                            "description": (item.get("description", "") or "")[:500]
                        }
                    )
                    await db.commit()
                    saved += 1
                    
            except Exception as e:
                logger.debug(f"保存素材失败: {e}")
        
        return saved
    
    async def _update_stats(self, platform_stats: Dict[str, int]):
        """更新平台采集统计"""
        try:
            async with AsyncSessionLocal() as db:
                for platform, count in platform_stats.items():
                    await db.execute(
                        text("""
                            UPDATE social_platform_auth 
                            SET total_collected = total_collected + :count,
                                today_collected = today_collected + :count,
                                last_collect_at = NOW()
                            WHERE platform = :platform
                        """),
                        {"platform": platform, "count": count}
                    )
                await db.commit()
        except Exception as e:
            logger.error(f"更新统计失败: {e}")


# 全局实例
social_collector = SocialMediaCollector()
