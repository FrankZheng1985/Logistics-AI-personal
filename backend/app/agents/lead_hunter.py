"""
小猎 - 线索猎手 (24小时智能版)
负责自动在互联网上搜索潜在客户线索
支持：
- 24小时不间断搜索
- 智能关键词轮换
- 搜索效果追踪
- URL去重
- 自动优化搜索策略
"""
from typing import Dict, Any, List, Optional
import json
import re
import asyncio
import httpx
import hashlib
from datetime import datetime, timedelta
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings


class LeadHunterAgent(BaseAgent):
    """小猎 - 线索猎手 (24小时智能版)"""
    
    name = "小猎"
    agent_type = AgentType.LEAD_HUNTER
    description = "线索猎手 - 24小时自动搜索互联网上的潜在客户线索"
    
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
        return """你是小猎，一位专业的线索猎手。你的任务是分析互联网上的内容，判断是否是潜在的物流客户线索。

分析时请考虑：
1. 是否有物流/货代需求（排除物流公司的广告和推广）
2. 需求的紧迫程度
3. 是否是真实的客户需求（不是物流公司发的）
4. 潜在价值大小

判断规则：
- 如果内容是物流公司的广告、推广、招商，返回 is_lead: false
- 如果内容是个人或企业在寻找物流服务，返回 is_lead: true
- 如果内容包含具体的发货需求（如目的地、货物类型、重量），提高意向等级

输出格式（JSON）：
{
    "is_lead": true/false,
    "confidence": 0-100,
    "intent_level": "high/medium/low",
    "lead_type": "个人/企业/电商卖家/外贸公司",
    "needs": ["海运", "空运", "清关", "FBA"],
    "contact_info": {
        "name": "",
        "phone": "",
        "email": "",
        "wechat": "",
        "company": ""
    },
    "summary": "简短描述这个线索",
    "follow_up_suggestion": "跟进建议"
}
"""
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理线索搜索任务
        
        Args:
            input_data: {
                "action": "search" | "analyze" | "hunt" | "smart_hunt",
                "source": "搜索来源",
                "content": "要分析的内容",
                "keywords": ["自定义关键词"],
                "max_keywords": 最大关键词数量,
                "max_results": 最大结果数量
            }
        """
        action = input_data.get("action", "smart_hunt")
        
        if action == "search":
            return await self._search_leads(input_data)
        elif action == "analyze":
            return await self._analyze_content(input_data)
        elif action == "hunt":
            return await self._full_hunt(input_data)
        elif action == "smart_hunt":
            return await self._smart_hunt(input_data)
        elif action == "get_stats":
            return await self._get_hunt_stats()
        else:
            return {"error": f"未知操作: {action}"}
    
    async def _smart_hunt(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        智能线索狩猎 - 24小时自动运行版本
        - 自动从数据库获取待搜索关键词
        - 智能选择搜索平台
        - 自动去重和记录
        - 追踪搜索效果
        """
        self.log("🎯 开始智能线索狩猎任务...")
        start_time = datetime.now()
        
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
                
                # 3. 分析每个搜索结果
                max_results = input_data.get("max_results", 30)
                keyword_stats = {}  # 记录每个关键词的效果
                
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
                        
                        # AI深度分析
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
                            
                            # 保存线索到数据库
                            lead_insert = await db.execute(
                                text("""
                                    INSERT INTO leads 
                                    (source, source_url, source_content, content, 
                                     ai_confidence, intent_level, ai_summary, ai_suggestion,
                                     needs, status, created_at)
                                    VALUES (:source, :url, :raw_content, :content, 
                                            :confidence, :level, :summary, :suggestion,
                                            :needs, 'new', NOW())
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
                                    "needs": analysis.get("needs", [])
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
        """
        self.log("开始线索狩猎任务...")
        
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
    
    async def _search_with_serper(self, query: str) -> List[Dict[str, Any]]:
        """
        使用Serper API搜索
        """
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "gl": "cn",
                        "hl": "zh-cn",
                        "num": 10
                    }
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
    async def search_with_serper(self, query: str) -> List[Dict[str, Any]]:
        """公开的Serper搜索方法"""
        return await self._search_with_serper(query)
    
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
        
        # 用AI深度分析
        prompt = f"""请分析以下内容是否是潜在的物流客户线索：

来源平台：{source}
URL：{url}
内容：{content}

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


# 注册Agent
lead_hunter_agent = LeadHunterAgent()
AgentRegistry.register(lead_hunter_agent)
