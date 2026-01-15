"""
小猎 - 线索猎手
负责自动在互联网上搜索潜在客户线索
"""
from typing import Dict, Any, List, Optional
import json
import re
import asyncio
import httpx
from datetime import datetime
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings


class LeadHunterAgent(BaseAgent):
    """小猎 - 线索猎手"""
    
    name = "小猎"
    agent_type = AgentType.LEAD_HUNTER
    description = "线索猎手 - 自动搜索互联网上的潜在客户线索"
    
    # 搜索关键词配置
    SEARCH_KEYWORDS = [
        "找货代", "货代推荐", "物流报价",
        "跨境物流", "FBA物流", "海运询价",
        "国际快递", "空运报价", "找物流公司",
        "货代哪家好", "物流服务", "清关服务",
        "求推荐货代", "物流怎么选", "发货到美国",
        "发货到欧洲", "亚马逊物流", "跨境电商物流"
    ]
    
    # 线索质量判断关键词
    HIGH_INTENT_KEYWORDS = [
        "急", "马上", "尽快", "报价", "价格", "多少钱",
        "立即", "今天", "明天", "这周", "想发", "要发",
        "urgent", "asap", "quote", "price", "how much"
    ]
    
    # 广告过滤关键词
    AD_FILTER_KEYWORDS = [
        "加盟", "招商", "代理", "免费试用", "限时优惠",
        "欢迎咨询", "专业物流", "我司", "我们公司",
        "联系电话", "点击咨询", "在线客服"
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
                "action": "search" | "analyze" | "hunt",
                "source": "搜索来源",
                "content": "要分析的内容",
                "keywords": ["自定义关键词"]
            }
        """
        action = input_data.get("action", "hunt")
        
        if action == "search":
            return await self._search_leads(input_data)
        elif action == "analyze":
            return await self._analyze_content(input_data)
        elif action == "hunt":
            return await self._full_hunt(input_data)
        else:
            return {"error": f"未知操作: {action}"}
    
    async def _full_hunt(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整的线索狩猎流程 - 使用Serper API搜索
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
        keywords = input_data.get("keywords", self.SEARCH_KEYWORDS[:6])  # 默认用前6个关键词
        
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
            "我司专业", "本公司专业", "欢迎来电"
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
        keywords = input_data.get("keywords", self.SEARCH_KEYWORDS[:3])
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


# 注册Agent
lead_hunter_agent = LeadHunterAgent()
AgentRegistry.register(lead_hunter_agent)
