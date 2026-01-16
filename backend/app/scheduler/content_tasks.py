"""
内容发布定时任务
包括：线索搜索、视频生成、内容发布
"""
import json
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.services.notification import notification_service
from app.core.config import settings


async def lead_hunt_task():
    """
    线索搜索任务 - 24小时智能版
    每小时执行，小猎自动搜索互联网潜在客户
    使用智能关键词轮换和效果追踪
    """
    logger.info("🎯 [小猎] 开始执行: 24小时智能线索搜索")
    
    try:
        from app.agents.lead_hunter import lead_hunter_agent
        
        # 使用智能狩猎模式
        result = await lead_hunter_agent.process({
            "action": "smart_hunt",
            "max_keywords": 5,      # 每次最多使用5个关键词
            "max_results": 30       # 每次最多分析30条结果
        })
        
        total_leads = result.get("total_leads", 0)
        high_intent_leads = result.get("high_intent_leads", 0)
        new_urls = result.get("new_urls", 0)
        keywords_used = result.get("keywords_used", [])
        
        logger.info(f"🎯 [小猎] 搜索完成: 关键词 {len(keywords_used)} 个, "
                    f"新URL {new_urls} 条, 线索 {total_leads} 条, 高意向 {high_intent_leads} 条")
        
        # 发现高意向线索时通知
        if high_intent_leads > 0:
            await notification_service.send_to_boss(
                title="🎯 发现高意向线索",
                content=f"小猎刚刚发现 {high_intent_leads} 条高意向线索！\n"
                        f"本次搜索关键词: {', '.join(keywords_used[:3])}...\n"
                        f"请及时跟进！"
            )
        
        # 每天早上8点和晚上20点发送汇总
        current_hour = datetime.now().hour
        if current_hour in [8, 20]:
            stats = await lead_hunter_agent.process({"action": "get_stats"})
            today_stats = stats.get("today", {})
            
            if today_stats.get("leads", 0) > 0:
                await notification_service.send_to_boss(
                    title="📊 小猎搜索日报",
                    content=f"今日搜索统计:\n"
                            f"• 搜索次数: {today_stats.get('searches', 0)}\n"
                            f"• 新URL: {today_stats.get('unique_urls', 0)}\n"
                            f"• 发现线索: {today_stats.get('leads', 0)}\n"
                            f"• 高意向: {today_stats.get('high_intent', 0)}"
                )
        
        return {
            "total_leads": total_leads,
            "high_intent_leads": high_intent_leads,
            "new_urls": new_urls,
            "keywords_count": len(keywords_used)
        }
        
    except Exception as e:
        logger.error(f"[小猎] 线索搜索任务失败: {e}")
        return {"error": str(e)}


async def lead_hunt_intensive_task():
    """
    加强线索搜索任务
    在高峰时段（9-11点、14-17点、19-21点）执行更密集的搜索
    """
    logger.info("🔥 [小猎] 开始执行: 加强线索搜索")
    
    try:
        from app.agents.lead_hunter import lead_hunter_agent
        
        # 加强模式：使用更多关键词和分析更多结果
        result = await lead_hunter_agent.process({
            "action": "smart_hunt",
            "max_keywords": 8,      # 使用更多关键词
            "max_results": 50       # 分析更多结果
        })
        
        total_leads = result.get("total_leads", 0)
        high_intent_leads = result.get("high_intent_leads", 0)
        
        logger.info(f"🔥 [小猎] 加强搜索完成: 线索 {total_leads} 条, 高意向 {high_intent_leads} 条")
        
        # 高意向线索立即通知
        if high_intent_leads >= 2:
            await notification_service.send_to_boss(
                title="🔥 发现多条高意向线索！",
                content=f"小猎在加强搜索中发现 {high_intent_leads} 条高意向线索，建议立即跟进！"
            )
        
        return {
            "total_leads": total_leads,
            "high_intent_leads": high_intent_leads,
            "mode": "intensive"
        }
        
    except Exception as e:
        logger.error(f"[小猎] 加强搜索任务失败: {e}")
        return {"error": str(e)}


async def lead_hunt_night_task():
    """
    夜间线索搜索任务
    在凌晨时段（0-6点）执行轻量级搜索
    """
    logger.info("🌙 [小猎] 开始执行: 夜间轻量搜索")
    
    try:
        from app.agents.lead_hunter import lead_hunter_agent
        
        # 夜间模式：减少搜索量，节省API调用
        result = await lead_hunter_agent.process({
            "action": "smart_hunt",
            "max_keywords": 3,      # 减少关键词
            "max_results": 15       # 减少分析量
        })
        
        total_leads = result.get("total_leads", 0)
        
        logger.info(f"🌙 [小猎] 夜间搜索完成: 线索 {total_leads} 条")
        
        return {
            "total_leads": total_leads,
            "mode": "night"
        }
        
    except Exception as e:
        logger.error(f"[小猎] 夜间搜索任务失败: {e}")
        return {"error": str(e)}


