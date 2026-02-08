"""
小析2 - 微信群情报员
负责监控微信群消息，提取有价值信息，更新知识库
注意：小析2只监控不发言
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings
from app.core.prompts.analyst2 import ANALYST2_SYSTEM_PROMPT


class Analyst2Agent(BaseAgent):
    """小析2 - 微信群情报员"""
    
    name = "小析2"
    agent_type = AgentType.ANALYST2
    description = "微信群情报员 - 静默监控微信群，提取有价值信息"
    
    # 关注的关键词（欧洲物流业务相关）
    MONITOR_KEYWORDS = {
        "线索类": [
            "找货代", "找物流", "询价", "报价", "多少钱",
            "欧洲", "德国", "法国", "英国", "荷兰", "意大利",
            "清关", "派送", "到门", "FBA", "海外仓"
        ],
        "情报类": [
            "运价", "价格", "涨价", "降价", "费率",
            "政策", "新规", "VAT", "关税", "海关",
            "港口", "拥堵", "延误", "罢工"
        ],
        "知识类": [
            "经验", "技巧", "注意", "建议", "分享",
            "清关流程", "时效", "多久", "需要什么"
        ]
    }
    
    # 过滤关键词（广告、无关内容）
    FILTER_KEYWORDS = [
        "加盟", "招商", "代理", "免费", "优惠券",
        "红包", "抢购", "限时", "促销", "打折"
    ]
    
    def _build_system_prompt(self) -> str:
        return ANALYST2_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理微信群消息
        
        Args:
            input_data: {
                "group_id": "群ID",
                "group_name": "群名称",
                "sender_name": "发送者名称",
                "content": "消息内容",
                "message_type": "text/image/file"
            }
        """
        group_id = input_data.get("group_id", "")
        group_name = input_data.get("group_name", "")
        sender_name = input_data.get("sender_name", "")
        content = input_data.get("content", "")
        message_type = input_data.get("message_type", "text")
        
        # 只处理文本消息
        if message_type != "text" or not content:
            return {
                "is_valuable": False,
                "category": "irrelevant",
                "reason": "非文本消息或内容为空"
            }
        
        # 快速过滤
        if self._quick_filter(content):
            return {
                "is_valuable": False,
                "category": "irrelevant",
                "reason": "被快速过滤（广告/无关）"
            }
        
        # 关键词初步判断
        keyword_result = self._keyword_check(content)
        
        # 如果没有匹配任何关键词，可能价值不高
        if not keyword_result["matched"]:
            return {
                "is_valuable": False,
                "category": "irrelevant",
                "reason": "未匹配关键词"
            }
        
        # 开始任务会话（实时直播）- 只对需要AI分析的消息启动
        await self.start_task_session("wechat_analyze", f"分析群消息: {group_name}")
        
        try:
            await self.log_live_step("analyze", "开始AI深度分析", f"来自: {sender_name}")
            
            # 使用AI进行深度分析
            analysis = await self._ai_analyze(content, group_name, sender_name)
            
            # 提取联系方式
            contact_info = self._extract_contact_info(content)
            if contact_info:
                analysis["key_info"] = analysis.get("key_info", {})
                analysis["key_info"]["contact_info"] = contact_info
                await self.log_live_step("result", "提取到联系方式", str(contact_info))
            
            # 添加元数据
            analysis["group_id"] = group_id
            analysis["group_name"] = group_name
            analysis["sender_name"] = sender_name
            analysis["keyword_matches"] = keyword_result["keywords"]
            analysis["analyzed_at"] = datetime.now().isoformat()
            
            # 记录日志
            if analysis.get("is_valuable"):
                self.log(f"发现有价值信息: [{group_name}] {analysis.get('category')} - {analysis.get('summary', '')[:50]}")
                await self.log_live_step("result", "发现有价值信息", f"{analysis.get('category')}: {analysis.get('summary', '')[:50]}")
            
            await self.end_task_session(f"完成消息分析: {'有价值' if analysis.get('is_valuable') else '无价值'}")
            return analysis
        except Exception as e:
            await self.end_task_session(error_message=str(e))
            raise
    
    def _quick_filter(self, content: str) -> bool:
        """快速过滤明显无关的内容"""
        # 太短的内容
        if len(content) < 5:
            return True
        
        # 包含过滤关键词
        for kw in self.FILTER_KEYWORDS:
            if kw in content:
                return True
        
        # 纯表情/纯数字
        if re.match(r'^[\d\s\[\]]+$', content):
            return True
        
        return False
    
    def _keyword_check(self, content: str) -> Dict[str, Any]:
        """关键词检查"""
        matched_keywords = []
        matched_categories = set()
        
        for category, keywords in self.MONITOR_KEYWORDS.items():
            for kw in keywords:
                if kw in content:
                    matched_keywords.append(kw)
                    matched_categories.add(category)
        
        return {
            "matched": len(matched_keywords) > 0,
            "keywords": matched_keywords,
            "categories": list(matched_categories)
        }
    
    async def _ai_analyze(
        self, 
        content: str,
        group_name: str,
        sender_name: str
    ) -> Dict[str, Any]:
        """使用AI进行深度分析"""
        prompt = f"""请分析以下微信群消息：

群名称：{group_name}
发送者：{sender_name}
消息内容：{content}

请判断这条消息的价值，并以JSON格式返回分析结果。"""
        
        response = await self.think([{"role": "user", "content": prompt}], temperature=0.3)
        
        # 解析JSON
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass
        
        # 解析失败，返回默认结果
        return {
            "is_valuable": False,
            "category": "irrelevant",
            "confidence": 0,
            "reason": "AI分析失败"
        }
    
    def _extract_contact_info(self, content: str) -> Optional[Dict[str, str]]:
        """提取联系方式"""
        contact = {}
        
        # 手机号
        phone_match = re.search(r'1[3-9]\d{9}', content)
        if phone_match:
            contact["phone"] = phone_match.group()
        
        # 微信号
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
        
        # 邮箱
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        if email_match:
            contact["email"] = email_match.group()
        
        return contact if contact else None
    
    async def process_batch(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量处理消息"""
        results = []
        for msg in messages:
            result = await self.process(msg)
            results.append({
                "message": msg,
                "analysis": result
            })
        return results
    
    async def get_daily_summary(self) -> Dict[str, Any]:
        """生成每日汇总"""
        from app.models.database import async_session_maker
        from sqlalchemy import text
        
        try:
            async with async_session_maker() as db:
                # 今日统计
                result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE is_valuable = true) as valuable,
                            COUNT(*) FILTER (WHERE analysis_result->>'category' = 'lead') as leads,
                            COUNT(*) FILTER (WHERE analysis_result->>'category' = 'intel') as intel,
                            COUNT(*) FILTER (WHERE analysis_result->>'category' = 'knowledge') as knowledge
                        FROM wechat_messages
                        WHERE DATE(created_at) = CURRENT_DATE
                    """)
                )
                stats = result.fetchone()
                
                # 获取今日发现的线索
                result = await db.execute(
                    text("""
                        SELECT content, analysis_result, group_id, sender_name
                        FROM wechat_messages
                        WHERE DATE(created_at) = CURRENT_DATE
                        AND analysis_result->>'category' = 'lead'
                        ORDER BY created_at DESC
                        LIMIT 10
                    """)
                )
                leads = result.fetchall()
                
                return {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "statistics": {
                        "total_messages": stats[0] if stats else 0,
                        "valuable_messages": stats[1] if stats else 0,
                        "leads_found": stats[2] if stats else 0,
                        "intel_collected": stats[3] if stats else 0,
                        "knowledge_extracted": stats[4] if stats else 0
                    },
                    "top_leads": [
                        {
                            "content": row[0][:100],
                            "analysis": row[1],
                            "group": row[2],
                            "sender": row[3]
                        }
                        for row in leads
                    ]
                }
        except Exception as e:
            logger.error(f"生成每日汇总失败: {e}")
            return {"error": str(e)}


# 创建单例并注册
analyst2_agent = Analyst2Agent()
AgentRegistry.register(analyst2_agent)
