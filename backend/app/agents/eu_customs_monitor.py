"""
小欧间谍 - 欧洲海关监控员
负责每天监控欧洲海关相关新闻，关注第三国进口欧洲的政策变化
重点关键词：反倾销、进口配额、关税调整、欧洲偷税、欧洲洗黑钱等
"""
import json
import hashlib
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import httpx

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings


class EUCustomsMonitorAgent(BaseAgent):
    """小欧间谍 - 欧洲海关监控员"""
    
    name = "小欧间谍"
    agent_type = AgentType.EU_CUSTOMS_MONITOR
    description = "欧洲海关监控员 - 每天监控欧洲海关新闻，关注反倾销、关税调整、进口政策等"
    
    # 监控关键词（中文）
    MONITOR_KEYWORDS_CN = [
        # 核心关键词
        "欧盟反倾销",
        "欧洲进口配额",
        "欧盟关税调整",
        "欧洲偷税",
        "欧洲洗黑钱",
        # 政策类
        "欧盟海关政策",
        "欧盟进口新规",
        "欧洲清关政策",
        "欧盟VAT新规",
        "欧洲关税壁垒",
        # 国家/地区
        "德国海关",
        "法国海关",
        "英国海关",
        "荷兰海关",
        "意大利海关",
        # 第三国相关
        "中国商品 欧盟",
        "第三国进口 欧洲",
        "中欧贸易",
        "对华关税",
        # 行业影响
        "欧洲物流政策",
        "欧盟电商法规",
        "跨境电商 欧洲新规",
    ]
    
    # 监控关键词（英文，用于搜索国际新闻）
    MONITOR_KEYWORDS_EN = [
        "EU anti-dumping",
        "European customs policy",
        "EU import quota",
        "EU tariff changes",
        "European Commission trade",
        "EU customs regulation",
        "third country import EU",
    ]
    
    # 新闻来源配置
    NEWS_SOURCES = {
        "eu_official": {
            "name": "欧盟官方",
            "site_filter": "site:ec.europa.eu OR site:europa.eu",
            "keywords": MONITOR_KEYWORDS_EN,
            "weight": 5  # 权重最高
        },
        "china_mofcom": {
            "name": "中国商务部",
            "site_filter": "site:mofcom.gov.cn",
            "keywords": ["欧盟", "欧洲", "反倾销", "关税"],
            "weight": 4
        },
        "customs_news": {
            "name": "海关新闻",
            "site_filter": "site:customs.gov.cn OR site:chinaports.com",
            "keywords": ["欧洲", "欧盟", "进口"],
            "weight": 3
        },
        "industry_media": {
            "name": "行业媒体",
            "site_filter": "site:56ec.com OR site:wuliu.com.cn OR site:chinawuliu.com.cn",
            "keywords": ["欧洲", "欧盟", "清关", "关税"],
            "weight": 3
        },
        "google_general": {
            "name": "综合搜索",
            "site_filter": "",
            "keywords": MONITOR_KEYWORDS_CN[:10],  # 使用前10个核心关键词
            "weight": 2
        }
    }
    
    # 重要性判断关键词（出现这些词的新闻更重要）
    IMPORTANCE_KEYWORDS = [
        "紧急", "重大", "突发", "立即生效", "新规实施",
        "反倾销税", "惩罚性关税", "禁止进口", "暂停进口",
        "调查", "制裁", "处罚", "罚款", "查获", "走私",
        "urgent", "breaking", "new regulation", "immediate effect"
    ]
    
    def _build_system_prompt(self) -> str:
        return """你是小欧间谍，一位专业的欧洲海关情报分析员。

你的工作是分析欧洲海关相关新闻，判断其对物流行业的重要性和影响。

分析维度：
1. 新闻类型：政策变化/反倾销措施/关税调整/执法行动/行业动态
2. 影响范围：涉及哪些国家、哪些商品类别
3. 紧急程度：是否需要立即关注和采取行动
4. 对物流业务的影响：清关、运费、时效等方面

输出要求：
- 所有内容必须使用中文输出
- 如果原文是英文，请翻译成中文
- 提供简洁明了的分析摘要
- 给出具体的业务建议

输出格式（JSON）：
{
    "is_important": true/false,
    "importance_score": 0-100,
    "news_type": "政策变化/反倾销/关税调整/执法行动/行业动态",
    "title_cn": "中文标题",
    "summary_cn": "中文摘要（100字以内）",
    "affected_countries": ["涉及国家"],
    "affected_products": ["涉及商品类别"],
    "impact_analysis": "对物流业务的影响分析",
    "business_suggestion": "业务建议",
    "urgency": "紧急/重要/一般"
}
"""
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理欧洲海关新闻监控任务
        
        Args:
            input_data: {
                "action": "monitor" | "search" | "analyze" | "get_stats",
                "keywords": ["自定义关键词"],  # 可选
                "sources": ["news_source_ids"],  # 可选
                "max_results": 最大结果数量  # 可选
            }
        """
        action = input_data.get("action", "monitor")
        
        # 开始任务会话（实时直播）
        await self.start_task_session(action, f"欧洲海关新闻监控: {action}")
        
        try:
            if action == "monitor":
                # 完整的监控流程
                result = await self._full_monitor(input_data)
            elif action == "search":
                # 仅搜索，不分析
                result = await self._search_news(input_data)
            elif action == "analyze":
                # 分析单条新闻
                result = await self._analyze_single_news(input_data)
            elif action == "get_stats":
                # 获取统计信息
                result = await self._get_monitor_stats()
            else:
                result = {"error": f"未知操作: {action}"}
            
            await self.end_task_session(f"完成{action}任务")
            return result
        except Exception as e:
            await self.end_task_session(error_message=str(e))
            raise
    
    async def _full_monitor(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整的监控流程：搜索 -> 分析 -> 存储 -> 通知
        """
        self.log("🔍 开始欧洲海关新闻监控...")
        start_time = datetime.now()
        
        # 检查API配置
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            self.log("Serper API未配置，无法进行搜索", "error")
            await self.log_error("Serper API未配置", "请在系统设置中配置API密钥")
            return {
                "error": "搜索API未配置",
                "message": "请在系统设置中配置 SERPER_API_KEY 以启用新闻监控功能"
            }
        
        results = {
            "monitor_time": datetime.now().isoformat(),
            "sources_searched": [],
            "news_found": [],
            "important_news": [],
            "total_news": 0,
            "important_count": 0,
            "notification_sent": False
        }
        
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                all_news = []
                
                # 1. 从各个来源搜索新闻
                for source_id, source_config in self.NEWS_SOURCES.items():
                    source_name = source_config["name"]
                    site_filter = source_config["site_filter"]
                    keywords = source_config.get("keywords", self.MONITOR_KEYWORDS_CN[:5])
                    
                    await self.log_live_step("search", f"搜索{source_name}新闻", f"来源: {source_id}")
                    
                    for keyword in keywords[:3]:  # 每个来源使用前3个关键词
                        try:
                            query = f"{keyword} {site_filter}".strip()
                            self.log(f"🔍 搜索: {query}")
                            
                            search_results = await self._search_with_serper(query)
                            
                            if search_results:
                                results["sources_searched"].append(source_name)
                                for item in search_results[:5]:  # 每个关键词取前5条
                                    url = item.get("url", "")
                                    if not url:
                                        continue
                                    
                                    # 检查是否已存在
                                    url_hash = hashlib.md5(url.encode()).hexdigest()
                                    existing = await db.execute(
                                        text("SELECT id FROM eu_customs_news WHERE url_hash = :hash"),
                                        {"hash": url_hash}
                                    )
                                    if existing.fetchone():
                                        continue
                                    
                                    item["source_id"] = source_id
                                    item["source_name"] = source_name
                                    item["keyword"] = keyword
                                    item["url_hash"] = url_hash
                                    all_news.append(item)
                            
                            # 控制请求频率
                            await asyncio.sleep(0.3)
                            
                        except Exception as e:
                            self.log(f"搜索失败 ({source_name}, {keyword}): {e}", "error")
                
                self.log(f"📰 获取 {len(all_news)} 条新URL待分析")
                await self.log_live_step("info", f"获取 {len(all_news)} 条新闻", "开始AI分析")
                
                # 2. AI分析每条新闻
                max_analyze = input_data.get("max_results", 30)
                
                for item in all_news[:max_analyze]:
                    try:
                        title = item.get("title", "")
                        content = item.get("content", item.get("snippet", ""))
                        url = item.get("url", "")
                        url_hash = item.get("url_hash", "")
                        
                        # 记录正在分析
                        await self.log_fetch(url, title, {"source": item.get("source_name")})
                        
                        # AI分析新闻重要性
                        await self.log_think("分析新闻重要性和影响", title[:50])
                        analysis = await self._analyze_news_importance({
                            "title": title,
                            "content": content,
                            "url": url,
                            "source": item.get("source_name", "")
                        })
                        
                        is_important = analysis.get("is_important", False)
                        importance_score = analysis.get("importance_score", 0)
                        
                        # 构建新闻数据
                        news_data = {
                            "title": title,
                            "title_cn": analysis.get("title_cn", title),
                            "content": content,
                            "summary_cn": analysis.get("summary_cn", ""),
                            "url": url,
                            "url_hash": url_hash,
                            "source_id": item.get("source_id", ""),
                            "source_name": item.get("source_name", ""),
                            "keyword": item.get("keyword", ""),
                            "news_type": analysis.get("news_type", "行业动态"),
                            "importance_score": importance_score,
                            "is_important": is_important,
                            "urgency": analysis.get("urgency", "一般"),
                            "affected_countries": analysis.get("affected_countries", []),
                            "affected_products": analysis.get("affected_products", []),
                            "impact_analysis": analysis.get("impact_analysis", ""),
                            "business_suggestion": analysis.get("business_suggestion", ""),
                            "collected_at": datetime.now().isoformat()
                        }
                        
                        results["news_found"].append(news_data)
                        results["total_news"] += 1
                        
                        if is_important:
                            results["important_news"].append(news_data)
                            results["important_count"] += 1
                            await self.log_result(
                                f"🚨 发现重要新闻!",
                                f"{analysis.get('title_cn', title)[:50]}",
                                {"importance_score": importance_score, "urgency": analysis.get("urgency")}
                            )
                        
                        # 保存到数据库
                        await db.execute(
                            text("""
                                INSERT INTO eu_customs_news 
                                (title, title_cn, content, summary_cn, url, url_hash,
                                 source_id, source_name, keyword, news_type,
                                 importance_score, is_important, urgency,
                                 affected_countries, affected_products,
                                 impact_analysis, business_suggestion, created_at)
                                VALUES 
                                (:title, :title_cn, :content, :summary_cn, :url, :url_hash,
                                 :source_id, :source_name, :keyword, :news_type,
                                 :importance_score, :is_important, :urgency,
                                 :affected_countries, :affected_products,
                                 :impact_analysis, :business_suggestion, NOW())
                                ON CONFLICT (url_hash) DO NOTHING
                            """),
                            {
                                "title": news_data["title"],
                                "title_cn": news_data["title_cn"],
                                "content": news_data["content"][:2000],  # 限制长度
                                "summary_cn": news_data["summary_cn"],
                                "url": news_data["url"],
                                "url_hash": news_data["url_hash"],
                                "source_id": news_data["source_id"],
                                "source_name": news_data["source_name"],
                                "keyword": news_data["keyword"],
                                "news_type": news_data["news_type"],
                                "importance_score": news_data["importance_score"],
                                "is_important": news_data["is_important"],
                                "urgency": news_data["urgency"],
                                "affected_countries": news_data["affected_countries"],
                                "affected_products": news_data["affected_products"],
                                "impact_analysis": news_data["impact_analysis"],
                                "business_suggestion": news_data["business_suggestion"]
                            }
                        )
                        
                    except Exception as e:
                        self.log(f"分析新闻失败: {e}", "error")
                
                await db.commit()
                
                # 3. 更新AI员工任务统计
                await db.execute(
                    text("""
                        UPDATE ai_agents
                        SET tasks_completed_today = tasks_completed_today + 1,
                            total_tasks_completed = total_tasks_completed + 1,
                            last_active_at = NOW()
                        WHERE agent_type = 'eu_customs_monitor'
                    """)
                )
                await db.commit()
                
                # 4. 发送企业微信通知（如果有重要新闻）
                if results["important_news"]:
                    notification_result = await self._send_wechat_notification(results["important_news"])
                    results["notification_sent"] = notification_result.get("success", False)
                
        except Exception as e:
            self.log(f"监控任务出错: {e}", "error")
            results["error"] = str(e)
            await self.log_error(str(e), "监控任务出错")
        
        # 去重sources
        results["sources_searched"] = list(set(results["sources_searched"]))
        
        duration = (datetime.now() - start_time).total_seconds()
        results["duration_seconds"] = round(duration, 2)
        
        self.log(f"✅ 监控完成！耗时{duration:.1f}秒，发现 {results['total_news']} 条新闻，"
                 f"重要新闻 {results['important_count']} 条")
        
        return results
    
    async def _search_with_serper(self, query: str) -> List[Dict[str, Any]]:
        """使用Serper API搜索新闻"""
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 使用新闻搜索API
                response = await client.post(
                    "https://google.serper.dev/news",
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "gl": "cn",
                        "hl": "zh-cn",
                        "num": 10,
                        "tbs": "qdr:w"  # 过去一周的新闻
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for item in data.get("news", []):
                        results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet", ""),
                            "url": item.get("link", ""),
                            "date": item.get("date", ""),
                            "source": item.get("source", "")
                        })
                    
                    return results
                else:
                    self.log(f"Serper API返回错误: {response.status_code}", "error")
                    
        except Exception as e:
            self.log(f"Serper搜索异常: {e}", "error")
        
        return []
    
    async def _analyze_news_importance(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI分析新闻重要性"""
        title = input_data.get("title", "")
        content = input_data.get("content", "")
        url = input_data.get("url", "")
        source = input_data.get("source", "")
        
        if not title:
            return {"is_important": False, "reason": "标题为空"}
        
        # 快速判断：检查是否包含重要性关键词
        combined_text = f"{title} {content}".lower()
        has_importance_keyword = any(kw.lower() in combined_text for kw in self.IMPORTANCE_KEYWORDS)
        
        # 使用AI深度分析
        prompt = f"""请分析以下欧洲海关相关新闻的重要性：

来源：{source}
标题：{title}
内容：{content[:500]}
URL：{url}

请从以下角度分析：
1. 这是什么类型的新闻？（政策变化/反倾销/关税调整/执法行动/行业动态）
2. 对物流行业有什么影响？
3. 需要立即关注吗？

请以JSON格式返回分析结果，所有内容必须使用中文。"""
        
        try:
            response = await self.think([{"role": "user", "content": prompt}], temperature=0.3)
            
            # 解析AI回复
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                
                # 如果有重要性关键词，提升分数
                if has_importance_keyword and result.get("importance_score", 0) < 70:
                    result["importance_score"] = min(result.get("importance_score", 50) + 20, 100)
                    if not result.get("is_important"):
                        result["is_important"] = result.get("importance_score", 0) >= 60
                
                return result
        except json.JSONDecodeError:
            self.log("AI分析结果解析失败", "warning")
        except Exception as e:
            self.log(f"AI分析异常: {e}", "error")
        
        # 如果AI分析失败，使用规则判断
        return self._rule_based_importance(title, content, has_importance_keyword)
    
    def _rule_based_importance(self, title: str, content: str, has_importance_keyword: bool) -> Dict[str, Any]:
        """基于规则的重要性判断（AI失败时的备选）"""
        importance_score = 30  # 基础分
        
        # 检查标题中的关键词
        title_keywords = ["反倾销", "关税", "新规", "政策", "禁止", "处罚", "调查"]
        title_matches = sum(1 for kw in title_keywords if kw in title)
        importance_score += title_matches * 15
        
        if has_importance_keyword:
            importance_score += 20
        
        # 检查内容中的关键词
        content_keywords = ["生效", "实施", "通知", "公告", "决定"]
        content_matches = sum(1 for kw in content_keywords if kw in content)
        importance_score += content_matches * 10
        
        importance_score = min(importance_score, 100)
        
        return {
            "is_important": importance_score >= 60,
            "importance_score": importance_score,
            "news_type": "行业动态",
            "title_cn": title,
            "summary_cn": content[:100] if content else "",
            "affected_countries": [],
            "affected_products": [],
            "impact_analysis": "需要进一步分析",
            "business_suggestion": "建议关注后续发展",
            "urgency": "重要" if importance_score >= 70 else "一般"
        }
    
    async def _send_wechat_notification(self, important_news: List[Dict[str, Any]]) -> Dict[str, Any]:
        """发送企业微信通知"""
        try:
            from app.services.notification import notification_service
            
            # 构建通知内容
            today = datetime.now().strftime("%Y年%m月%d日")
            
            content = f"""🔔 【欧洲海关情报日报】{today}

━━━━━━━━━━━━━━━━━━━━

📊 今日发现 {len(important_news)} 条重要新闻：

"""
            
            for i, news in enumerate(important_news[:5], 1):  # 最多显示5条
                urgency_emoji = "🚨" if news.get("urgency") == "紧急" else "⚠️" if news.get("urgency") == "重要" else "📌"
                content += f"""{urgency_emoji} {i}. {news.get('title_cn', news.get('title', ''))[:50]}
   类型：{news.get('news_type', '未知')} | 重要度：{news.get('importance_score', 0)}分
   摘要：{news.get('summary_cn', '')[:80]}...
   建议：{news.get('business_suggestion', '暂无')[:50]}

"""
            
            if len(important_news) > 5:
                content += f"... 还有 {len(important_news) - 5} 条重要新闻，请登录系统查看\n\n"
            
            content += """━━━━━━━━━━━━━━━━━━━━
由小欧间谍自动监控 | 物流获客AI"""
            
            # 发送通知
            await notification_service.send_to_boss(
                title=f"🔔 欧洲海关情报日报 {today}",
                content=content
            )
            
            self.log("✅ 企业微信通知已发送")
            return {"success": True}
            
        except Exception as e:
            self.log(f"发送企业微信通知失败: {e}", "error")
            return {"success": False, "error": str(e)}
    
    async def _search_news(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """仅搜索新闻，不做分析"""
        keywords = input_data.get("keywords", self.MONITOR_KEYWORDS_CN[:5])
        sources = input_data.get("sources", list(self.NEWS_SOURCES.keys()))
        
        all_results = []
        
        for source_id in sources:
            if source_id not in self.NEWS_SOURCES:
                continue
            
            source_config = self.NEWS_SOURCES[source_id]
            site_filter = source_config["site_filter"]
            
            for keyword in keywords[:3]:
                query = f"{keyword} {site_filter}".strip()
                results = await self._search_with_serper(query)
                
                for item in results:
                    item["source_id"] = source_id
                    item["source_name"] = source_config["name"]
                    item["keyword"] = keyword
                    all_results.append(item)
                
                await asyncio.sleep(0.3)
        
        return {
            "search_time": datetime.now().isoformat(),
            "results": all_results,
            "count": len(all_results)
        }
    
    async def _analyze_single_news(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析单条新闻"""
        return await self._analyze_news_importance(input_data)
    
    async def _get_monitor_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        try:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                # 今日统计
                today_result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE is_important = true) as important,
                            AVG(importance_score) as avg_score
                        FROM eu_customs_news
                        WHERE DATE(created_at) = CURRENT_DATE
                    """)
                )
                today = today_result.fetchone()
                
                # 本周统计
                week_result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE is_important = true) as important
                        FROM eu_customs_news
                        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                    """)
                )
                week = week_result.fetchone()
                
                # 按类型统计
                type_result = await db.execute(
                    text("""
                        SELECT news_type, COUNT(*) as count
                        FROM eu_customs_news
                        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                        GROUP BY news_type
                        ORDER BY count DESC
                    """)
                )
                by_type = {row[0]: row[1] for row in type_result.fetchall()}
                
                # 最近的重要新闻
                recent_result = await db.execute(
                    text("""
                        SELECT title_cn, news_type, importance_score, urgency, created_at
                        FROM eu_customs_news
                        WHERE is_important = true
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                )
                recent_important = [
                    {
                        "title": row[0],
                        "type": row[1],
                        "score": row[2],
                        "urgency": row[3],
                        "time": row[4].isoformat() if row[4] else None
                    }
                    for row in recent_result.fetchall()
                ]
                
                return {
                    "today": {
                        "total": today[0] if today else 0,
                        "important": today[1] if today else 0,
                        "avg_score": round(today[2], 1) if today and today[2] else 0
                    },
                    "this_week": {
                        "total": week[0] if week else 0,
                        "important": week[1] if week else 0
                    },
                    "by_type": by_type,
                    "recent_important": recent_important
                }
                
        except Exception as e:
            self.log(f"获取统计失败: {e}", "error")
            return {"error": str(e)}


# 创建单例并注册
eu_customs_monitor_agent = EUCustomsMonitorAgent()
AgentRegistry.register(eu_customs_monitor_agent)
