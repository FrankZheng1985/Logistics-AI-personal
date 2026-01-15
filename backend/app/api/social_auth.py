"""
社交媒体平台登录管理API
支持Cookie登录和扫码登录
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from app.models.database import AsyncSessionLocal
from app.services.social_collector import social_collector
from app.services.qrcode_login import qrcode_login_service
from sqlalchemy import text

router = APIRouter(prefix="/social-auth", tags=["社交媒体登录"])


class LoginRequest(BaseModel):
    platform: str  # xiaohongshu, douyin, bilibili


class SaveCookiesRequest(BaseModel):
    platform: str
    cookies: List[dict]
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class CollectRequest(BaseModel):
    platforms: Optional[List[str]] = None  # ["xiaohongshu", "bilibili", "douyin"]
    keywords: Optional[List[str]] = None


@router.get("/platforms")
async def get_all_platforms():
    """获取所有平台的登录状态"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT platform, platform_name, is_logged_in, login_username, 
                           login_avatar_url, cookies_expire_at, last_login_at,
                           last_collect_at, total_collected, today_collected, error_message
                    FROM social_platform_auth
                    ORDER BY platform
                """)
            )
            rows = result.fetchall()
            
            platforms = []
            for row in rows:
                platforms.append({
                    "platform": row[0],
                    "name": row[1],
                    "is_logged_in": row[2],
                    "username": row[3],
                    "avatar_url": row[4],
                    "expires_at": row[5].isoformat() if row[5] else None,
                    "last_login_at": row[6].isoformat() if row[6] else None,
                    "last_collect_at": row[7].isoformat() if row[7] else None,
                    "total_collected": row[8] or 0,
                    "today_collected": row[9] or 0,
                    "error_message": row[10]
                })
            
            return {"platforms": platforms}
            
    except Exception as e:
        logger.error(f"获取平台状态失败: {e}")
        # 返回默认配置
        return {
            "platforms": [
                {"platform": "xiaohongshu", "name": "小红书", "is_logged_in": False},
                {"platform": "douyin", "name": "抖音", "is_logged_in": False},
                {"platform": "bilibili", "name": "B站", "is_logged_in": False}
            ]
        }


@router.get("/platforms/{platform}")
async def get_platform_status(platform: str):
    """获取单个平台的登录状态"""
    return await social_collector.check_login_status(platform)


@router.post("/login/start")
async def start_login(request: LoginRequest):
    """开始登录会话（返回登录页面URL和说明）"""
    try:
        info = await social_collector.get_login_page_url(request.platform)
        return info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"启动登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/save")
async def save_login(request: SaveCookiesRequest):
    """保存登录Cookie（前端扫码登录后调用）"""
    try:
        success = await social_collector.save_login_state(
            platform=request.platform,
            cookies=request.cookies,
            username=request.username,
            avatar_url=request.avatar_url
        )
        
        if success:
            return {"message": "登录状态已保存", "platform": request.platform}
        else:
            raise HTTPException(status_code=500, detail="保存失败")
            
    except Exception as e:
        logger.error(f"保存登录状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout/{platform}")
async def logout(platform: str):
    """退出登录"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    UPDATE social_platform_auth 
                    SET is_logged_in = FALSE,
                        cookies_data = NULL,
                        login_username = NULL,
                        login_avatar_url = NULL,
                        updated_at = NOW()
                    WHERE platform = :platform
                """),
                {"platform": platform}
            )
            await db.commit()
        
        return {"message": f"{platform} 已退出登录"}
        
    except Exception as e:
        logger.error(f"退出登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect")
async def trigger_collect(request: CollectRequest = None):
    """触发社交媒体素材采集"""
    try:
        platforms = request.platforms if request else None
        keywords = request.keywords if request else None
        
        result = await social_collector.run_collection(
            platforms=platforms,
            keywords=keywords
        )
        
        return {
            "message": "采集完成",
            **result
        }
        
    except Exception as e:
        logger.error(f"采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords")
async def get_default_keywords():
    """获取默认搜索关键词"""
    return {
        "keywords": social_collector.SEARCH_KEYWORDS
    }


# ========== 扫码登录相关接口 ==========

class QRLoginRequest(BaseModel):
    platform: str  # douyin, bilibili, weixin_video


class SaveCookieStringRequest(BaseModel):
    platform: str
    cookies_str: str  # 用户从浏览器复制的Cookie字符串


@router.post("/qrcode/start")
async def start_qr_login(request: QRLoginRequest):
    """
    开始扫码登录会话 - 返回官方登录页面URL
    前端直接跳转到官方页面，用户扫码后点击"我已完成"
    """
    try:
        result = qrcode_login_service.get_login_url(request.platform)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取登录URL失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qrcode/verify")
async def verify_cookies(request: SaveCookieStringRequest):
    """
    验证并保存用户提供的Cookie
    用户在官方页面登录后，复制Cookie并提交
    """
    try:
        result = await qrcode_login_service.verify_and_save_cookies(
            request.platform, 
            request.cookies_str
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"验证Cookie失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qrcode/status/{session_id}")
async def check_qr_login_status(session_id: str):
    """检查扫码登录状态"""
    try:
        result = await qrcode_login_service.check_login_status(session_id)
        return result
    except Exception as e:
        logger.error(f"检查登录状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qrcode/refresh/{session_id}")
async def refresh_qrcode(session_id: str):
    """刷新二维码"""
    try:
        result = await qrcode_login_service.refresh_qrcode(session_id)
        return result
    except Exception as e:
        logger.error(f"刷新二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qrcode/cancel/{session_id}")
async def cancel_qr_login(session_id: str):
    """取消扫码登录会话"""
    try:
        success = await qrcode_login_service.cancel_login(session_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"取消登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qrcode/platforms")
async def get_qr_supported_platforms():
    """获取支持扫码登录的平台列表"""
    return {
        "platforms": [
            {
                "platform": "douyin",
                "name": "抖音",
                "description": "使用抖音App扫码登录"
            },
            {
                "platform": "bilibili", 
                "name": "B站",
                "description": "使用哔哩哔哩App扫码登录"
            },
            {
                "platform": "weixin_video",
                "name": "微信视频号",
                "description": "使用微信扫码登录"
            }
        ]
    }
