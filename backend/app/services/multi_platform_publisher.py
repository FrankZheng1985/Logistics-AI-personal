"""
多平台内容发布服务
支持：知乎、CSDN、简书、今日头条、微博、自有网站等
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


class MultiPlatformPublisher:
    """多平台内容发布服务"""
    
    # 支持的平台列表
    PLATFORMS = {
        "zhihu": {
            "name": "知乎",
            "icon": "📘",
            "type": "article",
            "max_title": 50,
            "max_content": 50000
        },
        "csdn": {
            "name": "CSDN",
            "icon": "💻",
            "type": "article",
            "max_title": 100,
            "max_content": 100000
        },
        "jianshu": {
            "name": "简书",
            "icon": "📝",
            "type": "article",
            "max_title": 50,
            "max_content": 30000
        },
        "toutiao": {
            "name": "今日头条",
            "icon": "📰",
            "type": "article",
            "max_title": 30,
            "max_content": 20000
        },
        "weibo": {
            "name": "微博",
            "icon": "🔴",
            "type": "short",
            "max_title": 0,
            "max_content": 2000
        },
        "baijiahao": {
            "name": "百家号",
            "icon": "📱",
            "type": "article",
            "max_title": 30,
            "max_content": 20000
        },
        "wordpress": {
            "name": "WordPress",
            "icon": "🌐",
            "type": "article",
            "max_title": 200,
            "max_content": 100000
        },
        "wechat_article": {
            "name": "微信公众号",
            "icon": "💚",
            "type": "article",
            "max_title": 64,
            "max_content": 20000
        }
    }
    
    def __init__(self):
        # 各平台API配置（需要在.env中配置）
        self.configs = {
            "zhihu": {
                "cookie": getattr(settings, 'ZHIHU_COOKIE', None),
            },
            "csdn": {
                "cookie": getattr(settings, 'CSDN_COOKIE', None),
            },
            "jianshu": {
                "token": getattr(settings, 'JIANSHU_TOKEN', None),
            },
            "toutiao": {
                "cookie": getattr(settings, 'TOUTIAO_COOKIE', None),
            },
            "weibo": {
                "cookie": getattr(settings, 'WEIBO_COOKIE', None),
            },
            "wordpress": {
                "url": getattr(settings, 'WORDPRESS_URL', None),
                "username": getattr(settings, 'WORDPRESS_USER', None),
                "password": getattr(settings, 'WORDPRESS_PASSWORD', None),
            }
        }
    
    def get_available_platforms(self) -> List[Dict[str, Any]]:
        """获取所有可用平台"""
        platforms = []
        for key, info in self.PLATFORMS.items():
            config = self.configs.get(key, {})
            # 检查是否已配置
            is_configured = any(v for v in config.values() if v)
            platforms.append({
                "key": key,
                "name": info["name"],
                "icon": info["icon"],
                "type": info["type"],
                "configured": is_configured,
                "max_title": info["max_title"],
                "max_content": info["max_content"]
            })
        return platforms
    
    def format_for_platform(
        self,
        content: str,
        topic: str,
        platform: str
    ) -> Dict[str, str]:
        """
        根据平台格式化内容
        """
        platform_info = self.PLATFORMS.get(platform, {})
        max_title = platform_info.get("max_title", 50)
        max_content = platform_info.get("max_content", 10000)
        platform_type = platform_info.get("type", "article")
        
        # 清理markdown标记
        content = content.replace("```", "").strip()
        
        # 提取标题和正文
        lines = content.split('\n')
        title = ""
        body_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 跳过元数据
            if line.startswith('【') and '】' in line:
                if '文案正文' in line or '推荐配图' in line or '最佳发布' in line or '预期互动' in line:
                    continue
            # 第一行非空作为标题
            if not title:
                title = line
            else:
                body_lines.append(line)
        
        # 生成标题
        if not title or len(title) > max_title:
            title = f"{topic} - 物流干货分享"
        if len(title) > max_title:
            title = title[:max_title-3] + "..."
        
        # 组装正文
        body = '\n\n'.join(body_lines)
        
        # 根据平台类型调整
        if platform_type == "short":
            # 短内容平台（微博等）
            if len(body) > max_content:
                body = body[:max_content-50] + "\n\n...完整内容请关注我们💼"
        else:
            # 长文章平台
            # 添加开头引言
            intro = f"📦 {topic}\n\n"
            # 添加结尾引导
            outro = "\n\n---\n\n💡 **关于我们**\n专注欧洲物流，清关到门一站式服务。\n如有物流需求，欢迎私信咨询！"
            
            body = intro + body + outro
            
            if len(body) > max_content:
                body = body[:max_content-100] + "\n\n...(内容过长已截断)"
        
        return {
            "title": title,
            "content": body,
            "platform": platform,
            "platform_name": platform_info.get("name", platform)
        }
    
    async def publish_to_wordpress(
        self,
        title: str,
        content: str,
        categories: List[str] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        发布到WordPress网站
        使用REST API
        """
        config = self.configs.get("wordpress", {})
        base_url = config.get("url")
        username = config.get("username")
        password = config.get("password")
        
        if not all([base_url, username, password]):
            return {
                "success": False,
                "error": "WordPress未配置，请在.env中设置WORDPRESS_URL, WORDPRESS_USER, WORDPRESS_PASSWORD"
            }
        
        try:
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json"
            }
            
            # 构建文章数据
            post_data = {
                "title": title,
                "content": content,
                "status": "publish"  # 直接发布，可改为 "draft" 草稿
            }
            
            if categories:
                post_data["categories"] = categories
            if tags:
                post_data["tags"] = tags
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/wp-json/wp/v2/posts",
                    headers=headers,
                    json=post_data,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        "success": True,
                        "post_id": data.get("id"),
                        "post_url": data.get("link"),
                        "message": f"文章已发布到WordPress: {data.get('link')}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"发布失败: {response.status_code} - {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"WordPress发布异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def publish_via_notification(
        self,
        title: str,
        content: str,
        platform: str,
        topic: str
    ) -> Dict[str, Any]:
        """
        通过企业微信通知发送格式化文案
        用户手动复制到对应平台发布
        """
        from app.services.notification import notification_service
        
        platform_info = self.PLATFORMS.get(platform, {})
        platform_name = platform_info.get("name", platform)
        platform_icon = platform_info.get("icon", "📄")
        
        # 构建通知消息
        message = f"""{platform_icon} {platform_name}文案已就绪！

【标题】
{title}

【正文】
{content[:1500]}{'...(内容过长，请查看完整版)' if len(content) > 1500 else ''}

━━━━━━━━━━━━━━
💡 发布提示：
1. 登录 {platform_name}
2. 创建新文章/动态
3. 复制以上标题和正文
4. 添加配图后发布
"""
        
        try:
            await notification_service.send_to_boss(
                title=f"{platform_icon} {platform_name}文案待发布",
                content=message
            )
            
            return {
                "success": True,
                "method": "notification",
                "platform": platform,
                "platform_name": platform_name,
                "message": f"文案已发送到企业微信，请手动复制到{platform_name}发布",
                "formatted_title": title,
                "formatted_content": content
            }
        except Exception as e:
            logger.error(f"通知发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def publish(
        self,
        content_id: str,
        platforms: List[str]
    ) -> Dict[str, Any]:
        """
        发布文案到多个平台
        
        Args:
            content_id: 文案ID
            platforms: 平台列表 ["zhihu", "csdn", "wordpress"]
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
        
        results = {}
        success_count = 0
        
        for platform in platforms:
            if platform not in self.PLATFORMS:
                results[platform] = {"success": False, "error": "不支持的平台"}
                continue
            
            # 格式化内容
            formatted = self.format_for_platform(content, topic, platform)
            
            # 根据平台选择发布方式
            if platform == "wordpress":
                # WordPress使用API发布
                result = await self.publish_to_wordpress(
                    title=formatted["title"],
                    content=formatted["content"],
                    tags=["物流", "跨境电商", "外贸"]
                )
            else:
                # 其他平台通过通知
                result = await self.publish_via_notification(
                    title=formatted["title"],
                    content=formatted["content"],
                    platform=platform,
                    topic=topic
                )
            
            results[platform] = result
            if result.get("success"):
                success_count += 1
        
        # 更新发布记录
        if success_count > 0:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE content_posts
                        SET status = CASE WHEN status = 'draft' THEN 'ready_to_publish' ELSE status END,
                            published_channels = array_cat(
                                COALESCE(published_channels, '{}'),
                                :platforms
                            ),
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": content_id, "platforms": platforms}
                )
                await db.commit()
        
        return {
            "success": success_count > 0,
            "total_platforms": len(platforms),
            "success_count": success_count,
            "results": results
        }
    
    async def batch_publish(
        self,
        content_id: str,
        all_platforms: bool = False
    ) -> Dict[str, Any]:
        """
        一键发布到所有已配置的平台
        """
        if all_platforms:
            # 发布到所有平台
            platforms = list(self.PLATFORMS.keys())
        else:
            # 只发布到已配置的平台
            platforms = [
                key for key, config in self.configs.items()
                if any(v for v in config.values() if v)
            ]
            # 如果没有配置任何平台，默认发送通知
            if not platforms:
                platforms = ["zhihu", "csdn", "toutiao"]  # 默认推荐平台
        
        return await self.publish(content_id, platforms)


# 创建单例
multi_platform_publisher = MultiPlatformPublisher()
