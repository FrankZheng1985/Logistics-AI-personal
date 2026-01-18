"""
市场情报定时任务
包括：市场情报采集、老板日报/周报推送
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.services.notification import notification_service
from app.core.config import settings


async def collect_market_intelligence():
    """
    采集市场情报
    每日6:00执行，采集欧洲物流行业新闻、运价、政策变化
    """
    logger.info("📊 开始执行: 市场情报采集")
    
    try:
        # 导入必要模块
        import httpx
        
        collected_intel = []
        
        # 1. 使用Serper API搜索欧洲物流新闻
        if settings.SERPER_API_KEY:
            search_queries = [
                "欧洲物流 最新消息 site:logistics.com OR site:163.com OR site:sina.com.cn",
                "欧盟海关政策 变化",
                "欧洲 卡车运价 行情",
                "德国 法国 清关 政策",
                "跨境电商 欧洲 物流"
            ]
            
            async with httpx.AsyncClient() as client:
                for query in search_queries:
                    try:
                        response = await client.post(
                            "https://google.serper.dev/search",
                            headers={"X-API-KEY": settings.SERPER_API_KEY},
                            json={
                                "q": query,
                                "gl": "cn",
                                "hl": "zh-cn",
                                "num": 5
                            },
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            for item in data.get("organic", [])[:3]:
                                intel = {
                                    "title": item.get("title", ""),
                                    "snippet": item.get("snippet", ""),
                                    "url": item.get("link", ""),
                                    "source": "google_search",
                                    "query": query,
                                    "collected_at": datetime.now().isoformat()
                                }
                                collected_intel.append(intel)
                    except Exception as e:
                        logger.warning(f"搜索失败 [{query}]: {e}")
        
        # 2. 保存到数据库
        if collected_intel:
            async with async_session_maker() as db:
                for intel in collected_intel:
                    await db.execute(
                        text("""
                            INSERT INTO market_intel 
                            (title, content, source, url, intel_type, created_at)
                            VALUES (:title, :content, :source, :url, 'news', NOW())
                            ON CONFLICT (url) DO NOTHING
                        """),
                        {
                            "title": intel["title"],
                            "content": intel["snippet"],
                            "source": intel["source"],
                            "url": intel["url"]
                        }
                    )
                await db.commit()
            
            logger.info(f"📊 采集到 {len(collected_intel)} 条市场情报")
        else:
            logger.info("📊 未采集到新的市场情报")
        
        return {"collected": len(collected_intel), "intel": collected_intel}
        
    except Exception as e:
        logger.error(f"市场情报采集失败: {e}")
        return {"error": str(e)}


async def send_boss_daily_report():
    """
    发送老板日报
    每日8:00推送欧洲物流早报
    """
    logger.info("📊 开始执行: 老板日报推送")
    
    try:
        async with async_session_maker() as db:
            # 1. 获取今日采集的情报
            result = await db.execute(
                text("""
                    SELECT title, content, url, intel_type
                    FROM market_intel
                    WHERE DATE(created_at) = CURRENT_DATE
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
            )
            news_items = result.fetchall()
            
            # 2. 获取昨日业务数据
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE - 1) as yesterday_leads,
                        COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE - 1 AND status = 'converted') as yesterday_converted
                    FROM leads
                """)
            )
            leads_stats = result.fetchone()
            
            # 3. 获取高意向客户
            result = await db.execute(
                text("""
                    SELECT name, company, intent_level, intent_score
                    FROM customers
                    WHERE intent_level IN ('S', 'A')
                    AND updated_at > NOW() - INTERVAL '24 hours'
                    ORDER BY intent_score DESC
                    LIMIT 5
                """)
            )
            high_intent_customers = result.fetchall()
        
        # 构建日报内容
        today = datetime.now().strftime("%Y年%m月%d日")
        
        report = f"""📊 【欧洲物流早报】{today}

━━━━━━━━━━━━━━━━━━━━

📈 昨日业务数据：
• 新增线索：{leads_stats[0] if leads_stats else 0} 条
• 成功转化：{leads_stats[1] if leads_stats else 0} 条

"""
        
        # 高意向客户
        if high_intent_customers:
            report += "⭐ 高意向客户动态：\n"
            for c in high_intent_customers:
                report += f"• {c[0]}({c[1] or '未知公司'}) - {c[2]}级 {c[3]}分\n"
            report += "\n"
        
        # 市场新闻
        if news_items:
            report += "📰 欧洲市场动态：\n"
            for item in news_items[:5]:
                report += f"• {item[0][:40]}...\n"
            report += "\n"
        
        report += """💡 AI建议：
• 关注欧盟最新清关政策变化
• 建议在客户工作时间主动联系高意向客户

