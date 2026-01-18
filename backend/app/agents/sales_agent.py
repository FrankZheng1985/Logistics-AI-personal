"""
小销 - 销售客服
负责首次接待、解答咨询、收集需求
支持查询ERP业务系统数据（只读）
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import select, text
import re

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from app.models.company_config import CompanyConfig
from app.core.prompts.sales import SALES_SYSTEM_PROMPT, CHAT_RESPONSE_PROMPT
from app.services.erp_query_helper import erp_query_helper


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
    
    async def _get_erp_context(self, message: str, customer_id: str = None) -> str:
        """
        根据消息内容智能查询ERP数据
        
        分析用户问题，自动判断需要查询什么ERP数据
        返回格式化的上下文信息供AI参考
        """
        erp_context_parts = []
        message_lower = message.lower()
        
        try:
            # 检查ERP是否可用
            if not await erp_query_helper.is_available():
                return ""
            
            # 1. 检测订单查询意图
            order_patterns = [
                r'订单[号]?\s*[：:是]?\s*([A-Za-z0-9\-]+)',
                r'单号\s*[：:是]?\s*([A-Za-z0-9\-]+)',
                r'查[一下]*\s*([A-Za-z0-9\-]+)\s*[订的]?单'
            ]
            for pattern in order_patterns:
                match = re.search(pattern, message)
                if match:
                    order_id = match.group(1)
                    order_data = await erp_query_helper.get_order_status(order_id)
                    if order_data:
                        erp_context_parts.append(
                            await erp_query_helper.format_for_ai_context("order", order_data)
                        )
                    break
            
            # 2. 检测物流跟踪意图
            if any(kw in message_lower for kw in ["物流", "到哪了", "运输状态", "在哪", "跟踪"]):
                # 尝试从消息中提取订单号
                for pattern in order_patterns:
                    match = re.search(pattern, message)
                    if match:
                        order_id = match.group(1)
                        tracking_data = await erp_query_helper.get_shipment_tracking(order_id)
                        if tracking_data:
                            erp_context_parts.append(
                                await erp_query_helper.format_for_ai_context("tracking", tracking_data)
                            )
                        break
            
            # 3. 检测报价查询意图
            if any(kw in message_lower for kw in ["报价", "价格", "多少钱", "运费", "费用"]):
                # 尝试提取路线信息
                from_loc = None
                to_loc = None
                transport = None
                
                # 检测目的地
                destinations = {
                    "美国": "USA", "英国": "UK", "德国": "Germany", 
                    "法国": "France", "日本": "Japan", "韩国": "Korea",
                    "澳洲": "Australia", "东南亚": "SEA", "欧洲": "Europe"
                }
                for dest_cn, dest_en in destinations.items():
                    if dest_cn in message:
                        to_loc = dest_cn
                        break
                
                # 检测运输方式
                if any(kw in message_lower for kw in ["海运", "船运", "海上"]):
                    transport = "sea"
                elif any(kw in message_lower for kw in ["空运", "航空", "飞机"]):
                    transport = "air"
                elif any(kw in message_lower for kw in ["铁路", "中欧班列", "陆运"]):
                    transport = "rail"
                
                # 查询报价
                pricing_data = await erp_query_helper.get_pricing_info(
                    to_location=to_loc,
                    transport_type=transport
                )
                if pricing_data:
                    erp_context_parts.append(
                        await erp_query_helper.format_for_ai_context("pricing", pricing_data)
                    )
            
            # 4. 如果有客户ID，获取客户档案作为背景
            if customer_id and len(customer_id) > 10:  # 看起来像有效的ID
                customer_data = await erp_query_helper.get_customer_profile(customer_id)
                if customer_data:
                    erp_context_parts.append(
                        await erp_query_helper.format_for_ai_context("customer", customer_data)
                    )
            
            if erp_context_parts:
                return "\n\n## ERP业务系统数据（来自真实系统，可用于回答客户问题）\n" + "\n\n".join(erp_context_parts)
            
        except Exception as e:
            logger.warning(f"获取ERP上下文失败: {e}")
        
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
        
        # 开始任务会话（实时直播）
        task_desc = "内部同事对话" if user_type == "internal" else "客户咨询"
        await self.start_task_session("chat", f"{task_desc}: {message[:30]}...")
        
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
            # 获取ERP业务数据上下文
            erp_context = await self._get_erp_context(message, customer_id)
            
            chat_prompt = f"""你正在与一位潜在客户对话。

## 你所在公司的信息
{company_context if company_context else "暂未配置公司信息"}
{erp_context}

## 客户信息
{customer_info}

## 对话历史
{chat_history}

## 客户最新消息
{message}

请根据公司信息和上下文，给出专业、友好的回复。
- 如果有ERP业务系统数据，优先使用这些真实数据回答客户问题
- 如果客户询问订单状态、物流跟踪、报价等，参考ERP数据给出准确回复
- 如果没有相关ERP数据，可以引导客户提供更多信息（如订单号）或留下联系方式
- 回复要专业但亲切，展现服务态度
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
        
        # 结束任务会话
        await self.end_task_session(f"完成{log_prefix}对话")
        
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