async def auto_video_generation():
    """
    自动视频生成任务
    每日10:00执行，小视自动生成营销视频
    """
    logger.info("🎬 开始执行: 自动视频生成")
    
    try:
        from app.agents.copywriter import copywriter_agent
        from app.agents.video_creator import video_creator_agent
        
        # 检查API是否配置
        if not settings.KELING_ACCESS_KEY or not settings.KELING_SECRET_KEY:
            logger.warning("🎬 可灵AI API未配置，跳过视频生成")
            return {"status": "skipped", "reason": "API未配置"}
        
        # 检查今天是否已生成视频
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM videos
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
            )
            today_videos = result.scalar() or 0
            
            if today_videos >= 3:
                logger.info("🎬 今日已生成足够视频，跳过")
                return {"status": "skipped", "reason": "今日已生成足够视频"}
        
        # 随机选择视频主题
        video_topics = [
            {
                "title": "欧洲清关到门服务",
                "description": "专业欧洲清关服务，码头清关到门一站式解决方案",
                "video_type": "service"
            },
            {
                "title": "德国/法国/英国快速派送",
                "description": "欧洲境内卡车运输，最后一公里派送到门",
                "video_type": "route"
            },
            {
                "title": "跨境电商欧洲物流方案",
                "description": "为电商卖家提供专业的欧洲FBA物流服务",
                "video_type": "solution"
            },
            {
                "title": "欧洲物流时效保证",
                "description": "准时、安全、高效的欧洲物流服务",
                "video_type": "feature"
            }
        ]
        
        import random
        topic = random.choice(video_topics)
        
        # 1. 小文撰写脚本
        logger.info(f"🎬 小文撰写脚本: {topic['title']}")
        script_result = await copywriter_agent.process({
            "task_type": "script",
            "title": topic["title"],
            "description": topic["description"],
            "video_type": topic["video_type"],
            "duration": 15
        })
        
        script = script_result.get("script", "")
        keywords = script_result.get("keywords", [])
        
        # 2. 小视生成视频
        logger.info(f"🎬 小视生成视频: {topic['title']}")
        video_result = await video_creator_agent.process({
            "title": topic["title"],
            "script": script,
            "keywords": keywords
        })
        
        # 3. 保存视频记录
        async with async_session_maker() as db:
            # 获取视频任务UUID（如果有的话）
            task_id = video_result.get("task_id")
            task_uuid = None
            if task_id:
                # 检查task_id是否是有效的UUID格式
                import uuid as uuid_module
                try:
                    task_uuid = uuid_module.UUID(task_id)
                except (ValueError, TypeError):
                    task_uuid = None
            
            await db.execute(
                text("""
                    INSERT INTO videos 
                    (title, script, video_url, status, created_at)
                    VALUES (:title, :script, :video_url, :status, NOW())
                """),
                {
                    "title": topic["title"],
                    "script": script,
                    "video_url": video_result.get("video_url", ""),
                    "status": video_result.get("status", "pending")
                }
            )
            
            # 更新小视和小文的任务统计
            await db.execute(
                text("""
                    UPDATE ai_agents
                    SET tasks_completed_today = tasks_completed_today + 1,
                        tasks_completed_total = tasks_completed_total + 1,
                        last_active_at = NOW(),
                        updated_at = NOW()
                    WHERE agent_type IN ('video_creator', 'copywriter')
                """)
            )
            await db.commit()
        
        logger.info(f"🎬 视频生成完成: {topic['title']}, 状态: {video_result.get('status')}")
        
        return {
            "title": topic["title"],
            "status": video_result.get("status"),
            "task_id": video_result.get("task_id")
        }
        
    except Exception as e:
        logger.error(f"自动视频生成失败: {e}")
        return {"error": str(e)}