━━━━━━━━━━━━━━━━━━━━
由小析自动生成 | 物流获客AI"""
        
        # 发送通知
        await notification_service.send_to_boss(
            title=f"📊 欧洲物流早报 {today}",
            content=report
        )
        
        logger.info("📊 老板日报推送完成")
        return {"status": "success", "report_length": len(report)}
        
    except Exception as e:
        logger.error(f"老板日报推送失败: {e}")
        return {"error": str(e)}


async def send_boss_weekly_report():
    """
    发送老板周报
    每周一8:00推送周度市场分析报告
    """
    logger.info("📊 开始执行: 老板周报推送")
    
    try:
        async with async_session_maker() as db:
            # 1. 本周业务统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_leads,
                        COUNT(*) FILTER (WHERE status = 'converted') as converted,
                        COUNT(*) FILTER (WHERE quality_score >= 60) as high_quality
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL '7 days'
                """)
            )
            leads_stats = result.fetchone()
            
            # 2. 各渠道来源统计
            result = await db.execute(
                text("""
                    SELECT source_channel, COUNT(*) as count
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    GROUP BY source_channel
                    ORDER BY count DESC
                """)
            )
            channel_stats = result.fetchall()
            
            # 3. 客户转化漏斗
            result = await db.execute(
                text("""
                    SELECT 
                        intent_level,
                        COUNT(*) as count
                    FROM customers
                    WHERE updated_at > NOW() - INTERVAL '7 days'
                    GROUP BY intent_level
                    ORDER BY 
                        CASE intent_level 
                            WHEN 'S' THEN 1 
                            WHEN 'A' THEN 2 
                            WHEN 'B' THEN 3 
                            WHEN 'C' THEN 4 
                        END
                """)
            )
            intent_distribution = result.fetchall()
            
            # 4. AI员工工作量
            result = await db.execute(
                text("""
                    SELECT 
                        agent_type,
                        SUM(tasks_completed_total) as total_tasks
                    FROM ai_agents
                    GROUP BY agent_type
                """)
            )
            agent_stats = result.fetchall()
        
        # 构建周报
        week_start = (datetime.now() - timedelta(days=7)).strftime("%m.%d")
        week_end = datetime.now().strftime("%m.%d")
        
        report = f"""📊 【周度市场分析报告】{week_start} - {week_end}

━━━━━━━━━━━━━━━━━━━━

一、本周业务回顾
• 新增线索：{leads_stats[0] if leads_stats else 0} 条
• 成功转化：{leads_stats[1] if leads_stats else 0} 条
• 高质量线索：{leads_stats[2] if leads_stats else 0} 条
• 转化率：{round(leads_stats[1]/leads_stats[0]*100, 1) if leads_stats and leads_stats[0] > 0 else 0}%

"""
        
        # 渠道统计
        if channel_stats:
            report += "二、渠道来源分析\n"
            for ch in channel_stats:
                channel_name = {
                    'lead_hunter': '小猎(搜索)',
                    'copywriter': '小文(内容)',
                    'video_creator': '小视(视频)',
                    'wechat': '企业微信',
                    'webchat': '网站客服'
                }.get(ch[0], ch[0] or '未知')
                report += f"• {channel_name}：{ch[1]} 条\n"
            report += "\n"
        
        # 客户分布
        if intent_distribution:
            report += "三、客户意向分布\n"
            for dist in intent_distribution:
                level_desc = {
                    'S': 'S级(热线索)',
                    'A': 'A级(高意向)',
                    'B': 'B级(有需求)',
                    'C': 'C级(潜在)'
                }.get(dist[0], dist[0])
                report += f"• {level_desc}：{dist[1]} 人\n"
            report += "\n"
        
        # AI员工工作量
        if agent_stats:
            report += "四、AI员工工作量\n"
            for agent in agent_stats:
                agent_name = {
                    'lead_hunter': '小猎',
                    'analyst': '小析',
                    'coordinator': '小调',
                    'sales': '小销',
                    'follow': '小跟',
                    'copywriter': '小文',
                    'video_creator': '小视'
                }.get(agent[0], agent[0])
                report += f"• {agent_name}：{agent[1] or 0} 次任务\n"
            report += "\n"
        
        report += """五、下周建议
• 重点跟进本周新增的S/A级客户
• 关注欧洲物流政策变化
• 优化高转化渠道的内容投放

━━━━━━━━━━━━━━━━━━━━
由小析自动生成 | 物流获客AI"""
        
        # 发送通知
        await notification_service.send_to_boss(
            title=f"📊 周度市场分析报告 {week_start}-{week_end}",
            content=report
        )
        
        logger.info("📊 老板周报推送完成")
        return {"status": "success", "report_length": len(report)}
        
    except Exception as e:
        logger.error(f"老板周报推送失败: {e}")
        return {"error": str(e)}


