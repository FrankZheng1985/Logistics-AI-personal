"""
内容发布服务
支持发布到：企业微信应用消息、企业微信客户朋友圈
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.core.config import settings
from app.models.database import async_session_maker


class ContentPublisher:
    """内容发布服务"""
    
    def __init__(self):
        self.corp_id = settings.WECHAT_CORP_ID
        self.agent_id = settings.WECHAT_AGENT_ID
        self.secret = settings.WECHAT_SECRET
        self._access_token = None
        self._token_expires_at = 0
    
    async def get_access_token(self) -> Optional[str]:
        """获取企业微信access_token"""
        import time
        
        # 检查token是否有效
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        
        if not self.corp_id or not self.secret:
            logger.warning("企业微信未配置，无法获取access_token")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                    params={
                        "corpid": self.corp_id,
                        "corpsecret": self.secret
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        self._access_token = data.get("access_token")
                        self._token_expires_at = time.time() + data.get("expires_in", 7200) - 300
                        return self._access_token
                    else:
                        logger.error(f"获取access_token失败: {data}")
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
        
        return None
    
    async def publish_to_wechat_app(
        self,
        content: str,
        title: Optional[str] = None,
        user_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发布到企业微信应用消息
        可以发送给指定用户或所有人
        
        Args:
            content: 文案内容
            title: 标题（可选）
            user_ids: 接收用户ID列表，为空则发送给所有人
        """
        access_token = await self.get_access_token()
        if not access_token:
            return {"success": False, "error": "无法获取access_token"}
        
        # 构建消息内容
        if title:
            message_content = f"📝 {title}\n\n{content}"
        else:
            message_content = content
        
        # 构建请求体
        payload = {
            "touser": "|".join(user_ids) if user_ids else "@all",
            "msgtype": "text",
            "agentid": int(self.agent_id),
            "text": {
                "content": message_content
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}",
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        logger.info(f"企业微信消息发送成功")
                        return {"success": True, "message": "发送成功"}
                    else:
                        logger.error(f"企业微信消息发送失败: {data}")
                        return {"success": False, "error": data.get("errmsg")}
        except Exception as e:
            logger.error(f"企业微信消息发送异常: {e}")
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "未知错误"}
    
    async def publish_to_wechat_moments(
        self,
        content: str,
        media_ids: Optional[List[str]] = None,
        visible_range: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        发布到企业微信客户朋友圈
        需要企业微信开通「客户朋友圈」功能
        
        Args:
            content: 文案内容
            media_ids: 图片/视频media_id列表（可选）
            visible_range: 可见范围（可选）
        """
        access_token = await self.get_access_token()
        if not access_token:
            return {"success": False, "error": "无法获取access_token"}
        
        # 构建朋友圈内容
        attachments = []
        
        # 文字内容
        text_attachment = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        attachments.append(text_attachment)
        
        # 如果有图片
        if media_ids:
            for media_id in media_ids:
                attachments.append({
                    "msgtype": "image",
                    "image": {
                        "media_id": media_id
                    }
                })
        
        payload = {
            "text": {
                "content": content
            },
            "attachments": attachments if media_ids else [],
            "visible_range": visible_range or {
                "sender_list": {
                    "user_list": ["@all"]  # 所有成员可发
                },
                "external_contact_list": {
                    "tag_list": []  # 所有客户可见
                }
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/add_moment_task?access_token={access_token}",
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        job_id = data.get("jobid")
                        logger.info(f"朋友圈发布任务创建成功: {job_id}")
                        return {
                            "success": True, 
                            "job_id": job_id,
                            "message": "朋友圈发布任务已创建"
                        }
                    else:
                        error_msg = data.get("errmsg", "")
                        # 常见错误处理
                        if "no permission" in error_msg.lower() or data.get("errcode") == 60020:
                            return {
                                "success": False, 
                                "error": "未开通客户朋友圈功能，请在企业微信管理后台开通"
                            }
                        logger.error(f"朋友圈发布失败: {data}")
                        return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"朋友圈发布异常: {e}")
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "未知错误"}
    
    async def publish_content(
        self,
        content_id: str,
        channels: List[str] = None
    ) -> Dict[str, Any]:
        """
        发布指定的文案内容
        
        Args:
            content_id: 文案ID
            channels: 发布渠道列表 ["wechat_app", "wechat_moments"]
        """
        if channels is None:
            channels = ["wechat_app"]  # 默认发送到企业微信应用
        
        # 获取文案内容
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT id, content, topic, platform, status
                    FROM content_posts
                    WHERE id = :id
                """),
                {"id": content_id}
            )
            row = result.fetchone()
            
            if not row:
                return {"success": False, "error": "文案不存在"}
            
            content = row[1]
            topic = row[2]
            status = row[4]
            
            if status == "published":
                return {"success": False, "error": "文案已发布"}
        
        results = {}
        all_success = True
        
        # 发布到各渠道
        for channel in channels:
            if channel == "wechat_app":
                result = await self.publish_to_wechat_app(
                    content=content,
                    title=f"【{topic}】营销文案"
                )
                results["wechat_app"] = result
                if not result.get("success"):
                    all_success = False
                    
            elif channel == "wechat_moments":
                result = await self.publish_to_wechat_moments(content=content)
                results["wechat_moments"] = result
                if not result.get("success"):
                    all_success = False
        
        # 更新发布状态
        if all_success:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE content_posts
                        SET status = 'published',
                            published_at = NOW(),
                            published_channels = :channels
                        WHERE id = :id
                    """),
                    {"id": content_id, "channels": channels}
                )
                await db.commit()
        
        return {
            "success": all_success,
            "results": results,
            "content_id": content_id
        }
    
    async def get_pending_contents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取待发布的文案列表"""
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT id, content, topic, platform, status, created_at
                    FROM content_posts
                    WHERE status = 'draft'
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            rows = result.fetchall()
            
            return [
                {
                    "id": str(row[0]),
                    "content": row[1],
                    "topic": row[2],
                    "platform": row[3],
                    "status": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in rows
            ]
    
    async def auto_publish_approved(self) -> Dict[str, Any]:
        """
        自动发布已审核通过的文案
        """
        async with async_session_maker() as db:
            # 获取已审核待发布的文案
            result = await db.execute(
                text("""
                    SELECT id, content, topic
                    FROM content_posts
                    WHERE status = 'approved'
                    ORDER BY created_at ASC
                    LIMIT 5
                """)
            )
            rows = result.fetchall()
            
            if not rows:
                return {"message": "没有待发布的文案", "published": 0}
            
            published_count = 0
            for row in rows:
                content_id = str(row[0])
                result = await self.publish_content(
                    content_id=content_id,
                    channels=["wechat_app"]
                )
                if result.get("success"):
                    published_count += 1
            
            return {
                "message": f"已发布 {published_count} 篇文案",
                "published": published_count
            }


# 创建单例
content_publisher = ContentPublisher()