async def auto_content_publish():
    """
    自动内容发布任务
    每周一/三/五执行，小文发布营销文案
    """
    logger.info("📝 开始执行: 自动内容发布")
    
    try:
        from app.agents.copywriter import copywriter_agent
        
        # 生成朋友圈文案
        topics = [
            {
                "topic": "欧洲清关到门服务",
                "purpose": "展示专业能力",
                "target_audience": "有欧洲发货需求的外贸商家"
            },
            {
                "topic": "物流时效保证",
                "purpose": "建立信任感",
                "target_audience": "追求时效的跨境电商卖家"
            },
            {
                "topic": "客户成功案例",
                "purpose": "社会证明",
                "target_audience": "正在比较货代的潜在客户"
            }
        ]
        
        import random
        topic = random.choice(topics)
        
        # 生成文案
        result = await copywriter_agent.process({
            "task_type": "moments",
            **topic
        })
        
        copy = result.get("copy", "")
        
        # 保存文案记录（实际发布需要对接各平台API）
        async with async_session_maker() as db:
            await db.execute(
                text("""
                    INSERT INTO content_posts 
                    (content, topic, platform, status, created_by, created_at)
                    VALUES (:content, :topic, 'wechat_moments', 'draft', 'copywriter', NOW())
                """),
                {
                    "content": copy,
                    "topic": topic["topic"]
                }
            )
            
            # 更新小文任务统计
            await db.execute(
                text("""
                    UPDATE ai_agents
                    SET tasks_completed_today = tasks_completed_today + 1,
                        tasks_completed_total = tasks_completed_total + 1,
                        last_active_at = NOW(),
                        updated_at = NOW()
                    WHERE agent_type = 'copywriter'
                """)
            )
            await db.commit()
        
        logger.info(f"📝 文案生成完成: {topic['topic']}")
        
        # 通知老板审核
        await notification_service.send_to_boss(
            title="📝 新文案待发布",
            content=f"小文为您撰写了新的朋友圈文案，主题：{topic['topic']}\n\n{copy[:200]}..."
        )
        
        return {
            "topic": topic["topic"],
            "copy_length": len(copy)
        }
        
    except Exception as e:
        logger.error(f"自动内容发布失败: {e}")
        return {"error": str(e)}


async def knowledge_base_update():
    """
    知识库更新任务
    每日23:00执行，小析2整理当日有价值信息入库
    """
    logger.info("📚 开始执行: 知识库更新")
    
    try:
        async with async_session_maker() as db:
            # 1. 从今日微信群消息中提取有价值信息
            result = await db.execute(
                text("""
                    SELECT id, content, analysis_result
                    FROM wechat_messages
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND is_valuable = true
                    AND knowledge_extracted = false
                """)
            )
            valuable_messages = result.fetchall()
            
            extracted_count = 0
            
            for msg in valuable_messages:
                msg_id = msg[0]
                content = msg[1]
                analysis = msg[2] if msg[2] else {}
                
                # 根据分析结果分类存入知识库
                if isinstance(analysis, str):
                    try:
                        analysis = json.loads(analysis)
                    except:
                        analysis = {}
                
                knowledge_type = analysis.get("category", "general")
                
                await db.execute(
                    text("""
                        INSERT INTO knowledge_base 
                        (content, knowledge_type, source, source_id, created_at)
                        VALUES (:content, :type, 'wechat_group', :source_id, NOW())
                    """),
                    {
                        "content": content,
                        "type": knowledge_type,
                        "source_id": str(msg_id)
                    }
                )
                
                # 标记已提取
                await db.execute(
                    text("""
                        UPDATE wechat_messages
                        SET knowledge_extracted = true
                        WHERE id = :id
                    """),
                    {"id": msg_id}
                )
                
                extracted_count += 1
            
            await db.commit()
            
            # 2. 从市场情报中提取知识
            result = await db.execute(
                text("""
                    SELECT id, title, content
                    FROM market_intel
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND knowledge_extracted = false
                """)
            )
            intel_items = result.fetchall()
            
            for intel in intel_items:
                await db.execute(
                    text("""
                        INSERT INTO knowledge_base 
                        (content, knowledge_type, source, source_id, created_at)
                        VALUES (:content, 'market_intel', 'market_intel', :source_id, NOW())
                    """),
                    {
                        "content": f"{intel[1]}: {intel[2]}",
                        "source_id": str(intel[0])
                    }
                )
                
                await db.execute(
                    text("""
                        UPDATE market_intel
                        SET knowledge_extracted = true
                        WHERE id = :id
                    """),
                    {"id": intel[0]}
                )
                
                extracted_count += 1
            
            await db.commit()
        
        logger.info(f"📚 知识库更新完成: 提取 {extracted_count} 条知识")
        
        return {"extracted_count": extracted_count}
        
    except Exception as e:
        logger.error(f"知识库更新失败: {e}")
        return {"error": str(e)}
