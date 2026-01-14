"""
小猎 - 线索猎手
负责自动在互联网上搜索潜在客户线索
"""
from typing import Dict, Any, List, Optional
import json
import re
import asyncio
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
    SEARCH_KEYWORDS_CN = [
        "找货代", "货代推荐", "物流报价",
        "跨境物流", "FBA物流", "海运询价",
        "国际快递", "空运报价", "找物流公司",
        "货代哪家好", "物流服务", "清关服务"
    ]
    
    SEARCH_KEYWORDS_EN = [
        "freight forwarder needed", "looking for logistics",
        "shipping quote", "FBA shipping", "sea freight",
        "air cargo quote", "customs clearance",
        "logistics company recommend"
    ]
    
    # 线索质量判断关键词
    HIGH_INTENT_KEYWORDS = [
        "急", "马上", "尽快", "报价", "价格", "多少钱",
        "urgent", "asap", "quote", "price", "how much"
    ]
    
    def _build_system_prompt(self) -> str:
        return """你是小猎，一位专业的线索猎手。你的任务是分析互联网上的内容，判断是否是潜在的物流客户线索。

分析时请考虑：
1. 是否有物流/货代需求
2. 需求的紧迫程度
3. 是否是真实需求（排除广告、竞争对手）
4. 潜在价值大小

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
        完整的线索狩猎流程
        """
        self.log("开始线索狩猎任务...")
        
        results = {
            "hunt_time": datetime.now().isoformat(),
            "sources_searched": [],
            "leads_found": [],
            "total_leads": 0,
            "high_intent_leads": 0
        }
        
        # 搜索各个来源
        sources = [
            ("weibo", self._search_weibo),
            ("zhihu", self._search_zhihu),
            ("tieba", self._search_tieba),
            ("google", self._search_google),
        ]
        
        for source_name, search_func in sources:
            try:
                self.log(f"搜索来源: {source_name}")
                leads = await search_func()
                results["sources_searched"].append(source_name)
                
                for lead in leads:
                    # 分析每个潜在线索
                    analysis = await self._analyze_content({
                        "content": lead.get("content", ""),
                        "source": source_name,
                        "url": lead.get("url", "")
                    })
                    
                    if analysis.get("is_lead"):
                        lead_data = {
                            **lead,
                            **analysis,
                            "source": source_name,
                            "found_at": datetime.now().isoformat()
                        }
                        results["leads_found"].append(lead_data)
                        results["total_leads"] += 1
                        
                        if analysis.get("intent_level") == "high":
                            results["high_intent_leads"] += 1
                            
            except Exception as e:
                self.log(f"搜索 {source_name} 失败: {e}", "error")
        
        self.log(f"线索狩猎完成！找到 {results['total_leads']} 条线索，其中高意向 {results['high_intent_leads']} 条")
        
        return results
    
    async def _analyze_content(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用AI分析内容是否是潜在客户
        """
        content = input_data.get("content", "")
        source = input_data.get("source", "unknown")
        
        if not content:
            return {"is_lead": False, "reason": "内容为空"}
        
        # 先用规则快速过滤
        if self._quick_filter(content):
            return {"is_lead": False, "reason": "被快速过滤"}
        
        # 用AI深度分析
        prompt = f"""请分析以下内容是否是潜在的物流客户线索：

来源：{source}
内容：{content}

请以JSON格式返回分析结果。"""
        
        response = await self.think([{"role": "user", "content": prompt}])
        
        # 解析AI回复
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
        except json.JSONDecodeError:
            pass
        
        # 解析失败，返回默认结果
        return {
            "is_lead": False,
            "confidence": 0,
            "reason": "AI分析失败"
        }
    
    def _quick_filter(self, content: str) -> bool:
        """
        快速过滤明显不是线索的内容
        """
        # 过滤广告
        ad_keywords = ["加盟", "招商", "代理", "免费试用", "限时优惠"]
        for kw in ad_keywords:
            if kw in content:
                return True
        
        # 过滤太短的内容
        if len(content) < 10:
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
            "qq": ""
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
            r'V[：:]\s*([a-zA-Z0-9_-]+)'
        ]
        for pattern in wechat_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                contact["wechat"] = match.group(1)
                break
        
        # 提取QQ
        qq_pattern = r'QQ[：:]\s*(\d{5,12})'
        qq_match = re.search(qq_pattern, content, re.IGNORECASE)
        if qq_match:
            contact["qq"] = qq_match.group(1)
        
        return contact
    
    async def _search_weibo(self) -> List[Dict[str, Any]]:
        """
        搜索微博上的线索
        TODO: 实现微博API或爬虫
        """
        # 示例返回，实际需要实现爬虫
        self.log("微博搜索 - 需要配置微博API")
        return []
    
    async def _search_zhihu(self) -> List[Dict[str, Any]]:
        """
        搜索知乎上的线索
        TODO: 实现知乎搜索
        """
        self.log("知乎搜索 - 需要配置知乎爬虫")
        return []
    
    async def _search_tieba(self) -> List[Dict[str, Any]]:
        """
        搜索贴吧上的线索
        TODO: 实现贴吧搜索
        """
        self.log("贴吧搜索 - 需要配置贴吧爬虫")
        return []
    
    async def _search_google(self) -> List[Dict[str, Any]]:
        """
        使用Google搜索线索
        TODO: 实现Google Custom Search API
        """
        self.log("Google搜索 - 需要配置Google API")
        return []
    
    async def search_with_serper(self, query: str) -> List[Dict[str, Any]]:
        """
        使用Serper API搜索（Google搜索API替代方案）
        需要配置 SERPER_API_KEY
        """
        import httpx
        
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            self.log("Serper API未配置", "warning")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key},
                    json={"q": query, "gl": "cn", "hl": "zh-cn"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for item in data.get("organic", []):
                        results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet", ""),
                            "url": item.get("link", ""),
                            "source": "google"
                        })
                    
                    return results
        except Exception as e:
            self.log(f"Serper搜索失败: {e}", "error")
        
        return []


# 注册Agent
lead_hunter_agent = LeadHunterAgent()
AgentRegistry.register(lead_hunter_agent)
