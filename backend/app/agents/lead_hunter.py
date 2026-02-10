"""
小猎 - 线索猎手 & 话题发现者
双模式运行：
1. 线索搜索模式：搜索互联网上的潜在客户线索
2. 话题发现模式：发现热门话题，配合小文生成回答内容引流

话题发现模式支持：
- 搜索知乎/小红书等平台的热门物流相关话题
- 评估话题价值（浏览量、回答数、时效性）
- 生成回答策略建议
- 与小文配合一键生成专业回答
"""
from typing import Dict, Any, List, Optional
import json
import re
import asyncio
import httpx
import hashlib
from datetime import datetime, timedelta
from loguru import logger
from app.core.prompts.lead_hunter import SYSTEM_PROMPT as LEAD_HUNTER_SYSTEM_PROMPT

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings
from app.core.prompt_utils import sanitize_user_input, wrap_user_content


class LeadHunterAgent(BaseAgent):
    """小猎 - 线索猎手 & 话题发现者"""
    
    name = "小猎"
    agent_type = AgentType.LEAD_HUNTER
    description = "线索猎手 & 话题发现者 - 搜索线索或发现热门话题配合内容引流"
    
    # 备用搜索关键词（数据库关键词不可用时使用）- 只搜索欧洲相关
    FALLBACK_KEYWORDS = [
        "欧洲货代", "欧洲物流推荐", "欧洲物流报价",
        "欧洲清关", "欧洲派送", "欧洲到门",
        "德国物流", "法国物流", "英国物流",
        "发货到欧洲", "欧洲FBA", "欧洲双清",
        "德国FBA", "英国FBA", "欧洲卡派"
    ]
    
    # 搜索平台配置
    PLATFORMS = {
        "weibo": {"site": "site:weibo.com", "weight": 3},
        "zhihu": {"site": "site:zhihu.com", "weight": 3},
        "tieba": {"site": "site:tieba.baidu.com", "weight": 2},
        "douyin": {"site": "site:douyin.com", "weight": 2},
        "xiaohongshu": {"site": "site:xiaohongshu.com", "weight": 2},
        "google": {"site": "", "weight": 4}  # 全网搜索
    }
    
    # 线索质量判断关键词
    HIGH_INTENT_KEYWORDS = [
        "急", "马上", "尽快", "报价", "价格", "多少钱",
        "立即", "今天", "明天", "这周", "想发", "要发",
        "求推荐", "有没有", "谁知道", "哪家好",
        "urgent", "asap", "quote", "price", "how much"
    ]
    
    # 广告过滤关键词
    AD_FILTER_KEYWORDS = [
        "加盟", "招商", "代理", "免费试用", "限时优惠",
        "欢迎咨询", "专业物流", "我司", "我们公司",
        "联系电话", "点击咨询", "在线客服", "招代理",
        "诚招", "火热招商"
    ]
    
    def _build_system_prompt(self) -> str:
        return LEAD_HUNTER_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理线索搜索或话题发现任务
        
        Args:
            input_data: {
                "action": "search" | "analyze" | "hunt" | "smart_hunt" | 
                          "discover_topics" | "analyze_topic" | "get_topic_stats" |
                          "discover_products" | "get_product_stats",
                "source": "搜索来源",
                "content": "要分析的内容",
                "keywords": ["自定义关键词"],
                "max_keywords": 最大关键词数量,
                "max_results": 最大结果数量
            }
        """
        action = input_data.get("action", "smart_hunt")
        
        # 开始任务会话（实时直播）
        await self.start_task_session(action, f"线索搜索任务: {action}")
        
        try:
            # 线索搜索模式
            if action == "search":
                result = await self._search_leads(input_data)
            elif action == "analyze":
                result = await self._analyze_content(input_data)
            elif action == "hunt":
                result = await self._full_hunt(input_data)
            elif action == "smart_hunt":
                result = await self._smart_hunt(input_data)
            elif action == "get_stats":
                result = await self._get_hunt_stats()
            # 话题发现模式
            elif action == "discover_topics":
                result = await self._discover_topics(input_data)
            elif action == "analyze_topic":
                result = await self._analyze_topic_value(input_data)
            elif action == "get_topic_stats":
                result = await self._get_topic_stats()
            elif action == "generate_answer":
                result = await self._generate_answer(input_data)
            # 产品趋势发现模式（内容引流 + 市场洞察）
            elif action == "discover_products":
                result = await self._discover_product_trends(input_data)
            elif action == "get_product_stats":
                result = await self._get_product_stats()
            else:
                result = {"error": f"未知操作: {action}"}
            
            await self.end_task_session(f"完成{action}任务")
            return result
        except Exception as e:
            await self.end_task_session(error_message=str(e))
            raise
    
    async def _smart_hunt(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        智能线索狩猎 - 24小时自动运行版本
        - 自动从数据库获取待搜索关键词
        - 智能选择搜索平台
        - 自动去重和记录
        - 追踪搜索效果
        - 只搜索最近1个月内的内容（确保线索时效性）
        """
        # 开始任务会话（实时直播）
        await self.start_task_session("smart_hunt", "智能线索狩猎 - 搜索互联网潜在客户")
        
        self.log("🎯 开始智能线索狩猎任务（仅搜索最近1个月内的线索）...")
        start_time = datetime.now()
        
        # 检查API配置
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            self.log("Serper API未配置，无法进行搜索", "error")
            await self.log_error("Serper API未配置", "请在系统设置中配置API密钥")
            await self.end_task_session(error_message="API未配置")
            return {
                "error": "搜索API未配置",
                "message": "请在系统设置中配置 SERPER_API_KEY 以启用线索搜索功能",
                "hunt_time": datetime.now().isoformat(),
                "sources_searched": [],
                "leads_found": [],
                "total_leads": 0
            }
        
        results = {
            "hunt_time": datetime.now().isoformat(),
            "hunt_mode": "smart_24h",
            "sources_searched": [],
            "leads_found": [],
            "total_leads": 0,
            "high_intent_leads": 0,
            "keywords_used": [],
            "search_queries": [],
            "new_urls": 0,
            "duplicate_urls": 0,
            "stats": {}
        }
        
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 1. 获取待搜索的关键词（优先级高、效果好、冷却时间已过）
                max_keywords = input_data.get("max_keywords", 5)
                
                keyword_result = await db.execute(
                    text("""
                        SELECT id, keyword, keyword_type, platform, priority, success_rate
                        FROM lead_hunt_keywords
                        WHERE is_active = true
                        AND (next_search_after IS NULL OR next_search_after <= NOW())
                        ORDER BY 
                            priority DESC,
                            success_rate DESC,
                            last_searched_at ASC NULLS FIRST
                        LIMIT :limit
                    """),
                    {"limit": max_keywords}
                )
                keywords_data = keyword_result.fetchall()
                
                # 如果数据库没有关键词，使用备用关键词
                if not keywords_data:
                    self.log("数据库无可用关键词，使用备用关键词")
                    keywords_to_use = self.FALLBACK_KEYWORDS[:max_keywords]
                    keywords_data = [(None, kw, 'fallback', None, 5, 0) for kw in keywords_to_use]
                
                self.log(f"本次将使用 {len(keywords_data)} 个关键词搜索")
                await self.log_live_step("info", f"准备搜索 {len(keywords_data)} 个关键词", 
                    f"关键词: {', '.join([k[1] for k in keywords_data[:5]])}")
                
                all_raw_results = []
                
                # 2. 对每个关键词进行搜索
                for kw_data in keywords_data:
                    kw_id, keyword, kw_type, kw_platform, priority, success_rate = kw_data
                    results["keywords_used"].append(keyword)
                    
                    # 确定搜索平台
                    if kw_platform:
                        platforms_to_search = [(kw_platform, self.PLATFORMS.get(kw_platform, {}).get("site", ""))]
                    else:
                        # 根据当前时间智能选择平台
                        platforms_to_search = self._select_platforms_by_time()
                    
                    keyword_leads = 0
                    keyword_high_intent = 0
                    
                    for platform_name, site_filter in platforms_to_search:
                        try:
                            query = f"{keyword} {site_filter}".strip()
                            self.log(f"🔍 搜索: {query}")
                            results["search_queries"].append(query)
                            
                            # 记录搜索步骤（实时直播）
                            await self.log_search(keyword, platform_name, {"query": query})
                            
                            search_results = await self._search_with_serper(query)
                            
                            if search_results:
                                results["sources_searched"].append(platform_name)
                                
                                for item in search_results:
                                    url = item.get("url", "")
                                    if not url:
                                        continue
                                    
                                    # 检查URL是否已搜索过
                                    url_hash = hashlib.md5(url.encode()).hexdigest()
                                    
                                    existing_url = await db.execute(
                                        text("""
                                            SELECT id, is_lead FROM lead_hunt_searched_urls
                                            WHERE url_hash = :hash
                                        """),
                                        {"hash": url_hash}
                                    )
                                    existing = existing_url.fetchone()
                                    
                                    if existing:
                                        results["duplicate_urls"] += 1
                                        continue
                                    
                                    results["new_urls"] += 1
                                    
                                    item["platform"] = platform_name
                                    item["keyword"] = keyword
                                    item["keyword_id"] = kw_id
                                    item["url_hash"] = url_hash
                                    all_raw_results.append(item)
                            
                            # 控制请求频率
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            self.log(f"搜索失败 ({platform_name}, {keyword}): {e}", "error")
                    
                    # 更新关键词统计（在分析完所有结果后更新）
                
                self.log(f"📊 获取 {len(all_raw_results)} 条新URL待分析")
                await self.log_live_step("info", f"获取 {len(all_raw_results)} 条新URL", "开始AI分析筛选")
                
                # 3. 分析每个搜索结果
                max_results = input_data.get("max_results", 30)
                keyword_stats = {}  # 记录每个关键词的效果
                analyzed_count = 0
                
                for item in all_raw_results[:max_results]:
                    try:
                        content = f"{item.get('title', '')} {item.get('content', '')}"
                        url = item.get("url", "")
                        url_hash = item.get("url_hash", "")
                        keyword = item.get("keyword", "")
                        keyword_id = item.get("keyword_id")
                        platform = item.get("platform", "google")
                        
                        # 快速过滤
                        if self._quick_filter(content):
                            # 记录为非线索URL
                            await db.execute(
                                text("""
                                    INSERT INTO lead_hunt_searched_urls 
                                    (url_hash, url, source_keyword, platform, is_lead)
                                    VALUES (:hash, :url, :keyword, :platform, false)
                                    ON CONFLICT (url_hash) DO NOTHING
                                """),
                                {"hash": url_hash, "url": url, "keyword": keyword, "platform": platform}
                            )
                            continue
                        
                        # 记录正在分析的URL（实时直播）
                        analyzed_count += 1
                        await self.log_fetch(url, item.get("title", ""), {"platform": platform})
                        
                        # AI深度分析
                        await self.log_think("判断是否为潜在客户线索", content[:100])
                        analysis = await self._analyze_content({
                            "content": content,
                            "source": platform,
                            "url": url
                        })
                        
                        is_lead = analysis.get("is_lead", False)
                        intent_level = analysis.get("intent_level", "low")
                        is_high_intent = intent_level == "high"
                        
                        # 初始化关键词统计
                        if keyword not in keyword_stats:
                            keyword_stats[keyword] = {"id": keyword_id, "leads": 0, "high_intent": 0}
                        
                        if is_lead:
                            # 记录发现线索（实时直播）
                            await self.log_result(
                                f"🎯 发现潜在线索!", 
                                f"意向等级: {intent_level}, 来源: {platform}",
                                {"url": url, "intent_level": intent_level}
                            )
                            
                            # 提取联系方式
                            contact_info = analysis.get("contact_info", {})
                            extracted_contact = self._extract_contact_info(content)
                            for key, value in extracted_contact.items():
                                if value and not contact_info.get(key):
                                    contact_info[key] = value
                            
                            lead_data = {
                                "title": item.get("title", ""),
                                "content": content,
                                "url": url,
                                "source": platform,
                                "keyword": keyword,
                                "found_at": datetime.now().isoformat(),
                                "is_lead": True,
                                "confidence": analysis.get("confidence", 50),
                                "intent_level": intent_level,
                                "lead_type": analysis.get("lead_type", ""),
                                "needs": analysis.get("needs", []),
                                "contact_info": contact_info,
                                "summary": analysis.get("summary", ""),
                                "follow_up_suggestion": analysis.get("follow_up_suggestion", "")
                            }
                            
                            results["leads_found"].append(lead_data)
                            results["total_leads"] += 1
                            keyword_stats[keyword]["leads"] += 1
                            
                            if is_high_intent:
                                results["high_intent_leads"] += 1
                                keyword_stats[keyword]["high_intent"] += 1
                            
                            # 检测线索语言
                            from app.services.language_detector import language_detector
                            lead_language = language_detector.detect_customer_language(
                                name=lead_data.get("contact_name"),
                                email=lead_data.get("email"),
                                company=lead_data.get("company"),
                                message=content  # 用原始内容检测
                            )
                            
                            # 保存线索到数据库
                            lead_insert = await db.execute(
                                text("""
                                    INSERT INTO leads 
                                    (source, source_url, source_content, content, 
                                     ai_confidence, intent_level, ai_summary, ai_suggestion,
                                     needs, status, language, created_at)
                                    VALUES (:source, :url, :raw_content, :content, 
                                            :confidence, :level, :summary, :suggestion,
                                            :needs, 'new', :language, NOW())
                                    ON CONFLICT (source_url) DO NOTHING
                                    RETURNING id
                                """),
                                {
                                    "source": platform,
                                    "url": url,
                                    "raw_content": content,
                                    "content": json.dumps(lead_data, ensure_ascii=False),
                                    "confidence": analysis.get("confidence", 50) / 100.0,
                                    "level": {"high": "high", "medium": "medium", "low": "low"}.get(intent_level, "unknown"),
                                    "summary": analysis.get("summary", ""),
                                    "suggestion": analysis.get("follow_up_suggestion", ""),
                                    "needs": analysis.get("needs", []),
                                    "language": lead_language
                                }
                            )
                            lead_row = lead_insert.fetchone()
                            lead_id = lead_row[0] if lead_row else None
                            
                            # 记录已搜索URL（标记为线索）
                            await db.execute(
                                text("""
                                    INSERT INTO lead_hunt_searched_urls 
                                    (url_hash, url, source_keyword, platform, is_lead, lead_id)
                                    VALUES (:hash, :url, :keyword, :platform, true, :lead_id)
                                    ON CONFLICT (url_hash) DO NOTHING
                                """),
                                {"hash": url_hash, "url": url, "keyword": keyword, 
                                 "platform": platform, "lead_id": lead_id}
                            )
                        else:
                            # 记录为非线索URL
                            await db.execute(
                                text("""
                                    INSERT INTO lead_hunt_searched_urls 
                                    (url_hash, url, source_keyword, platform, is_lead)
                                    VALUES (:hash, :url, :keyword, :platform, false)
                                    ON CONFLICT (url_hash) DO NOTHING
                                """),
                                {"hash": url_hash, "url": url, "keyword": keyword, "platform": platform}
                            )
                            
                    except Exception as e:
                        self.log(f"分析内容失败: {e}", "error")
                
                # 4. 更新关键词效果统计
                for keyword, stats in keyword_stats.items():
                    if stats["id"]:
                        await db.execute(
                            text("""
                                SELECT update_keyword_stats(:kw_id, :leads, :high_intent)
                            """),
                            {"kw_id": stats["id"], "leads": stats["leads"], "high_intent": stats["high_intent"]}
                        )
                
                # 5. 记录搜索历史
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                await db.execute(
                    text("""
                        INSERT INTO lead_hunt_history 
                        (keyword, search_query, results_count, leads_found, high_intent_leads, duration_ms)
                        VALUES (:keyword, :query, :results, :leads, :high_intent, :duration)
                    """),
                    {
                        "keyword": ", ".join(results["keywords_used"]),
                        "query": ", ".join(results["search_queries"][:10]),  # 只记录前10个
                        "results": len(all_raw_results),
                        "leads": results["total_leads"],
                        "high_intent": results["high_intent_leads"],
                        "duration": duration_ms
                    }
                )
                
                # 6. 更新每日统计
                today = datetime.now().date()
                await db.execute(
                    text("""
                        INSERT INTO lead_hunt_stats 
                        (stat_date, total_searches, total_results, total_leads, high_intent_leads, unique_urls)
                        VALUES (:date, 1, :results, :leads, :high_intent, :urls)
                        ON CONFLICT (stat_date) DO UPDATE SET
                            total_searches = lead_hunt_stats.total_searches + 1,
                            total_results = lead_hunt_stats.total_results + :results,
                            total_leads = lead_hunt_stats.total_leads + :leads,
                            high_intent_leads = lead_hunt_stats.high_intent_leads + :high_intent,
                            unique_urls = lead_hunt_stats.unique_urls + :urls,
                            updated_at = NOW()
                    """),
                    {
                        "date": today,
                        "results": len(all_raw_results),
                        "leads": results["total_leads"],
                        "high_intent": results["high_intent_leads"],
                        "urls": results["new_urls"]
                    }
                )
                
                # 7. 更新小猎的任务统计
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
        
        except Exception as e:
            self.log(f"智能狩猎出错: {e}", "error")
            results["error"] = str(e)
            await self.log_error(str(e), "智能狩猎任务出错")
            await self.end_task_session(error_message=str(e))
            return results
        
        # 去重sources_searched
        results["sources_searched"] = list(set(results["sources_searched"]))
        
        duration = (datetime.now() - start_time).total_seconds()
        results["stats"] = {
            "duration_seconds": round(duration, 2),
            "keywords_count": len(results["keywords_used"]),
            "queries_count": len(results["search_queries"]),
            "new_urls_analyzed": results["new_urls"],
            "duplicate_urls_skipped": results["duplicate_urls"]
        }
        
        self.log(f"✅ 智能狩猎完成！耗时{duration:.1f}秒，新URL {results['new_urls']} 条，"
                 f"发现线索 {results['total_leads']} 条，高意向 {results['high_intent_leads']} 条")
        
        # 结束任务会话（实时直播）
        await self.end_task_session(
            f"发现 {results['total_leads']} 条线索，其中高意向 {results['high_intent_leads']} 条"
        )
        
        return results
    
    def _select_platforms_by_time(self) -> List[tuple]:
        """
        根据当前时间智能选择搜索平台
        不同时间段用户活跃的平台不同
        """
        current_hour = datetime.now().hour
        
        # 深夜/凌晨 (0-6点) - 搜索量较少，主要搜Google
        if 0 <= current_hour < 6:
            return [
                ("google", ""),
                ("zhihu", self.PLATFORMS["zhihu"]["site"])
            ]
        # 早上 (6-9点) - 微博活跃
        elif 6 <= current_hour < 9:
            return [
                ("weibo", self.PLATFORMS["weibo"]["site"]),
                ("google", "")
            ]
        # 上午工作时间 (9-12点) - 全面搜索
        elif 9 <= current_hour < 12:
            return [
                ("google", ""),
                ("zhihu", self.PLATFORMS["zhihu"]["site"]),
                ("weibo", self.PLATFORMS["weibo"]["site"])
            ]
        # 午休时间 (12-14点) - 社交平台活跃
        elif 12 <= current_hour < 14:
            return [
                ("weibo", self.PLATFORMS["weibo"]["site"]),
                ("xiaohongshu", self.PLATFORMS["xiaohongshu"]["site"]),
                ("google", "")
            ]
        # 下午工作时间 (14-18点) - 全面搜索
        elif 14 <= current_hour < 18:
            return [
                ("google", ""),
                ("zhihu", self.PLATFORMS["zhihu"]["site"]),
                ("tieba", self.PLATFORMS["tieba"]["site"])
            ]
        # 晚间 (18-22点) - 社交平台最活跃
        elif 18 <= current_hour < 22:
            return [
                ("weibo", self.PLATFORMS["weibo"]["site"]),
                ("zhihu", self.PLATFORMS["zhihu"]["site"]),
                ("douyin", self.PLATFORMS["douyin"]["site"]),
                ("google", "")
            ]
        # 深夜 (22-24点) - 知乎夜猫子活跃
        else:
            return [
                ("zhihu", self.PLATFORMS["zhihu"]["site"]),
                ("google", "")
            ]
    
    async def _get_hunt_stats(self) -> Dict[str, Any]:
        """
        获取搜索统计数据
        """
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 今日统计
                today_result = await db.execute(
                    text("""
                        SELECT total_searches, total_results, total_leads, 
                               high_intent_leads, unique_urls
                        FROM lead_hunt_stats
                        WHERE stat_date = CURRENT_DATE
                    """)
                )
                today = today_result.fetchone()
                
                # 本周统计
                week_result = await db.execute(
                    text("""
                        SELECT SUM(total_searches), SUM(total_results), 
                               SUM(total_leads), SUM(high_intent_leads)
                        FROM lead_hunt_stats
                        WHERE stat_date >= CURRENT_DATE - INTERVAL '7 days'
                    """)
                )
                week = week_result.fetchone()
                
                # 最佳关键词
                best_kw_result = await db.execute(
                    text("""
                        SELECT keyword, leads_found, success_rate
                        FROM lead_hunt_keywords
                        WHERE is_active = true AND search_count > 0
                        ORDER BY success_rate DESC
                        LIMIT 5
                    """)
                )
                best_keywords = best_kw_result.fetchall()
                
                return {
                    "today": {
                        "searches": today[0] if today else 0,
                        "results": today[1] if today else 0,
                        "leads": today[2] if today else 0,
                        "high_intent": today[3] if today else 0,
                        "unique_urls": today[4] if today else 0
                    },
                    "this_week": {
                        "searches": week[0] if week else 0,
                        "results": week[1] if week else 0,
                        "leads": week[2] if week else 0,
                        "high_intent": week[3] if week else 0
                    },
                    "best_keywords": [
                        {"keyword": kw[0], "leads": kw[1], "success_rate": round(kw[2] * 100, 1)}
                        for kw in best_keywords
                    ]
                }
        except Exception as e:
            self.log(f"获取统计失败: {e}", "error")
            return {"error": str(e)}
    
    async def _full_hunt(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整的线索狩猎流程 - 使用Serper API搜索
        (保留原有方法以保持兼容性)
        - 只搜索最近1个月内的内容
        """
        self.log("开始线索狩猎任务（仅搜索最近1个月内的线索）...")
        
        # 检查API配置
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            self.log("Serper API未配置，无法进行搜索", "error")
            return {
                "error": "搜索API未配置",
                "message": "请在系统设置中配置 SERPER_API_KEY 以启用线索搜索功能",
                "hunt_time": datetime.now().isoformat(),
                "sources_searched": [],
                "leads_found": [],
                "total_leads": 0
            }
        
        results = {
            "hunt_time": datetime.now().isoformat(),
            "sources_searched": [],
            "leads_found": [],
            "total_leads": 0,
            "high_intent_leads": 0,
            "search_queries": []
        }
        
        # 获取自定义关键词或使用默认关键词
        keywords = input_data.get("keywords", self.FALLBACK_KEYWORDS[:6])
        
        # 定义搜索平台和对应的site限定
        platforms = [
            ("weibo", "site:weibo.com"),
            ("zhihu", "site:zhihu.com"),
            ("tieba", "site:tieba.baidu.com"),
            ("google", "")  # 全网搜索
        ]
        
        all_raw_results = []
        
        # 对每个关键词和平台组合进行搜索
        for keyword in keywords[:3]:  # 限制搜索次数，控制API调用
            for platform_name, site_filter in platforms:
                try:
                    query = f"{keyword} {site_filter}".strip()
                    self.log(f"搜索: {query}")
                    results["search_queries"].append(query)
                    
                    search_results = await self._search_with_serper(query)
                    
                    if search_results:
                        results["sources_searched"].append(platform_name)
                        for item in search_results:
                            item["platform"] = platform_name
                            item["keyword"] = keyword
                            all_raw_results.append(item)
                    
                    # 避免请求过快
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.log(f"搜索失败 ({platform_name}, {keyword}): {e}", "error")
        
        # 去重（根据URL）
        seen_urls = set()
        unique_results = []
        for item in all_raw_results:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(item)
        
        self.log(f"共获取 {len(unique_results)} 条去重后的搜索结果")
        
        # 分析每个搜索结果
        for item in unique_results[:20]:  # 限制分析数量
            try:
                content = f"{item.get('title', '')} {item.get('content', '')}"
                
                # 快速过滤
                if self._quick_filter(content):
                    continue
                
                # AI深度分析
                analysis = await self._analyze_content({
                    "content": content,
                    "source": item.get("platform", "google"),
                    "url": item.get("url", "")
                })
                
                if analysis.get("is_lead"):
                    # 提取联系方式
                    contact_info = analysis.get("contact_info", {})
                    extracted_contact = self._extract_contact_info(content)
                    # 合并联系信息
                    for key, value in extracted_contact.items():
                        if value and not contact_info.get(key):
                            contact_info[key] = value
                    
                    lead_data = {
                        "title": item.get("title", ""),
                        "content": content,
                        "url": item.get("url", ""),
                        "source": item.get("platform", "google"),
                        "keyword": item.get("keyword", ""),
                        "found_at": datetime.now().isoformat(),
                        "is_lead": True,
                        "confidence": analysis.get("confidence", 50),
                        "intent_level": analysis.get("intent_level", "medium"),
                        "lead_type": analysis.get("lead_type", ""),
                        "needs": analysis.get("needs", []),
                        "contact_info": contact_info,
                        "summary": analysis.get("summary", ""),
                        "follow_up_suggestion": analysis.get("follow_up_suggestion", "")
                    }
                    
                    results["leads_found"].append(lead_data)
                    results["total_leads"] += 1
                    
                    if analysis.get("intent_level") == "high":
                        results["high_intent_leads"] += 1
                        
            except Exception as e:
                self.log(f"分析内容失败: {e}", "error")
        
        # 去重sources_searched
        results["sources_searched"] = list(set(results["sources_searched"]))
        
        self.log(f"线索狩猎完成！找到 {results['total_leads']} 条线索，其中高意向 {results['high_intent_leads']} 条")
        
        return results
    
    async def _search_with_serper(self, query: str, time_range: str = "m") -> List[Dict[str, Any]]:
        """
        使用Serper API搜索
        
        Args:
            query: 搜索查询
            time_range: 时间范围限制
                - "d": 过去一天
                - "w": 过去一周  
                - "m": 过去一个月（默认）
                - "y": 过去一年
                - None: 不限制时间
        """
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return []
        
        try:
            # 构建搜索参数
            search_params = {
                "q": query,
                "gl": "cn",
                "hl": "zh-cn",
                "num": 10
            }
            
            # 添加时间限制：tbs参数控制搜索结果时间范围
            # qdr:d = 过去一天, qdr:w = 过去一周, qdr:m = 过去一个月, qdr:y = 过去一年
            if time_range:
                search_params["tbs"] = f"qdr:{time_range}"
                self.log(f"🕐 搜索时间限制: 过去{'一天' if time_range == 'd' else '一周' if time_range == 'w' else '一个月' if time_range == 'm' else '一年'}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json"
                    },
                    json=search_params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for item in data.get("organic", []):
                        results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet", ""),
                            "url": item.get("link", ""),
                            "position": item.get("position", 0)
                        })
                    
                    return results
                else:
                    self.log(f"Serper API返回错误: {response.status_code}", "error")
                    
        except Exception as e:
            self.log(f"Serper搜索异常: {e}", "error")
        
        return []
    
    # 公开方法供外部调用
    async def search_with_serper(self, query: str, time_range: str = "m") -> List[Dict[str, Any]]:
        """
        公开的Serper搜索方法
        
        Args:
            query: 搜索查询
            time_range: 时间范围限制（默认1个月）
                - "d": 过去一天
                - "w": 过去一周
                - "m": 过去一个月（默认）
                - "y": 过去一年
                - None: 不限制时间
        """
        return await self._search_with_serper(query, time_range)
    
    async def _analyze_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用AI分析内容是否是潜在客户
        """
        content = input_data.get("content", "")
        source = input_data.get("source", "unknown")
        url = input_data.get("url", "")
        
        if not content:
            return {"is_lead": False, "reason": "内容为空"}
        
        # 快速规则判断
        # 检查是否包含高意向关键词
        has_high_intent = any(kw in content for kw in self.HIGH_INTENT_KEYWORDS)
        
        # 用AI深度分析（清理用户输入防止注入）
        safe_content = sanitize_user_input(content, max_length=5000)
        safe_url = sanitize_user_input(url, max_length=500)
        safe_source = sanitize_user_input(source, max_length=100)
        
        prompt = f"""请分析以下内容是否是潜在的物流客户线索：

来源平台：{safe_source}
URL：{safe_url}
内容：{safe_content}

注意：
1. 如果这是物流公司/货代公司的广告或推广，返回 is_lead: false
2. 如果这是真实的客户在寻找物流服务，返回 is_lead: true
3. 包含具体发货需求（目的地、货物、时间）的线索优先级更高

请以JSON格式返回分析结果。"""
        
        try:
            response = await self.think([{"role": "user", "content": prompt}])
            
            # 解析AI回复
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                
                # 如果有高意向关键词，提升意向等级
                if has_high_intent and result.get("is_lead"):
                    if result.get("intent_level") == "low":
                        result["intent_level"] = "medium"
                    elif result.get("intent_level") == "medium":
                        result["intent_level"] = "high"
                
                return result
        except json.JSONDecodeError:
            self.log("AI分析结果解析失败", "warning")
        except Exception as e:
            self.log(f"AI分析异常: {e}", "error")
        
        # 如果AI分析失败，使用规则判断
        return self._rule_based_analysis(content, has_high_intent)
    
    def _rule_based_analysis(self, content: str, has_high_intent: bool) -> Dict[str, Any]:
        """
        基于规则的简单分析（AI失败时的备选）
        """
        # 检查是否是广告
        is_ad = any(kw in content for kw in self.AD_FILTER_KEYWORDS)
        if is_ad:
            return {"is_lead": False, "reason": "疑似广告内容"}
        
        # 检查是否包含需求关键词
        need_keywords = ["找", "求", "想", "要", "需要", "推荐", "哪家", "怎么选"]
        has_need = any(kw in content for kw in need_keywords)
        
        if has_need:
            return {
                "is_lead": True,
                "confidence": 60 if has_high_intent else 40,
                "intent_level": "high" if has_high_intent else "medium",
                "needs": [],
                "contact_info": {},
                "summary": "规则匹配的潜在线索",
                "follow_up_suggestion": "建议进一步分析"
            }
        
        return {"is_lead": False, "reason": "未匹配到需求关键词"}
    
    def _quick_filter(self, content: str) -> bool:
        """
        快速过滤明显不是线索的内容
        """
        # 过滤太短的内容
        if len(content) < 15:
            return True
        
        # 过滤明显的广告
        ad_strong_keywords = [
            "招商加盟", "代理商招募", "诚招代理",
            "我司专业", "本公司专业", "欢迎来电",
            "业务合作", "招聘司机", "招聘业务员"
        ]
        for kw in ad_strong_keywords:
            if kw in content:
                return True
        
        return False
    
    def _extract_contact_info(self, content: str) -> Dict[str, str]:
        """
        从内容中提取联系方式
        """
        contact = {
            "phone": "",
            "email": "",
            "wechat": "",
            "qq": "",
            "name": "",
            "company": ""
        }
        
        # 提取手机号
        phone_pattern = r'1[3-9]\d{9}'
        phones = re.findall(phone_pattern, content)
        if phones:
            contact["phone"] = phones[0]
        
        # 提取邮箱
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, content)
        if emails:
            contact["email"] = emails[0]
        
        # 提取微信号
        wechat_patterns = [
            r'微信[：:]\s*([a-zA-Z0-9_-]+)',
            r'wx[：:]\s*([a-zA-Z0-9_-]+)',
            r'V[：:]\s*([a-zA-Z0-9_-]+)',
            r'WeChat[：:]\s*([a-zA-Z0-9_-]+)'
        ]
        for pattern in wechat_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                contact["wechat"] = match.group(1)
                break
        
        # 提取QQ
        qq_patterns = [
            r'QQ[：:]\s*(\d{5,12})',
            r'qq[：:]\s*(\d{5,12})'
        ]
        for pattern in qq_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                contact["qq"] = match.group(1)
                break
        
        return contact
    
    async def _search_leads(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据指定参数搜索线索
        """
        keywords = input_data.get("keywords", self.FALLBACK_KEYWORDS[:3])
        sources = input_data.get("sources", ["google"])
        
        results = []
        for keyword in keywords:
            for source in sources:
                site_filter = ""
                if source == "weibo":
                    site_filter = "site:weibo.com"
                elif source == "zhihu":
                    site_filter = "site:zhihu.com"
                elif source == "tieba":
                    site_filter = "site:tieba.baidu.com"
                
                query = f"{keyword} {site_filter}".strip()
                search_results = await self._search_with_serper(query)
                results.extend(search_results)
        
        return {"results": results, "count": len(results)}
    
    async def add_keyword(self, keyword: str, keyword_type: str = "general", 
                          platform: str = None, priority: int = 5) -> Dict[str, Any]:
        """
        添加新的搜索关键词
        """
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO lead_hunt_keywords 
                        (keyword, keyword_type, platform, priority)
                        VALUES (:keyword, :type, :platform, :priority)
                        ON CONFLICT (keyword, platform) DO UPDATE SET
                            priority = :priority,
                            is_active = true,
                            updated_at = NOW()
                    """),
                    {"keyword": keyword, "type": keyword_type, 
                     "platform": platform, "priority": priority}
                )
                await db.commit()
            
            return {"success": True, "keyword": keyword}
        except Exception as e:
            self.log(f"添加关键词失败: {e}", "error")
            return {"success": False, "error": str(e)}


    # ==================== 话题发现模式（新增）====================
    
    def _enhance_search_keyword(self, keyword: str) -> str:
        """
        增强搜索关键词，添加同义词和相关术语以提高搜索覆盖率
        """
        # 关键词同义词映射
        keyword_synonyms = {
            "跨境电商物流": "跨境电商物流 OR 跨境物流 OR 国际电商物流",
            "国际货运代理": "国际货运代理 OR 货代 OR 国际货代",
            "海外仓": "海外仓 OR 海外仓储 OR 境外仓",
            "双清包税": "双清包税 OR DDP OR 双清",
            "海运费查询": "海运费查询 OR 海运价格 OR 海运费用",
            "FBA头程": "FBA头程 OR FBA物流 OR 亚马逊头程",
            "清关": "清关 OR 报关 OR 通关",
        }
        
        # 如果关键词有同义词，使用扩展后的查询
        if keyword in keyword_synonyms:
            return keyword_synonyms[keyword]
        
        # 对于包含特定术语的关键词，添加相关搜索词
        if "物流" in keyword and "跨境" not in keyword:
            return f"{keyword} OR 国际物流"
        if "货代" in keyword:
            return f"{keyword} OR 国际货代"
        if "FBA" in keyword:
            return f"{keyword} OR 亚马逊物流"
        
        return keyword

    async def _discover_topics(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发现热门话题 - 用于内容引流
        搜索知乎、小红书等平台的热门物流相关话题
        """
        self.log("🔍 开始发现热门话题...")
        start_time = datetime.now()
        
        # 检查API配置
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return {
                "error": "搜索API未配置",
                "message": "请在系统设置中配置 SERPER_API_KEY"
            }
        
        results = {
            "discover_time": datetime.now().isoformat(),
            "mode": "topic_discovery",
            "topics_found": [],
            "total_topics": 0,
            "high_value_topics": 0,
            "platforms_searched": [],
            "keywords_used": []
        }
        
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 1. 获取搜索关键词
                max_keywords = input_data.get("max_keywords", 8)
                
                kw_result = await db.execute(
                    text("""
                        SELECT id, keyword, category, platform, priority
                        FROM topic_search_keywords
                        WHERE is_active = true
                        ORDER BY priority DESC, RANDOM()
                        LIMIT :limit
                    """),
                    {"limit": max_keywords}
                )
                keywords_data = kw_result.fetchall()
                
                if not keywords_data:
                    # 使用默认关键词
                    default_keywords = [
                        ("FBA头程费用", "报价咨询"),
                        ("货物被扣怎么办", "问题求助"),
                        ("货代怎么选", "选择咨询"),
                        ("海运清关流程", "流程咨询"),
                        ("国际物流报价", "报价咨询"),
                        ("跨境电商物流", "行业讨论"),
                        ("国际货运代理", "选择咨询"),
                        ("海外仓服务", "流程咨询"),
                        ("双清包税", "流程咨询"),
                        ("海运费查询", "报价咨询")
                    ]
                    keywords_data = [(None, kw, cat, None, 8) for kw, cat in default_keywords]
                
                self.log(f"使用 {len(keywords_data)} 个关键词搜索话题")
                
                # 2. 定义搜索平台（扩展更多平台，提高话题发现覆盖率）
                platforms = [
                    ("zhihu", "site:zhihu.com/question", "知乎问答"),
                    ("xiaohongshu", "site:xiaohongshu.com", "小红书"),
                    ("baidu_zhidao", "site:zhidao.baidu.com", "百度知道"),
                    ("tieba", "site:tieba.baidu.com", "百度贴吧"),
                    ("douyin", "site:douyin.com", "抖音"),
                    ("weibo", "site:weibo.com", "微博"),
                ]
                
                all_topics = []
                
                # 3. 对每个关键词在每个平台搜索
                for kw_data in keywords_data:
                    kw_id, keyword, category, kw_platform, priority = kw_data
                    results["keywords_used"].append(keyword)
                    
                    # 增强搜索关键词
                    enhanced_keyword = self._enhance_search_keyword(keyword)
                    
                    for platform_id, site_filter, platform_name in platforms:
                        # 如果关键词指定了平台，只搜索该平台
                        if kw_platform and kw_platform != platform_id:
                            continue
                        
                        try:
                            # 构建搜索查询（优化查询逻辑，支持更广泛的行业术语）
                            query = f"{enhanced_keyword} {site_filter}".strip()
                            self.log(f"🔍 搜索: {query}")
                            
                            # 话题发现严格限制在过去一个月内，确保内容的时效性
                            search_results = await self._search_with_serper(query, time_range="m")
                            
                            if search_results:
                                self.log(f"✅ {platform_name} 返回 {len(search_results)} 条结果")
                                results["platforms_searched"].append(platform_name)
                                
                                for item in search_results[:5]:  # 每个关键词每个平台取前5条
                                    url = item.get("url", "")
                                    title = item.get("title", "")
                                    
                                    if not url or not title:
                                        continue
                                    
                                    # 检查是否已存在
                                    url_hash = hashlib.md5(url.encode()).hexdigest()
                                    
                                    existing = await db.execute(
                                        text("SELECT id FROM hot_topics WHERE url_hash = :hash"),
                                        {"hash": url_hash}
                                    )
                                    if existing.fetchone():
                                        continue
                                    
                                    # 分析话题价值
                                    self.log(f"🧠 AI分析话题价值: {title[:30]}...")
                                    topic_analysis = await self._analyze_topic_value({
                                        "title": title,
                                        "content": item.get("content", ""),
                                        "url": url,
                                        "platform": platform_id,
                                        "category": category
                                    })
                                    
                                    if topic_analysis.get("is_valuable", False):
                                        self.log(f"🎯 发现高价值话题: {title[:30]} (分数: {topic_analysis.get('value_score')})")
                                        
                                        # 立即保存话题到数据库，实现增量更新
                                        await db.execute(
                                            text("""
                                                INSERT INTO hot_topics 
                                                (title, url, url_hash, platform, category, keywords,
                                                 value_score, ai_summary, ai_answer_strategy, 
                                                 ai_recommended_points, priority, status)
                                                VALUES 
                                                (:title, :url, :url_hash, :platform, :category, :keywords,
                                                 :value_score, :summary, :strategy, :points, :priority, 'new')
                                                ON CONFLICT (url_hash) DO NOTHING
                                            """),
                                            {
                                                "title": title,
                                                "url": url,
                                                "url_hash": url_hash,
                                                "platform": platform_id,
                                                "category": category,
                                                "keywords": [keyword],
                                                "value_score": topic_analysis.get("value_score", 50),
                                                "summary": topic_analysis.get("summary", ""),
                                                "strategy": topic_analysis.get("answer_strategy", ""),
                                                "points": topic_analysis.get("recommended_points", []),
                                                "priority": "high" if topic_analysis.get("value_score", 0) >= 70 else "medium"
                                            }
                                        )
                                        await db.commit()  # 立即提交
                                        
                                        topic_data = {
                                            "title": title,
                                            "url": url,
                                            "url_hash": url_hash,
                                            "platform": platform_id,
                                            "category": category,
                                            "keyword": keyword,
                                            "value_score": topic_analysis.get("value_score", 50)
                                        }
                                        results["topics_found"].append(topic_data)
                                        results["total_topics"] += 1
                                        if topic_analysis.get("value_score", 0) >= 70:
                                            results["high_value_topics"] += 1
                                    else:
                                        self.log(f"⏭️ 话题价值不足，跳过: {title[:30]} (理由: {topic_analysis.get('reason')})")
                            else:
                                self.log(f"❌ {platform_name} 未返回结果")
                            
                            # 控制请求频率
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            self.log(f"搜索话题失败 ({platform_name}, {keyword}): {e}", "error")
                
                # 4. 更新小猎的任务统计
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
                
        except Exception as e:
            self.log(f"话题发现出错: {e}", "error")
            results["error"] = str(e)
        
        # 去重平台列表
        results["platforms_searched"] = list(set(results["platforms_searched"]))
        
        duration = (datetime.now() - start_time).total_seconds()
        results["duration_seconds"] = round(duration, 2)
        
        self.log(f"✅ 话题发现完成！耗时{duration:.1f}秒，发现 {results['total_topics']} 个话题，"
                 f"高价值 {results['high_value_topics']} 个")
        
        return results
    
    async def _analyze_topic_value(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析话题价值，判断是否值得回答
        """
        title = input_data.get("title", "")
        content = input_data.get("content", "")
        url = input_data.get("url", "")
        platform = input_data.get("platform", "")
        category = input_data.get("category", "")
        
        if not title:
            return {"is_valuable": False, "reason": "标题为空"}
        
        # 快速过滤广告和无效内容
        ad_keywords = ["广告", "推广", "优惠", "限时", "加盟", "招商", "代理"]
        if any(kw in title for kw in ad_keywords):
            return {"is_valuable": False, "reason": "疑似广告"}
        
        # 使用AI分析话题价值
        prompt = f"""请分析以下话题是否值得一个物流/货代公司去回答（内容引流目的）：

平台：{platform}
标题：{title}
内容摘要：{content[:300] if content else '无'}

请从以下角度分析：
1. 这个话题是否与国际物流/货代服务相关？
2. 提问者是否可能是潜在客户？
3. 回答这个问题能否展示专业性？
4. 预计能带来多少曝光？

请以JSON格式返回：
{{
    "is_valuable": true/false,
    "value_score": 0-100,
    "summary": "话题核心是什么",
    "answer_strategy": "建议如何回答这个问题",
    "recommended_points": ["回答要点1", "回答要点2", "回答要点3"],
    "potential_exposure": "high/medium/low",
    "reason": "判断理由"
}}"""
        
        try:
            response = await self.think([{"role": "user", "content": prompt}])
            
            # 解析AI回复
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
        except Exception as e:
            self.log(f"AI分析话题失败: {e}", "warning")
        
        # 如果AI分析失败，使用规则判断
        value_keywords = ["怎么", "如何", "推荐", "哪家", "多少钱", "费用", "流程", "问题"]
        has_value = any(kw in title for kw in value_keywords)
        
        return {
            "is_valuable": has_value,
            "value_score": 60 if has_value else 30,
            "summary": title[:50],
            "answer_strategy": "提供专业建议，展示公司优势",
            "recommended_points": ["专业解答", "案例分享", "联系方式"],
            "reason": "规则判断"
        }
    
    async def _generate_answer(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为话题生成专业回答内容（调用小文）
        """
        topic_id = input_data.get("topic_id")
        
        if not topic_id:
            return {"error": "缺少话题ID"}
        
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            from app.agents.copywriter import copywriter_agent
            
            async with async_session_maker() as db:
                # 获取话题信息
                result = await db.execute(
                    text("""
                        SELECT title, url, platform, category, 
                               ai_summary, ai_answer_strategy, ai_recommended_points
                        FROM hot_topics WHERE id = :id
                    """),
                    {"id": topic_id}
                )
                topic = result.fetchone()
                
                if not topic:
                    return {"error": "话题不存在"}
                
                title, url, platform, category, summary, strategy, points = topic
                
                # 获取公司信息
                company_result = await db.execute(
                    text("SELECT company_name, company_intro, advantages, contact_wechat, contact_phone FROM company_config LIMIT 1")
                )
                company = company_result.fetchone()
                
                company_name = company[0] if company else "我们公司"
                company_intro = company[1] if company else ""
                advantages = company[2] if company else []
                contact_wechat = company[3] if company else ""
                contact_phone = company[4] if company else ""
                
                # 调用小文生成内容
                content_result = await copywriter_agent.process({
                    "action": "generate",
                    "content_type": "zhihu_answer" if platform == "zhihu" else "social_post",
                    "topic": title,
                    "context": {
                        "platform": platform,
                        "category": category,
                        "summary": summary,
                        "strategy": strategy,
                        "recommended_points": points,
                        "company_name": company_name,
                        "company_intro": company_intro,
                        "advantages": advantages,
                        "contact_wechat": contact_wechat,
                        "contact_phone": contact_phone
                    }
                })
                
                generated_content = content_result.get("content", "")
                
                if generated_content:
                    # 保存生成的内容
                    await db.execute(
                        text("""
                            UPDATE hot_topics 
                            SET generated_content = :content,
                                generated_at = NOW(),
                                updated_at = NOW()
                            WHERE id = :id
                        """),
                        {"content": generated_content, "id": topic_id}
                    )
                    await db.commit()
                
                return {
                    "success": True,
                    "topic_id": topic_id,
                    "title": title,
                    "platform": platform,
                    "generated_content": generated_content,
                    "url": url
                }
                
        except Exception as e:
            self.log(f"生成回答失败: {e}", "error")
            return {"error": str(e)}
    
    async def _get_topic_stats(self) -> Dict[str, Any]:
        """获取话题发现统计"""
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 总话题数
                total_result = await db.execute(
                    text("SELECT COUNT(*) FROM hot_topics")
                )
                total = total_result.scalar() or 0
                
                # 待回答话题数
                new_result = await db.execute(
                    text("SELECT COUNT(*) FROM hot_topics WHERE status = 'new'")
                )
                new_count = new_result.scalar() or 0
                
                # 已回答数
                answered_result = await db.execute(
                    text("SELECT COUNT(*) FROM hot_topics WHERE status = 'answered'")
                )
                answered_count = answered_result.scalar() or 0
                
                # 高价值话题数
                high_value_result = await db.execute(
                    text("SELECT COUNT(*) FROM hot_topics WHERE value_score >= 70 AND status = 'new'")
                )
                high_value_count = high_value_result.scalar() or 0
                
                # 按平台统计
                platform_result = await db.execute(
                    text("""
                        SELECT platform, COUNT(*) 
                        FROM hot_topics 
                        WHERE status = 'new'
                        GROUP BY platform
                    """)
                )
                by_platform = {row[0]: row[1] for row in platform_result.fetchall()}
                
                return {
                    "total": total,
                    "new": new_count,
                    "answered": answered_count,
                    "high_value": high_value_count,
                    "by_platform": by_platform
                }
                
        except Exception as e:
            self.log(f"获取话题统计失败: {e}", "error")
            return {"error": str(e)}

    # ==================== 产品趋势发现模式（新增）====================
    
    async def _discover_product_trends(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发现欧洲跨境电商热门产品趋势
        搜索完成后交给小调处理：存入知识库 + 发送邮件
        """
        self.log("🛒 开始发现欧洲热门产品趋势...")
        start_time = datetime.now()
        
        # 检查API配置
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return {
                "error": "搜索API未配置",
                "message": "请在系统设置中配置 SERPER_API_KEY"
            }
        
        results = {
            "discover_time": datetime.now().isoformat(),
            "mode": "product_trend_discovery",
            "products_found": [],
            "total_products": 0,
            "high_trend_products": 0,
            "platforms_searched": [],
            "keywords_used": []
        }
        
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 1. 获取搜索关键词
                max_keywords = input_data.get("max_keywords", 10)
                
                kw_result = await db.execute(
                    text("""
                        SELECT id, keyword, category, platform, priority
                        FROM product_trend_keywords
                        WHERE is_active = true
                        ORDER BY priority DESC, RANDOM()
                        LIMIT :limit
                    """),
                    {"limit": max_keywords}
                )
                keywords_data = kw_result.fetchall()
                
                if not keywords_data:
                    # 使用默认关键词
                    default_keywords = [
                        ("欧洲跨境电商爆款 2026", "综合"),
                        ("德国亚马逊热销产品", "亚马逊"),
                        ("英国电商热卖", "综合"),
                        ("Temu欧洲热销", "新平台"),
                        ("欧洲家居用品热销", "家居"),
                    ]
                    keywords_data = [(None, kw, cat, None, 8) for kw, cat in default_keywords]
                
                self.log(f"使用 {len(keywords_data)} 个关键词搜索产品趋势")
                
                # 2. 定义搜索平台
                platforms = [
                    ("google", "", "谷歌搜索"),
                    ("baidu", "site:baidu.com", "百度"),
                ]
                
                all_products = []
                
                # 3. 对每个关键词搜索
                for kw_data in keywords_data:
                    kw_id, keyword, category, kw_platform, priority = kw_data
                    results["keywords_used"].append(keyword)
                    
                    for platform_id, site_filter, platform_name in platforms:
                        try:
                            # 构建搜索查询
                            query = f"{keyword} {site_filter}".strip()
                            self.log(f"🔍 搜索: {query}")
                            
                            search_results = await self._search_with_serper(query)
                            
                            if search_results:
                                results["platforms_searched"].append(platform_name)
                                
                                for item in search_results[:5]:  # 每个关键词取前5条
                                    url = item.get("url", "")
                                    title = item.get("title", "")
                                    content = item.get("content", "")
                                    
                                    if not url or not title:
                                        continue
                                    
                                    # 检查是否已存在
                                    existing = await db.execute(
                                        text("SELECT id FROM product_trends WHERE source_url = :url"),
                                        {"url": url}
                                    )
                                    if existing.fetchone():
                                        continue
                                    
                                    # AI分析产品趋势
                                    product_analysis = await self._analyze_product_trend({
                                        "title": title,
                                        "content": content,
                                        "url": url,
                                        "platform": platform_id,
                                        "category": category,
                                        "keyword": keyword
                                    })
                                    
                                    if product_analysis.get("is_valid_product", False):
                                        product_data = {
                                            "product_name": product_analysis.get("product_name", title[:100]),
                                            "category": product_analysis.get("category", category),
                                            "description": product_analysis.get("description", content[:500]),
                                            "source_url": url,
                                            "source_platform": platform_id,
                                            "source_region": "europe",
                                            "sales_volume": product_analysis.get("sales_volume", ""),
                                            "price_range": product_analysis.get("price_range", ""),
                                            "growth_rate": product_analysis.get("growth_rate", ""),
                                            "trend_score": product_analysis.get("trend_score", 50),
                                            "ai_analysis": product_analysis.get("analysis", ""),
                                            "ai_opportunity": product_analysis.get("opportunity", ""),
                                            "ai_logistics_tips": product_analysis.get("logistics_tips", ""),
                                            "keywords": [keyword] + product_analysis.get("keywords", [])
                                        }
                                        all_products.append(product_data)
                            
                            # 控制请求频率
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            self.log(f"搜索产品趋势失败 ({platform_name}, {keyword}): {e}", "error")
                
                # 4. 保存产品趋势到数据库
                saved_products = []
                for product in all_products:
                    try:
                        result = await db.execute(
                            text("""
                                INSERT INTO product_trends 
                                (product_name, category, description, source_url, source_platform,
                                 source_region, sales_volume, price_range, growth_rate, trend_score,
                                 ai_analysis, ai_opportunity, ai_logistics_tips, keywords, status)
                                VALUES 
                                (:name, :category, :desc, :url, :platform, :region, :sales,
                                 :price, :growth, :score, :analysis, :opportunity, :logistics, :keywords, 'new')
                                ON CONFLICT DO NOTHING
                                RETURNING id
                            """),
                            {
                                "name": product["product_name"],
                                "category": product["category"],
                                "desc": product["description"],
                                "url": product["source_url"],
                                "platform": product["source_platform"],
                                "region": product["source_region"],
                                "sales": product["sales_volume"],
                                "price": product["price_range"],
                                "growth": product["growth_rate"],
                                "score": product["trend_score"],
                                "analysis": product["ai_analysis"],
                                "opportunity": product["ai_opportunity"],
                                "logistics": product["ai_logistics_tips"],
                                "keywords": product["keywords"]
                            }
                        )
                        row = result.fetchone()
                        if row:
                            product["id"] = str(row[0])
                            saved_products.append(product)
                            results["products_found"].append(product)
                            results["total_products"] += 1
                            if product["trend_score"] >= 70:
                                results["high_trend_products"] += 1
                            
                    except Exception as e:
                        self.log(f"保存产品趋势失败: {e}", "error")
                
                await db.commit()
                
                # 5. 更新小猎的任务统计
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
                
                # 6. 如果有发现产品，交给小调处理
                if saved_products:
                    await self._notify_coordinator_for_products(saved_products, db)
                
        except Exception as e:
            self.log(f"产品趋势发现出错: {e}", "error")
            results["error"] = str(e)
        
        # 去重平台列表
        results["platforms_searched"] = list(set(results["platforms_searched"]))
        
        duration = (datetime.now() - start_time).total_seconds()
        results["duration_seconds"] = round(duration, 2)
        
        self.log(f"✅ 产品趋势发现完成！耗时{duration:.1f}秒，发现 {results['total_products']} 个产品，"
                 f"高趋势 {results['high_trend_products']} 个")
        
        return results
    
    async def _analyze_product_trend(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析产品趋势价值
        """
        title = input_data.get("title", "")
        content = input_data.get("content", "")
        url = input_data.get("url", "")
        category = input_data.get("category", "")
        keyword = input_data.get("keyword", "")
        
        if not title:
            return {"is_valid_product": False, "reason": "标题为空"}
        
        # 快速过滤非产品内容
        invalid_keywords = ["招聘", "加盟", "代理", "培训", "课程", "教程"]
        if any(kw in title for kw in invalid_keywords):
            return {"is_valid_product": False, "reason": "非产品内容"}
        
        # 使用AI分析产品趋势
        prompt = f"""请分析以下搜索结果是否是有价值的欧洲跨境电商产品趋势信息：

搜索关键词：{keyword}
标题：{title}
内容摘要：{content[:500] if content else '无'}
URL：{url}

请从以下角度分析：
1. 这是否是具体的产品或产品类目信息？
2. 这个产品在欧洲市场的热度如何？
3. 作为物流公司，了解这个信息有什么价值？
4. 这类产品的物流需求特点是什么？

请以JSON格式返回：
{{
    "is_valid_product": true/false,
    "product_name": "产品名称",
    "category": "产品类别",
    "description": "产品简要描述",
    "sales_volume": "销量描述，如'热销'、'10万+'等",
    "price_range": "价格区间，如'€10-30'",
    "growth_rate": "增长率描述，如'增长50%'",
    "trend_score": 0-100,
    "analysis": "产品趋势分析摘要",
    "opportunity": "对物流公司的商机分析",
    "logistics_tips": "针对该产品的物流建议（包装、时效、清关等）",
    "keywords": ["相关关键词1", "关键词2"],
    "reason": "判断理由"
}}"""
        
        try:
            response = await self.think([{"role": "user", "content": prompt}])
            
            # 解析AI回复
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
        except Exception as e:
            self.log(f"AI分析产品趋势失败: {e}", "warning")
        
        # 如果AI分析失败，使用规则判断
        product_keywords = ["热销", "爆款", "畅销", "热卖", "销量", "排行", "趋势"]
        has_product_signal = any(kw in title or kw in content for kw in product_keywords)
        
        return {
            "is_valid_product": has_product_signal,
            "product_name": title[:100],
            "category": category,
            "description": content[:300],
            "trend_score": 50 if has_product_signal else 30,
            "analysis": "规则判断",
            "reason": "规则匹配"
        }
    
    async def _notify_coordinator_for_products(self, products: List[Dict], db) -> None:
        """
        通知小调处理产品趋势信息
        1. 存入知识库
        2. 发送邮件通知
        """
        try:
            from sqlalchemy import text
            from app.agents.coordinator import coordinator_agent
            from app.services.email_service import email_service
            
            self.log(f"📤 通知小调处理 {len(products)} 个产品趋势...")
            
            # 准备产品摘要
            product_summary = []
            for p in products:
                summary = f"""
🛒 **{p.get('product_name', '未知产品')}**
- 类别: {p.get('category', '未知')}
- 趋势评分: {p.get('trend_score', 0)}分
- 销量: {p.get('sales_volume', '未知')}
- 价格: {p.get('price_range', '未知')}
- 分析: {p.get('ai_analysis', '暂无')}
- 物流建议: {p.get('ai_logistics_tips', '暂无')}
- 来源: {p.get('source_url', '')}
"""
                product_summary.append(summary)
            
            # 1. 存入知识库（作为市场情报）
            knowledge_content = f"""
# 欧洲跨境电商产品趋势报告

发现时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
发现数量: {len(products)} 个产品

## 产品详情

{''.join(product_summary)}

## 总结

本次发现了 {len(products)} 个欧洲市场热门产品趋势，建议关注高趋势评分的产品，
及时调整物流服务策略，抓住市场机会。
"""
            
            try:
                await db.execute(
                    text("""
                        INSERT INTO knowledge_base 
                        (title, content, category, tags, source, created_at)
                        VALUES 
                        (:title, :content, 'market_intelligence', :tags, 'lead_hunter', NOW())
                    """),
                    {
                        "title": f"欧洲产品趋势报告 - {datetime.now().strftime('%Y-%m-%d')}",
                        "content": knowledge_content,
                        "tags": ["欧洲市场", "产品趋势", "跨境电商", "市场情报"]
                    }
                )
                self.log("✅ 产品趋势已存入知识库")
            except Exception as e:
                self.log(f"存入知识库失败: {e}", "warning")
            
            # 2. 发送邮件通知
            email_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
        .product {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
        .score {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .tips {{ background: #e8f4f8; padding: 10px; border-radius: 5px; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛒 欧洲热门产品趋势报告</h1>
        <p>发现时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>本次共发现 <strong>{len(products)}</strong> 个热门产品趋势</p>
    </div>
    
    <h2>📊 产品详情</h2>
"""
            
            for p in products:
                score = p.get('trend_score', 0)
                score_color = '#28a745' if score >= 70 else '#ffc107' if score >= 50 else '#6c757d'
                
                email_body += f"""
    <div class="product">
        <h3>{p.get('product_name', '未知产品')}</h3>
        <p><strong>类别:</strong> {p.get('category', '未知')}</p>
        <p><strong>趋势评分:</strong> <span class="score" style="color: {score_color}">{score}分</span></p>
        <p><strong>销量情况:</strong> {p.get('sales_volume', '未知')}</p>
        <p><strong>价格区间:</strong> {p.get('price_range', '未知')}</p>
        <p><strong>趋势分析:</strong> {p.get('ai_analysis', '暂无')}</p>
        <div class="tips">
            <strong>💡 物流建议:</strong> {p.get('ai_logistics_tips', '暂无')}
        </div>
        <p><strong>🔗 来源:</strong> <a href="{p.get('source_url', '#')}">{p.get('source_url', '无')}</a></p>
    </div>
"""
            
            email_body += f"""
    <div class="footer">
        <p>此邮件由 <strong>小猎 (Lead Hunter AI)</strong> 自动发送</p>
        <p>产品趋势信息已同步存入知识库，可在系统中查看完整报告</p>
        <p>如有问题请联系系统管理员</p>
    </div>
</body>
</html>
"""
            
            # 发送邮件
            try:
                email_result = await email_service.send_email(
                    to_emails=[getattr(settings, 'BOSS_EMAIL', '18757672416@163.com')],
                    subject=f"🛒 欧洲热门产品趋势报告 - {datetime.now().strftime('%Y-%m-%d')} ({len(products)}个产品)",
                    html_content=email_body
                )
                
                if email_result.get("status") == "sent":
                    self.log("✅ 产品趋势报告邮件已发送")
                    
                    # 更新产品状态为已发送邮件
                    for p in products:
                        if p.get("id"):
                            await db.execute(
                                text("""
                                    UPDATE product_trends 
                                    SET is_email_sent = true, updated_at = NOW()
                                    WHERE id = :id
                                """),
                                {"id": p["id"]}
                            )
                else:
                    self.log(f"发送邮件失败: {email_result.get('error')}", "error")
                    
            except Exception as e:
                self.log(f"发送邮件异常: {e}", "error")
            
            await db.commit()
            
        except Exception as e:
            self.log(f"通知小调处理失败: {e}", "error")
    
    async def _get_product_stats(self) -> Dict[str, Any]:
        """获取产品趋势统计"""
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 总产品数
                total_result = await db.execute(
                    text("SELECT COUNT(*) FROM product_trends")
                )
                total = total_result.scalar() or 0
                
                # 今日新发现
                today_result = await db.execute(
                    text("SELECT COUNT(*) FROM product_trends WHERE DATE(created_at) = CURRENT_DATE")
                )
                today_count = today_result.scalar() or 0
                
                # 高趋势产品数
                high_trend_result = await db.execute(
                    text("SELECT COUNT(*) FROM product_trends WHERE trend_score >= 70")
                )
                high_trend_count = high_trend_result.scalar() or 0
                
                # 已发送邮件数
                emailed_result = await db.execute(
                    text("SELECT COUNT(*) FROM product_trends WHERE is_email_sent = true")
                )
                emailed_count = emailed_result.scalar() or 0
                
                # 按类别统计
                category_result = await db.execute(
                    text("""
                        SELECT category, COUNT(*) 
                        FROM product_trends 
                        GROUP BY category
                        ORDER BY COUNT(*) DESC
                        LIMIT 10
                    """)
                )
                by_category = {row[0]: row[1] for row in category_result.fetchall()}
                
                # 最新发现的产品
                recent_result = await db.execute(
                    text("""
                        SELECT product_name, category, trend_score, source_url, created_at
                        FROM product_trends
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                )
                recent_products = [
                    {
                        "name": row[0],
                        "category": row[1],
                        "score": row[2],
                        "url": row[3],
                        "created_at": row[4].isoformat() if row[4] else None
                    }
                    for row in recent_result.fetchall()
                ]
                
                return {
                    "total": total,
                    "today": today_count,
                    "high_trend": high_trend_count,
                    "emailed": emailed_count,
                    "by_category": by_category,
                    "recent_products": recent_products
                }
                
        except Exception as e:
            self.log(f"获取产品趋势统计失败: {e}", "error")
            return {"error": str(e)}


# 注册Agent
lead_hunter_agent = LeadHunterAgent()
AgentRegistry.register(lead_hunter_agent)
