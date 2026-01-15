"""
扫码登录服务
支持抖音、B站、微信视频号的二维码扫码登录
"""
import os
import json
import asyncio
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from uuid import uuid4

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 未安装，扫码登录功能不可用")

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class QRCodeLoginService:
    """二维码扫码登录服务"""
    
    # 平台配置
    PLATFORMS = {
        "douyin": {
            "name": "抖音",
            "login_url": "https://www.douyin.com/",
            "qr_selector": "div.qrcode-image img, img[class*='qrcode'], div[class*='qrcode'] img",
            "login_check_selector": "div[class*='avatar'], img[class*='avatar']",
            "cookie_domain": ".douyin.com"
        },
        "bilibili": {
            "name": "B站",
            "login_url": "https://passport.bilibili.com/login",
            "qr_selector": "div.qrcode-img img, canvas.qrcode-img, img[alt*='二维码']",
            "login_check_selector": "a.header-entry-avatar, div.mini-avatar",
            "cookie_domain": ".bilibili.com"
        },
        "weixin_video": {
            "name": "微信视频号",
            "login_url": "https://channels.weixin.qq.com/platform/login",
            "qr_selector": "img[class*='qrcode'], div[class*='qrcode'] img",
            "login_check_selector": "div[class*='avatar'], span[class*='nickname']",
            "cookie_domain": ".qq.com"
        }
    }
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.active_sessions: Dict[str, Dict] = {}  # session_id -> {context, page, platform}
        self.qr_images_dir = Path("/tmp/qr_images")
        self.qr_images_dir.mkdir(parents=True, exist_ok=True)
    
    async def init_browser(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装，请先安装: pip install playwright && playwright install chromium")
        
        if self.browser is None:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process'
                ]
            )
            logger.info("[扫码登录] Playwright 浏览器已启动")
        return self.browser
    
    async def close_browser(self):
        """关闭浏览器"""
        # 关闭所有活跃会话
        for session_id in list(self.active_sessions.keys()):
            await self.cancel_login(session_id)
        
        if self.browser:
            await self.browser.close()
            self.browser = None
            logger.info("[扫码登录] 浏览器已关闭")
    
    async def start_login(self, platform: str) -> Dict[str, Any]:
        """
        启动扫码登录会话
        返回 session_id 和二维码图片（base64）
        """
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.PLATFORMS[platform]
        session_id = str(uuid4())
        
        try:
            browser = await self.init_browser()
            
            # 创建新的浏览器上下文
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            logger.info(f"[扫码登录] 正在打开 {config['name']} 登录页: {config['login_url']}")
            await page.goto(config["login_url"], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # 等待页面加载
            
            # 保存会话信息
            self.active_sessions[session_id] = {
                "context": context,
                "page": page,
                "platform": platform,
                "created_at": datetime.utcnow()
            }
            
            # 获取二维码图片
            qr_base64 = await self._capture_qrcode(page, platform)
            
            if not qr_base64:
                # 如果没找到二维码，截取整个页面
                screenshot_path = self.qr_images_dir / f"{session_id}_full.png"
                await page.screenshot(path=str(screenshot_path))
                with open(screenshot_path, "rb") as f:
                    qr_base64 = base64.b64encode(f.read()).decode()
                logger.warning(f"[扫码登录] 未找到二维码元素，返回整页截图")
            
            return {
                "session_id": session_id,
                "platform": platform,
                "platform_name": config["name"],
                "qr_image": qr_base64,
                "status": "waiting_scan",
                "message": f"请使用 {config['name']} App 扫描二维码"
            }
            
        except Exception as e:
            logger.error(f"[扫码登录] 启动登录失败: {e}")
            # 清理会话
            if session_id in self.active_sessions:
                await self.cancel_login(session_id)
            raise
    
    async def _capture_qrcode(self, page: Page, platform: str) -> Optional[str]:
        """捕获二维码图片"""
        config = self.PLATFORMS[platform]
        
        try:
            # 尝试找到二维码元素
            selectors = config["qr_selector"].split(", ")
            
            for selector in selectors:
                try:
                    qr_element = await page.wait_for_selector(selector.strip(), timeout=5000)
                    if qr_element:
                        # 截取二维码元素
                        qr_image = await qr_element.screenshot()
                        return base64.b64encode(qr_image).decode()
                except:
                    continue
            
            # 如果是B站，尝试获取canvas
            if platform == "bilibili":
                try:
                    canvas = await page.query_selector("canvas")
                    if canvas:
                        qr_image = await canvas.screenshot()
                        return base64.b64encode(qr_image).decode()
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.debug(f"[扫码登录] 捕获二维码失败: {e}")
            return None
    
    async def check_login_status(self, session_id: str) -> Dict[str, Any]:
        """检查登录状态"""
        if session_id not in self.active_sessions:
            return {
                "session_id": session_id,
                "status": "expired",
                "message": "会话已过期，请重新扫码"
            }
        
        session = self.active_sessions[session_id]
        page = session["page"]
        platform = session["platform"]
        config = self.PLATFORMS[platform]
        
        try:
            # 检查是否已登录（通过查找头像等元素）
            login_selectors = config["login_check_selector"].split(", ")
            
            for selector in login_selectors:
                try:
                    element = await page.query_selector(selector.strip())
                    if element:
                        # 登录成功！获取Cookie
                        cookies = await session["context"].cookies()
                        
                        # 保存Cookie到数据库
                        await self._save_cookies(platform, cookies)
                        
                        # 清理会话
                        await self.cancel_login(session_id)
                        
                        return {
                            "session_id": session_id,
                            "status": "success",
                            "platform": platform,
                            "message": f"{config['name']} 登录成功！"
                        }
                except:
                    continue
            
            # 检查会话是否超时（5分钟）
            if datetime.utcnow() - session["created_at"] > timedelta(minutes=5):
                await self.cancel_login(session_id)
                return {
                    "session_id": session_id,
                    "status": "timeout",
                    "message": "扫码超时，请重新获取二维码"
                }
            
            return {
                "session_id": session_id,
                "status": "waiting",
                "message": "等待扫码..."
            }
            
        except Exception as e:
            logger.error(f"[扫码登录] 检查状态失败: {e}")
            return {
                "session_id": session_id,
                "status": "error",
                "message": str(e)
            }
    
    async def _save_cookies(self, platform: str, cookies: List[Dict]) -> bool:
        """保存Cookie到数据库"""
        try:
            config = self.PLATFORMS[platform]
            
            # 过滤相关域名的Cookie
            domain = config["cookie_domain"]
            relevant_cookies = [
                c for c in cookies 
                if domain in c.get("domain", "") or c.get("domain", "").endswith(domain.lstrip("."))
            ]
            
            async with AsyncSessionLocal() as db:
                expire_at = datetime.utcnow() + timedelta(days=30)  # Cookie有效期30天
                
                await db.execute(
                    text("""
                        UPDATE social_platform_auth 
                        SET is_logged_in = TRUE,
                            cookies_data = :cookies,
                            cookies_expire_at = :expire_at,
                            last_login_at = NOW(),
                            error_message = NULL,
                            updated_at = NOW()
                        WHERE platform = :platform
                    """),
                    {
                        "platform": platform,
                        "cookies": json.dumps(relevant_cookies),
                        "expire_at": expire_at
                    }
                )
                await db.commit()
                
            logger.info(f"[扫码登录] {config['name']} Cookie 已保存，共 {len(relevant_cookies)} 个")
            return True
            
        except Exception as e:
            logger.error(f"[扫码登录] 保存Cookie失败: {e}")
            return False
    
    async def cancel_login(self, session_id: str) -> bool:
        """取消登录会话"""
        if session_id not in self.active_sessions:
            return False
        
        try:
            session = self.active_sessions[session_id]
            await session["context"].close()
            del self.active_sessions[session_id]
            logger.info(f"[扫码登录] 会话 {session_id[:8]}... 已取消")
            return True
        except Exception as e:
            logger.error(f"[扫码登录] 取消会话失败: {e}")
            return False
    
    async def refresh_qrcode(self, session_id: str) -> Dict[str, Any]:
        """刷新二维码"""
        if session_id not in self.active_sessions:
            return {
                "status": "expired",
                "message": "会话已过期"
            }
        
        session = self.active_sessions[session_id]
        page = session["page"]
        platform = session["platform"]
        config = self.PLATFORMS[platform]
        
        try:
            # 刷新页面
            await page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 重新获取二维码
            qr_base64 = await self._capture_qrcode(page, platform)
            
            if not qr_base64:
                screenshot_path = self.qr_images_dir / f"{session_id}_refresh.png"
                await page.screenshot(path=str(screenshot_path))
                with open(screenshot_path, "rb") as f:
                    qr_base64 = base64.b64encode(f.read()).decode()
            
            # 重置创建时间
            session["created_at"] = datetime.utcnow()
            
            return {
                "session_id": session_id,
                "qr_image": qr_base64,
                "status": "refreshed",
                "message": "二维码已刷新"
            }
            
        except Exception as e:
            logger.error(f"[扫码登录] 刷新二维码失败: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# 全局实例
qrcode_login_service = QRCodeLoginService()
