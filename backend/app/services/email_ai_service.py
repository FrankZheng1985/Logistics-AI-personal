"""
邮件AI分析服务 - 深度阅读、分类、摘要、行动建议
Clauwdbot 的邮件智能助手能力
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.core.llm import chat_completion


class EmailAIService:
    """邮件AI深度分析服务"""
    
    # 邮件分类标签
    CATEGORIES = {
        "urgent": "紧急",
        "inquiry": "询价/询盘",
        "complaint": "投诉",
        "order": "订单相关",
        "payment": "付款/财务",
        "logistics": "物流跟踪",
        "marketing": "营销/广告",
        "internal": "内部通知",
        "spam": "垃圾邮件",
        "other": "其他"
    }
    
    async def analyze_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量分析邮件：分类 + 摘要 + 优先级 + 建议
        
        Args:
            emails: [{"subject": "", "from": "", "body": "", "date": ""}]
        
        Returns:
            {"categories": {...}, "priorities": [...], "daily_brief": "..."}
        """
        if not emails:
            return {"categories": {}, "priorities": [], "daily_brief": "今天没有新邮件"}
        
        # 构建邮件摘要列表（控制长度）
        email_summaries = []
        for i, email in enumerate(emails[:20]):  # 最多分析20封
            body_preview = (email.get("body") or "")[:300]
            email_summaries.append(
                f"[邮件{i+1}] 发件人: {email.get('from', '未知')}\n"
                f"主题: {email.get('subject', '无主题')}\n"
                f"时间: {email.get('date', '未知')}\n"
                f"内容预览: {body_preview}"
            )
        
        all_emails_text = "\n\n".join(email_summaries)
        
        analysis_prompt = f"""你是一位专业的物流公司高级秘书，请分析以下邮件并给出处理建议。

{all_emails_text}

请返回JSON格式：
{{
    "summary": "今日邮件整体概况（1-2句话）",
    "emails": [
        {{
            "index": 1,
            "category": "分类（urgent/inquiry/complaint/order/payment/logistics/marketing/internal/spam/other）",
            "priority": "优先级（high/medium/low）",
            "one_line_summary": "一句话摘要",
            "suggested_action": "建议的处理方式",
            "needs_reply": true
        }}
    ],
    "urgent_count": 0,
    "needs_reply_count": 0,
    "top_priorities": ["最需要优先处理的1-3件事"]
}}
只返回JSON。"""

        try:
            import json
            import re
            
            response = await chat_completion(
                messages=[{"role": "user", "content": analysis_prompt}],
                use_advanced=True,
                max_tokens=3000,
                temperature=0.3
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return {"success": True, **json.loads(json_match.group())}
            
            return {"success": False, "error": "分析结果解析失败"}
            
        except Exception as e:
            logger.error(f"[EmailAI] 邮件分析失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def read_email_detail(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度阅读单封邮件，给出详细分析
        
        Args:
            email: {"subject": "", "from": "", "body": "", "date": ""}
        
        Returns:
            {"summary": "...", "key_points": [...], "suggested_reply": "...", "action_items": [...]}
        """
        body = (email.get("body") or "")[:2000]
        
        read_prompt = f"""请深度分析以下邮件内容：

发件人: {email.get('from', '未知')}
主题: {email.get('subject', '无主题')}
时间: {email.get('date', '未知')}
正文:
{body}

请返回JSON格式：
{{
    "summary": "邮件核心内容摘要（2-3句话）",
    "key_points": ["关键信息1", "关键信息2"],
    "sender_intent": "发件人的意图/目的",
    "urgency": "紧急程度（high/medium/low）",
    "needs_reply": true,
    "suggested_reply": "建议回复内容的要点（如果需要回复）",
    "action_items": ["需要做的事项1", "需要做的事项2"],
    "related_info": "可能需要关联的信息（如客户档案、订单号等）"
}}
只返回JSON。"""

        try:
            import json
            import re
            
            response = await chat_completion(
                messages=[{"role": "user", "content": read_prompt}],
                use_advanced=True,
                max_tokens=2000,
                temperature=0.3
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return {"success": True, **json.loads(json_match.group())}
            
            return {"success": False, "error": "分析结果解析失败"}
            
        except Exception as e:
            logger.error(f"[EmailAI] 邮件深度阅读失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def draft_reply(self, email: Dict[str, Any], reply_instruction: str = "") -> Dict[str, Any]:
        """
        帮老板草拟邮件回复
        
        Args:
            email: 原始邮件
            reply_instruction: 老板的回复指示（如"告诉他下周发货"）
        
        Returns:
            {"draft": "...", "subject": "..."}
        """
        body = (email.get("body") or "")[:1500]
        
        draft_prompt = f"""请帮我草拟一封回复邮件。

原始邮件：
发件人: {email.get('from', '未知')}
主题: {email.get('subject', '无主题')}
内容: {body}

回复指示：{reply_instruction or '请根据邮件内容给出专业、得体的回复'}

要求：
1. 语气专业、礼貌
2. 直接给出可发送的邮件正文
3. 如果涉及物流业务，要用行业术语
4. 简洁明了，不要废话

请返回JSON格式：
{{
    "subject": "回复主题",
    "body": "邮件正文",
    "tone": "语气描述"
}}
只返回JSON。"""

        try:
            import json
            import re
            
            response = await chat_completion(
                messages=[{"role": "user", "content": draft_prompt}],
                use_advanced=True,
                max_tokens=2000,
                temperature=0.5
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return {"success": True, **json.loads(json_match.group())}
            
            return {"success": True, "body": response, "subject": f"Re: {email.get('subject', '')}"}
            
        except Exception as e:
            logger.error(f"[EmailAI] 草拟回复失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_daily_email_brief(self, emails: List[Dict[str, Any]], user_name: str = "郑总") -> str:
        """
        生成每日邮件简报（口语化，给老板看的）
        
        Args:
            emails: 未读邮件列表
            user_name: 老板称呼
        
        Returns:
            口语化的邮件简报文本
        """
        if not emails:
            return f"{user_name}，今天邮箱里没有新邮件，挺清净的~"
        
        # 先做批量分析
        analysis = await self.analyze_emails(emails)
        
        if not analysis.get("success"):
            return f"{user_name}，邮件分析出了点问题，我稍后再试。您也可以直接说'查看邮件详情'让我重新读一遍。"
        
        # 用 LLM 把分析结果转成口语化简报
        import json
        brief_prompt = f"""你是Clauwdbot，温柔利索的AI女助理。请把以下邮件分析结果转成微信聊天风格的简报给{user_name}看。

分析结果：
{json.dumps(analysis, ensure_ascii=False, indent=2)}

要求：
1. 像在微信上跟老板汇报一样自然
2. 先说重要的（紧急邮件和需要回复的）
3. 不要用markdown、标签、列表符号
4. 不超过200字
5. 最后问老板要不要看某封邮件的详情或帮忙回复"""

        try:
            brief = await chat_completion(
                messages=[{"role": "user", "content": brief_prompt}],
                temperature=0.7,
                max_tokens=500
            )
            return brief
        except Exception as e:
            logger.error(f"[EmailAI] 生成邮件简报失败: {e}")
            return f"{user_name}，今天有{len(emails)}封新邮件，其中{analysis.get('urgent_count', 0)}封比较紧急。要我帮您详细看看吗？"


# 单例
email_ai_service = EmailAIService()
