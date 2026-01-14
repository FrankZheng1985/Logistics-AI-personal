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
    线索搜索任务
    每2小时执行，小猎自动搜索互联网潜在客户
    """
    logger.info("🎯 开始执行: 线索搜索任务")
    
    try:
        from app.agents.lead_hunter import lead_hunter_agent
        
        # 欧洲物流相关搜索关键词
        search_queries = [
            "找欧洲货代 site:weibo.com OR site:zhihu.com",
            "欧洲清关 报价",
            "德国派送 物流公司",
            "法国到门 价格",
            "欧洲FBA物流 推荐"
        ]
        
        total_leads = 0
        high_intent_leads = 0
        
        for query in search_queries:
            try:
                # 使用Serper API搜索
                results = await lead_hunter_agent.search_with_serper(query)
                
                for result in results:
                    # 分析是否是有效线索
                    analysis = await lead_hunter_agent._analyze_content({
                        "content": f"{result.get('title', '')} {result.get('content', '')}",
                        "source": "serper",
                        "url": result.get("url", "")
                    })
                    
                    if analysis.get("is_lead"):
                        total_leads += 1
                        
                        # 保存线索到数据库
                        async with async_session_maker() as db:
                            await db.execute(
                                text("""
                                    INSERT INTO leads 
                                    (source, source_url, content, quality_score, 
                                     intent_level, status, source_channel, created_at)
                                    VALUES ('serper', :url, :content, :score, 
                                            :level, 'new', 'lead_hunter', NOW())
                                    ON CONFLICT (source_url) DO NOTHING
                                """),
                                {
                                    "url": result.get("url", ""),
                                    "content": json.dumps({
                                        "title": result.get("title", ""),
                                        "snippet": result.get("content", ""),
                                        "analysis": analysis
                                    }, ensure_ascii=False),
                                    "score": analysis.get("confidence", 50),
                                    "level": {
                                        "high": "A",
                                        "medium": "B",
                                        "low": "C"
                                    }.get(analysis.get("intent_level", "low"), "C")
                                }
                            )
                            await db.commit()
                        
                        if analysis.get("intent_level") == "high":
                            high_intent_leads += 1
                            
            except Exception as e:
                logger.warning(f"搜索失败 [{query}]: {e}")
        
        # 更新小猎的任务统计
        async with async_session_maker() as db:
            await db.execute(
                text("""
                    UPDATE ai_agents
                    SET tasks_completed_today = tasks_completed_today + 1,
                        tasks_completed_total = tasks_completed_total + 1,
                        last_active_at = NOW(),
                        updated_at = NOW()
                    WHERE agent_type = 'lead_hunter'
                """)
            )
            await db.commit()
        
        logger.info(f"🎯 线索搜索完成: 发现 {total_leads} 条线索，高意向 {high_intent_leads} 条")
        
        # 发现高意向线索通知
        if high_intent_leads > 0:
            await notification_service.send_to_boss(
                title="🎯 发现高意向线索",
                content=f"小猎刚刚发现 {high_intent_leads} 条高意向线索，请及时跟进！"
            )
        
        return {
            "total_leads": total_leads,
            "high_intent_leads": high_intent_leads
        }
        
    except Exception as e:
        logger.error(f"线索搜索任务失败: {e}")
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
            await db.execute(
                text("""
                    INSERT INTO videos 
                    (title, script, video_url, task_id, status, created_by, created_at)
                    VALUES (:title, :script, :video_url, :task_id, :status, 'video_creator', NOW())
                """),
                {
                    "title": topic["title"],
                    "script": script,
                    "video_url": video_result.get("video_url", ""),
                    "task_id": video_result.get("task_id", ""),
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
