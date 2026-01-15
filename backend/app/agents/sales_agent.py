"""
小销 - 销售客服
负责首次接待、解答咨询、收集需求
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import select, text

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from app.models.company_config import CompanyConfig
from app.core.prompts.sales import SALES_SYSTEM_PROMPT, CHAT_RESPONSE_PROMPT


class SalesAgent(BaseAgent):
    """小销 - 销售客服"""
    
    name = "小销"
    agent_type = AgentType.SALES
    description = "销售客服 - 负责首次接待、解答咨询、收集需求"
    
    def _build_system_prompt(self) -> str:
        return SALES_SYSTEM_PROMPT
    
    async def _get_company_context(self) -> str:
        """从数据库获取公司上下文信息"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CompanyConfig).limit(1))
                config = result.scalar_one_or_none()
                
                if not config:
                    return ""
                
                lines = []
                
                if config.company_name:
                    lines.append(f"公司名称：{config.company_name}")
                
                if config.company_intro:
                    lines.append(f"公司简介：{config.company_intro}")
                
                if config.products:
                    products_text = []
                    for p in config.products:
                        name = p.get('name', '')
                        desc = p.get('description', '')
                        features = p.get('features', [])
                        products_text.append(f"- {name}: {desc} (特点: {', '.join(features)})")
                    if products_text:
                        lines.append("我们提供的产品服务：")
                        lines.extend(products_text)
                
                if config.service_routes:
                    routes_text = []
                    for r in config.service_routes:
                        from_loc = r.get('from_location', '')
                        to_loc = r.get('to_location', '')
                        transport = r.get('transport', '')
                        time = r.get('time', '')
                        price_ref = r.get('price_ref', '')
                        route_info = f"- {from_loc}→{to_loc} ({transport}): {time}"
                        if price_ref:
                            route_info += f", 参考价格: {price_ref}"
                        routes_text.append(route_info)
                    if routes_text:
                        lines.append("服务航线：")
                        lines.extend(routes_text)
                
                if config.advantages:
                    lines.append(f"公司优势：{', '.join(config.advantages)}")
                
                if config.price_policy:
                    lines.append(f"价格政策：{config.price_policy}")
                
                if config.contact_phone:
                    lines.append(f"联系电话：{config.contact_phone}")
                
                if config.contact_wechat:
                    lines.append(f"客服微信：{config.contact_wechat}")
                
                return "\n".join(lines)
        except Exception as e:
            logger.error(f"获取公司配置失败: {e}")
            return ""
    
    async def _get_work_stats(self) -> Dict[str, Any]:
        """从数据库获取真实的工作统计数据"""
        stats = {
            "today_conversations": 0,
            "today_inquiries": 0,  # 询价相关对话
            "today_new_customers": 0,
            "today_follow_records": 0,
            "total_customers": 0,
            "high_intent_customers": 0,
            "total_leads": 0,
        }
        
        try:
            async with AsyncSessionLocal() as db:
                # 获取今天的开始时间（UTC）
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                
                # 今日对话总数
                result = await db.execute(
                    text("SELECT COUNT(*) FROM conversations WHERE created_at >= :today"),
                    {"today": today}
                )
                stats["today_conversations"] = result.scalar() or 0
                
                # 今日询价相关对话（包含报价、价格、费用等关键词）
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) FROM conversations 
                        WHERE created_at >= :today 
                        AND message_type = 'inbound'
                        AND (content ILIKE '%报价%' OR content ILIKE '%价格%' 
                             OR content ILIKE '%多少钱%' OR content ILIKE '%费用%'
                             OR content ILIKE '%运费%' OR content ILIKE '%FCL%'
                             OR content ILIKE '%整柜%' OR content ILIKE '%拼箱%')
                    """),
                    {"today": today}
                )
                stats["today_inquiries"] = result.scalar() or 0
                
                # 今日新客户数
                result = await db.execute(
                    text("SELECT COUNT(*) FROM customers WHERE created_at >= :today"),
                    {"today": today}
                )
                stats["today_new_customers"] = result.scalar() or 0
                
                # 今日跟进记录数
                result = await db.execute(
                    text("SELECT COUNT(*) FROM follow_records WHERE created_at >= :today"),
                    {"today": today}
                )
                stats["today_follow_records"] = result.scalar() or 0
                
                # 总客户数
                result = await db.execute(text("SELECT COUNT(*) FROM customers"))
                stats["total_customers"] = result.scalar() or 0
                
                # 高意向客户数 (intent_score >= 60)
                result = await db.execute(
                    text("SELECT COUNT(*) FROM customers WHERE intent_score >= 60")
                )
                stats["high_intent_customers"] = result.scalar() or 0
                
                # 总线索数
                result = await db.execute(text("SELECT COUNT(*) FROM leads"))
                stats["total_leads"] = result.scalar() or 0
                
        except Exception as e:
            logger.error(f"获取工作统计数据失败: {e}")
        
        return stats
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理对话
        
        Args:
            input_data: {
                "customer_id": "客户/同事ID",
                "message": "消息内容",
                "customer_info": "客户信息（可选）",
                "chat_history": "对话历史（可选）",
                "context": {"user_type": "external/internal"}
            }
        
        Returns:
            {
                "reply": "回复内容",
                "intent_signals": ["识别到的意向信号"],
                "collected_info": {"收集到的信息"}
            }
        """
        customer_id = input_data.get("customer_id", "")
        message = input_data.get("message", "")
        customer_info = input_data.get("customer_info", "新客户，暂无信息")
        chat_history = input_data.get("chat_history", "无历史对话")
        context = input_data.get("context", {})
        user_type = context.get("user_type", "external")
        
        # 获取公司上下文信息
        company_context = await self._get_company_context()
        
        # 根据用户类型使用不同的提示
        if user_type == "internal":
            # 内部同事模式 - 获取真实工作数据
            work_stats = await self._get_work_stats()
            
            # 构建工作数据摘要
            work_summary = f"""## 今日真实工作数据（必须基于此回答）
- 今日对话总数：{work_stats['today_conversations']}条
- 今日询价咨询：{work_stats['today_inquiries']}条
- 今日新增客户：{work_stats['today_new_customers']}位
- 今日跟进记录：{work_stats['today_follow_records']}条
- 客户总数：{work_stats['total_customers']}位
- 高意向客户：{work_stats['high_intent_customers']}位
- 线索总数：{work_stats['total_leads']}条"""
            
            chat_prompt = f"""你是公司的AI助手"小销"，现在正在和公司内部的同事聊天。

## 你所在公司的信息
{company_context if company_context else "暂未配置公司信息"}

{work_summary}

## 同事的消息
{message}

请用轻松、友好的同事语气回复。重要规则：
1. 语气亲切随和，像朋友聊天一样
2. 可以用一些轻松的表情符号
3. **关于工作的问题，必须且只能基于上面的"今日真实工作数据"来回答**
4. **绝对不能编造或夸大工作成果！如果数据是0就如实说没有**
5. 如果同事问"忙不忙"、"处理了多少"等问题，如实回答真实数据
6. 如果是闲聊，可以简单回应
7. 回复简洁，不要太长
"""
        else:
            # 外部客户模式 - 专业的销售客服语气
            chat_prompt = f"""你正在与一位潜在客户对话。

## 你所在公司的信息
{company_context if company_context else "暂未配置公司信息"}

## 客户信息
{customer_info}

## 对话历史
{chat_history}

## 客户最新消息
{message}

请根据公司信息和上下文，给出专业、友好的回复。如果客户询问价格、航线、时效等，请根据公司配置的信息回答。如果公司没有配置相关信息，可以引导客户留下联系方式，由专业业务员跟进。
"""
        
        # 生成回复
        reply = await self.think([{"role": "user", "content": chat_prompt}])
        
        # 分析意向信号和收集的信息（仅对外部客户）
        intent_signals = []
        collected_info = {}
        if user_type == "external":
            intent_signals = self._analyze_intent_signals(message)
            collected_info = self._extract_info(message)
        
        log_prefix = "同事" if user_type == "internal" else "客户"
        self.log(f"回复{log_prefix} {customer_id[:8]}...: {reply[:50]}...")
        
        return {
            "reply": reply,
            "intent_signals": intent_signals,
            "collected_info": collected_info
        }
    
    def _analyze_intent_signals(self, message: str) -> List[str]:
        """分析消息中的意向信号"""
        signals = []
        message_lower = message.lower()
        
        # 高意向信号
        if any(kw in message_lower for kw in ["报价", "价格", "多少钱", "费用", "运费"]):
            signals.append("ask_price")
        
        if any(kw in message_lower for kw in ["时效", "多久", "几天", "多长时间"]):
            signals.append("ask_transit_time")
        
        if any(kw in message_lower for kw in ["合作", "长期", "签约", "代理"]):
            signals.append("express_interest")
        
        # 信息提供信号
        if any(kw in message_lower for kw in ["kg", "公斤", "吨", "立方", "cbm"]):
            signals.append("provide_cargo_info")
        
        if any(kw in message_lower for kw in ["电话", "微信", "联系"]):
            signals.append("leave_contact")
        
        # 低意向信号
        if any(kw in message_lower for kw in ["随便问问", "了解一下", "暂时不"]):
            signals.append("just_asking")
        
        return signals
    
    def _extract_info(self, message: str) -> Dict[str, Any]:
        """从消息中提取有用信息"""
        info = {}
        
        # 提取货物信息
        # 这里可以用更复杂的NLP，暂时用简单规则
        if "kg" in message.lower() or "公斤" in message:
            info["has_weight_info"] = True
        
        if "cbm" in message.lower() or "立方" in message:
            info["has_volume_info"] = True
        
        # 提取目的地
        destinations = ["美国", "英国", "德国", "法国", "日本", "韩国", "澳洲", "东南亚"]
        for dest in destinations:
            if dest in message:
                info["destination"] = dest
                break
        
        return info
    
    async def greet_new_customer(self, customer_name: Optional[str] = None) -> str:
        """生成新客户问候语"""
        greeting_prompt = f"""
        请为一位新客户生成开场问候语。
        {"客户名称：" + customer_name if customer_name else "客户名称未知"}
        
        要求：
        1. 热情友好但不过分
        2. 简短有力
        3. 引导客户说出需求
        """
        
        return await self.think([{"role": "user", "content": greeting_prompt}])


# 创建单例并注册
sales_agent = SalesAgent()
AgentRegistry.register(sales_agent)