async def collect_eu_customs_news():
    """
    采集欧洲海关新闻
    每日6:00执行，由小欧间谍负责
    
    监控内容：
    - 反倾销、进口配额、关税调整
    - 欧洲偷税、欧洲洗黑钱
    - 欧盟海关政策、第三国进口
    - 清关新规、VAT变化
    """
    logger.info("🕵️ 开始执行: 欧洲海关新闻采集（小欧间谍）")
    
    try:
        from app.agents.eu_customs_monitor import eu_customs_monitor_agent
        
        # 执行完整监控任务
        result = await eu_customs_monitor_agent.process({
            "action": "monitor",
            "max_results": 50  # 每次最多分析50条新闻
        })
        
        total_news = result.get("total_news", 0)
        important_count = result.get("important_count", 0)
        notification_sent = result.get("notification_sent", False)
        
        logger.info(f"🕵️ 欧洲海关新闻采集完成: "
                   f"共采集 {total_news} 条, 重要 {important_count} 条, "
                   f"已通知: {'是' if notification_sent else '否'}")
        
        # 更新每日统计
        async with async_session_maker() as db:
            today = datetime.now().date()
            await db.execute(
                text("""
                    INSERT INTO eu_customs_monitor_stats 
                    (stat_date, total_news, important_news, notifications_sent,
                     sources_searched, keywords_used)
                    VALUES (:date, :total, :important, :notified, :sources, :keywords)
                    ON CONFLICT (stat_date) DO UPDATE SET
                        total_news = eu_customs_monitor_stats.total_news + :total,
                        important_news = eu_customs_monitor_stats.important_news + :important,
                        notifications_sent = eu_customs_monitor_stats.notifications_sent + :notified,
                        updated_at = NOW()
                """),
                {
                    "date": today,
                    "total": total_news,
                    "important": important_count,
                    "notified": 1 if notification_sent else 0,
                    "sources": result.get("sources_searched", []),
                    "keywords": []
                }
            )
            await db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"欧洲海关新闻采集失败: {e}")
        return {"error": str(e)}


async def check_urgent_intel():
    """
    检查紧急情报
    实时监控，发现紧急情报立即推送老板
    
    紧急情报类型：
    - 欧洲港口罢工
    - 清关政策突变
    - VAT税率调整
    """
    logger.info("📊 开始执行: 紧急情报检查")
    
    try:
        import httpx
        
        urgent_keywords = [
            "欧洲港口 罢工",
            "欧盟 清关 新政策",
            "VAT 税率 调整",
            "欧洲物流 中断"
        ]
        
        urgent_intel = []
        
        if settings.SERPER_API_KEY:
            async with httpx.AsyncClient() as client:
                for keyword in urgent_keywords:
                    try:
                        response = await client.post(
                            "https://google.serper.dev/news",
                            headers={"X-API-KEY": settings.SERPER_API_KEY},
                            json={
                                "q": keyword,
                                "gl": "cn",
                                "hl": "zh-cn",
                                "num": 3
                            },
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            for item in data.get("news", []):
                                # 检查是否是24小时内的新闻
                                date_str = item.get("date", "")
                                if "小时" in date_str or "分钟" in date_str:
                                    urgent_intel.append({
                                        "title": item.get("title", ""),
                                        "snippet": item.get("snippet", ""),
                                        "url": item.get("link", ""),
                                        "keyword": keyword
                                    })
                    except Exception as e:
                        logger.warning(f"紧急情报搜索失败 [{keyword}]: {e}")
        
        # 发现紧急情报，立即通知
        if urgent_intel:
            logger.warning(f"⚠️ 发现 {len(urgent_intel)} 条紧急情报！")
            
            alert_content = "⚠️ 【紧急情报预警】\n\n"
            for intel in urgent_intel[:3]:
                alert_content += f"📌 {intel['title']}\n{intel['snippet'][:100]}...\n\n"
            
            await notification_service.send_to_boss(
                title="⚠️ 紧急情报预警",
                content=alert_content
            )
            
            # 保存到数据库
            async with async_session_maker() as db:
                for intel in urgent_intel:
                    await db.execute(
                        text("""
                            INSERT INTO market_intel 
                            (title, content, source, url, intel_type, is_urgent, created_at)
                            VALUES (:title, :content, 'google_news', :url, 'urgent', true, NOW())
                            ON CONFLICT (url) DO NOTHING
                        """),
                        {
                            "title": intel["title"],
                            "content": intel["snippet"],
                            "url": intel["url"]
                        }
                    )
                await db.commit()
        
        return {"urgent_count": len(urgent_intel), "intel": urgent_intel}
        
    except Exception as e:
        logger.error(f"紧急情报检查失败: {e}")
        return {"error": str(e)}
