"""
小红书发布服务
支持：
1. 官方API发布（需要申请权限）
2. 格式化文案 + 企业微信通知（手动发布）
"""
import httpx
import hashlib
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.core.config import settings
from app.models.database import async_session_maker


class XiaohongshuPublisher:
    """小红书发布服务"""
    
    def __init__(self):
        # 小红书开放平台配置（需要申请）
        self.app_key = getattr(settings, 'XHS_APP_KEY', None)
        self.app_secret = getattr(settings, 'XHS_APP_SECRET', None)
        self.api_base_url = "https://ark.xiaohongshu.com"
        
        # 小红书内容规范
        self.MAX_TITLE_LENGTH = 20  # 标题最长20字
        self.MAX_CONTENT_LENGTH = 1000  # 正文最长1000字
        self.MAX_IMAGES = 18  # 最多18张图
        self.MAX_TOPICS = 10  # 最多10个话题标签
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """生成API签名"""
        if not self.app_secret:
            return ""
        
        # 按key排序
        sorted_params = sorted(params.items())
        # 拼接字符串
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        sign_str += f"&app_secret={self.app_secret}"
        
        # MD5签名
        return hashlib.md5(sign_str.encode()).hexdigest().upper()
    
    def format_for_xiaohongshu(
        self,
        content: str,
        topic: str,
        add_topics: bool = True
    ) -> Dict[str, str]:
        """
        将文案格式化为小红书风格
        
        Args:
            content: 原始文案内容
            topic: 主题
            add_topics: 是否添加话题标签
        
        Returns:
            {
                "title": "小红书标题",
                "content": "格式化后的正文",
                "topics": ["话题1", "话题2"]
            }
        """
        # 清理markdown代码块标记
        content = content.replace("```", "").strip()
        
        # 提取或生成标题
        lines = content.split('\n')
        title = ""
        body_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 跳过元数据行
            if line.startswith('【') and '】' in line and len(line) < 30:
                continue
            if '最佳发布时间' in line or '预期互动' in line or '推荐配图' in line:
                continue
            # 第一行作为标题
            if not title and len(line) <= self.MAX_TITLE_LENGTH:
                title = line
            else:
                body_lines.append(line)
        
        # 如果没有合适的标题，从topic生成
        if not title:
            title = f"🚀{topic}｜外贸人必看"
        
        # 确保标题长度
        if len(title) > self.MAX_TITLE_LENGTH:
            title = title[:self.MAX_TITLE_LENGTH-3] + "..."
        
        # 组装正文
        body = '\n\n'.join(body_lines)
        
        # 确保正文长度
        if len(body) > self.MAX_CONTENT_LENGTH:
            body = body[:self.MAX_CONTENT_LENGTH-50] + "\n\n...更多干货请关注我💼"
        
        # 生成话题标签
        topics = []
        if add_topics:
            # 物流相关话题
            base_topics = [
                "跨境物流", "外贸干货", "货代", "国际物流",
                "跨境电商", "外贸人", "亚马逊FBA"
            ]
            # 根据主题添加相关话题
            if "欧洲" in topic or "德国" in topic or "法国" in topic:
                topics.extend(["欧洲物流", "欧洲FBA", "欧洲清关"])
            if "美国" in topic or "FBA" in topic:
                topics.extend(["美国物流", "美国FBA", "亚马逊卖家"])
            if "清关" in topic:
                topics.extend(["清关", "报关", "进出口"])
            
            # 添加基础话题
            topics.extend(base_topics)
            # 去重并限制数量
            topics = list(dict.fromkeys(topics))[:self.MAX_TOPICS]
        
        # 在正文末尾添加话题标签
        if topics:
            topic_tags = " ".join([f"#{t}" for t in topics])
            body = f"{body}\n\n{topic_tags}"
        
        return {
            "title": title,
            "content": body,
            "topics": topics
        }
    
    async def publish_via_api(
        self,
        title: str,
        content: str,
        image_urls: List[str] = None
    ) -> Dict[str, Any]:
        """
        通过小红书官方API发布笔记
        需要先申请开放平台权限
        """
        if not self.app_key or not self.app_secret:
            return {
                "success": False,
                "error": "未配置小红书开放平台API，请先申请权限",
                "need_manual": True
            }
        
        try:
            timestamp = str(int(time.time()))
            
            params = {
                "app_key": self.app_key,
                "timestamp": timestamp,
                "title": title,
                "content": content,
            }
            
            if image_urls:
                params["images"] = json.dumps(image_urls)
            
            params["sign"] = self._generate_signature(params)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/api/content/note/publish",
                    json=params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        return {
                            "success": True,
                            "note_id": data.get("data", {}).get("note_id"),
                            "message": "小红书笔记发布成功"
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("msg", "发布失败"),
                            "need_manual": True
                        }
                else:
                    return {
                        "success": False,
                        "error": f"API请求失败: {response.status_code}",
                        "need_manual": True
                    }
                    
        except Exception as e:
            logger.error(f"小红书API发布异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "need_manual": True
            }
    
    async def publish_via_notification(
        self,
        title: str,
        content: str,
        topic: str
    ) -> Dict[str, Any]:
        """
        通过企业微信通知发送格式化文案
        用户手动复制到小红书发布
        """
        from app.services.notification import notification_service
        
        # 格式化为小红书风格
        formatted = self.format_for_xiaohongshu(content, topic)
        
        # 构建通知消息
        message = f"""📕 小红书文案已就绪！

【标题】
{formatted['title']}

【正文】
{formatted['content']}

━━━━━━━━━━━━━━
💡 发布提示：
1. 打开小红书APP
2. 点击底部 ➕ 发布
3. 复制以上标题和正文
4. 添加3-9张配图效果更佳
5. 最佳发布时间：12:00-14:00 或 20:00-22:00
"""
        
        # 发送到企业微信
        try:
            await notification_service.send_to_boss(
                title="📕 小红书文案待发布",
                content=message
            )
            
            return {
                "success": True,
                "method": "notification",
                "message": "文案已发送到企业微信，请手动复制到小红书发布",
                "formatted_title": formatted["title"],
                "formatted_content": formatted["content"],
                "topics": formatted["topics"]
            }
        except Exception as e:
            logger.error(f"通知发送失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def publish(
        self,
        content_id: str,
        image_urls: List[str] = None
    ) -> Dict[str, Any]:
        """
        发布文案到小红书
        优先尝试API，失败则通过通知
        
        Args:
            content_id: 文案ID
            image_urls: 配图URL列表
        """
        # 获取文案内容
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT id, content, topic, status
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
        
        # 格式化文案
        formatted = self.format_for_xiaohongshu(content, topic)
        
        # 尝试API发布
        if self.app_key and self.app_secret:
            api_result = await self.publish_via_api(
                title=formatted["title"],
                content=formatted["content"],
                image_urls=image_urls
            )
            
            if api_result.get("success"):
                # 更新发布状态
                async with async_session_maker() as db:
                    await db.execute(
                        text("""
                            UPDATE content_posts
                            SET status = 'published',
                                published_at = NOW(),
                                published_channels = array_append(
                                    COALESCE(published_channels, '{}'),
                                    'xiaohongshu'
                                )
                            WHERE id = :id
                        """),
                        {"id": content_id}
                    )
                    await db.commit()
                
                return api_result
        
        # API不可用，通过通知发送
        notify_result = await self.publish_via_notification(
            title=formatted["title"],
            content=formatted["content"],
            topic=topic
        )
        
        if notify_result.get("success"):
            # 更新状态为待发布（已通知）
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE content_posts
                        SET status = 'ready_to_publish',
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": content_id}
                )
                await db.commit()
        
        return notify_result


# 创建单例
xiaohongshu_publisher = XiaohongshuPublisher()
