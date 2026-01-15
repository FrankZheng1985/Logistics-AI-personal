"""
扫码登录服务
支持抖音、B站、微信视频号的二维码扫码登录
方案：用户在官方页面扫码后，系统自动获取Cookie
"""
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
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
    """二维码扫码登录服务 - 跳转官方页面方案"""
    
    # 平台配置 - 使用能正常显示登录二维码的页面
    PLATFORMS = {
        "douyin": {
            "name": "抖音",
            # 使用抖音创作者平台，会自动弹出登录二维码
            "login_url": "https://creator.douyin.com/",
            "home_url": "https://www.douyin.com/",
            "cookie_domain": ".douyin.com",
            "login_check_url": "https://www.douyin.com/user/self",
            "login_indicators": ["passport_csrf_token", "sessionid", "ttwid"]
        },
        "bilibili": {
            "name": "B站",
            # B站主站，点击右上角登录
            "login_url": "https://www.bilibili.com/",
            "home_url": "https://www.bilibili.com/",
            "cookie_domain": ".bilibili.com",
            "login_check_url": "https://api.bilibili.com/x/web-interface/nav",
            "login_indicators": ["SESSDATA", "bili_jct", "DedeUserID"]
        },
        "weixin_video": {
            "name": "微信视频号",
            # 微信视频号创作者平台
            "login_url": "https://channels.weixin.qq.com/platform/login",
            "home_url": "https://channels.weixin.qq.com/platform",
            "cookie_domain": ".qq.com",
            "login_check_url": "https://channels.weixin.qq.com/platform",
            "login_indicators": ["uin", "skey"]
        }
    }
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.active_sessions: Dict[str, Dict] = {}  # session_id -> {context, page, platform}
    
    async def init_browser(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")
        
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            logger.info("[扫码登录] Playwright 浏览器已启动")
        return self.browser
    
    async def close_browser(self):
        """关闭浏览器"""
        for session_id in list(self.active_sessions.keys()):
            await self.cancel_login(session_id)
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("[扫码登录] 浏览器已关闭")
    
    def get_login_url(self, platform: str) -> Dict[str, Any]:
        """
        获取平台登录URL（前端直接跳转使用）
        """
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.PLATFORMS[platform]
        session_id = str(uuid4())
        
        # 记录会话（用于后续验证）
        self.active_sessions[session_id] = {
            "platform": platform,
            "created_at": datetime.utcnow(),
            "status": "pending"
        }
        
        return {
            "session_id": session_id,
            "platform": platform,
            "platform_name": config["name"],
            "login_url": config["login_url"],
            "status": "redirect",
            "message": f"请在新窗口中完成 {config['name']} 登录，登录成功后点击'我已完成登录'"
        }
    
    async def verify_and_save_cookies(self, platform: str, cookies_str: str) -> Dict[str, Any]:
        """
        验证并保存用户提供的Cookie
        cookies_str: 用户从浏览器复制的Cookie字符串
        """
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.PLATFORMS[platform]
        
        try:
            # 解析Cookie字符串
            cookies = self._parse_cookie_string(cookies_str, config["cookie_domain"])
            
            if not cookies:
                return {
                    "status": "error",
                    "message": "Cookie格式无效，请重新复制"
                }
            
            # 检查是否包含必要的登录标识Cookie
            cookie_names = [c.get("name", "") for c in cookies]
            has_login_cookie = any(
                indicator in cookie_names 
                for indicator in config["login_indicators"]
            )
            
            if not has_login_cookie:
                return {
                    "status": "error", 
                    "message": f"未检测到登录Cookie，请确保已在 {config['name']} 登录成功"
                }
            
            # 保存Cookie到数据库
            await self._save_cookies(platform, cookies)
            
            return {
                "status": "success",
                "platform": platform,
                "message": f"{config['name']} 登录成功！已保存 {len(cookies)} 个Cookie"
            }
            
        except Exception as e:
            logger.error(f"[扫码登录] 验证Cookie失败: {e}")
            return {
                "status": "error",
                "message": f"验证失败: {str(e)}"
            }
    
    async def fetch_cookies_from_browser(self, platform: str) -> Dict[str, Any]:
        """
        使用Playwright打开登录页面，等待用户扫码后获取Cookie
        这个方法会启动一个浏览器会话，用户需要在5分钟内完成扫码
        """
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = self.PLATFORMS[platform]
        session_id = str(uuid4())
        
        try:
            browser = await self.init_browser()
            
            # 创建浏览器上下文
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            logger.info(f"[扫码登录] 正在打开 {config['name']} 登录页...")
            await page.goto(config["login_url"], wait_until="networkidle", timeout=60000)
            
            # 保存会话
            self.active_sessions[session_id] = {
                "context": context,
                "page": page,
                "platform": platform,
                "created_at": datetime.utcnow(),
                "status": "waiting"
            }
            
            return {
                "session_id": session_id,
                "platform": platform,
                "platform_name": config["name"],
                "login_url": config["login_url"],
                "status": "waiting",
                "message": f"浏览器会话已创建，请在 {config['name']} 官网完成扫码登录"
            }
            
        except Exception as e:
            logger.error(f"[扫码登录] 启动浏览器失败: {e}")
            raise
    
    async def check_login_status(self, session_id: str) -> Dict[str, Any]:
        """检查扫码登录状态"""
        if session_id not in self.active_sessions:
            return {
                "session_id": session_id,
                "status": "expired",
                "message": "会话已过期"
            }
        
        session = self.active_sessions[session_id]
        
        # 如果是简单会话（只记录了platform），返回等待状态
        if "context" not in session:
            if datetime.utcnow() - session["created_at"] > timedelta(minutes=10):
                del self.active_sessions[session_id]
                return {"status": "expired", "message": "会话已过期"}
            return {"status": "waiting", "message": "等待用户完成登录..."}
        
        platform = session["platform"]
        config = self.PLATFORMS[platform]
        context = session["context"]
        page = session["page"]
        
        try:
            # 获取当前所有Cookie
            cookies = await context.cookies()
            cookie_names = [c.get("name", "") for c in cookies]
            
            # 检查是否有登录Cookie
            has_login = any(
                indicator in cookie_names 
                for indicator in config["login_indicators"]
            )
            
            if has_login:
                # 登录成功！保存Cookie
                await self._save_cookies(platform, cookies)
                await self.cancel_login(session_id)
                
                return {
                    "session_id": session_id,
                    "status": "success",
                    "platform": platform,
                    "message": f"{config['name']} 登录成功！"
                }
            
            # 检查超时
            if datetime.utcnow() - session["created_at"] > timedelta(minutes=5):
                await self.cancel_login(session_id)
                return {
                    "session_id": session_id,
                    "status": "timeout",
                    "message": "登录超时，请重试"
                }
            
            return {
                "session_id": session_id,
                "status": "waiting",
                "message": "等待扫码登录..."
            }
            
        except Exception as e:
            logger.error(f"[扫码登录] 检查状态失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _parse_cookie_string(self, cookie_str: str, domain: str) -> List[Dict]:
        """解析Cookie字符串为Cookie列表"""
        cookies = []
        
        # 支持多种格式
        # 格式1: name=value; name2=value2
        # 格式2: 从浏览器开发者工具复制的表格格式
        
        lines = cookie_str.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试解析表格格式（从开发者工具复制）
            if '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    value = parts[1].strip()
                    if name and value:
                        cookies.append({
                            "name": name,
                            "value": value,
                            "domain": domain,
                            "path": "/"
                        })
            # 尝试解析 name=value 格式
            elif '=' in line:
                for pair in line.split(';'):
                    pair = pair.strip()
                    if '=' in pair:
                        name, value = pair.split('=', 1)
                        name = name.strip()
                        value = value.strip()
                        if name and value and not name.lower() in ['path', 'domain', 'expires', 'max-age', 'secure', 'httponly', 'samesite']:
                            cookies.append({
                                "name": name,
                                "value": value,
                                "domain": domain,
                                "path": "/"
                            })
        
        return cookies
    
    async def _save_cookies(self, platform: str, cookies: List[Dict]) -> bool:
        """保存Cookie到数据库"""
        try:
            config = self.PLATFORMS[platform]
            domain = config["cookie_domain"]
            
            # 过滤相关域名的Cookie
            relevant_cookies = [
                c for c in cookies 
                if domain in c.get("domain", "") or c.get("domain", "").endswith(domain.lstrip("."))
            ]
            
            if not relevant_cookies:
                relevant_cookies = cookies  # 如果没有匹配的，保存所有
            
            async with AsyncSessionLocal() as db:
                expire_at = datetime.utcnow() + timedelta(days=30)
                
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
            if "context" in session:
                await session["context"].close()
            del self.active_sessions[session_id]
            logger.info(f"[扫码登录] 会话已取消")
            return True
        except Exception as e:
            logger.error(f"[扫码登录] 取消会话失败: {e}")
            return False


# 全局实例
qrcode_login_service = QRCodeLoginService()
