"""
邮件服务
支持两类邮件：
1. 系统通知邮件：高意向客户提醒、每日汇总、异常告警等（发给管理员）
2. 客户营销邮件：跟进邮件、促销邮件、激活邮件等（发给客户）
"""
import smtplib
import ssl
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.core.config import settings


class EmailService:
    """邮件服务"""
    
    def __init__(self):
        # 先从环境变量加载默认配置
        self.smtp_host = getattr(settings, 'SMTP_HOST', '')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 465)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.notify_email = getattr(settings, 'NOTIFY_EMAIL', '')
        self.sender_name = getattr(settings, 'EMAIL_SENDER_NAME', '物流获客AI')
        
        # 默认公司名称（用于邮件模板）
        self.default_company_name = "物流智能体"
        
        # 标记是否已从数据库加载
        self._db_config_loaded = False
    
    async def load_config_from_db(self, force: bool = False):
        """从数据库加载SMTP配置（如果有）"""
        if self._db_config_loaded and not force:
            return
        
        try:
            from app.models.database import async_session_maker
            import json
            
            async with async_session_maker() as db:
                result = await db.execute(
                    text("SELECT value FROM system_settings WHERE key = 'smtp'")
                )
                row = result.fetchone()
                
                if row and row[0]:
                    config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    
                    # 用数据库配置覆盖环境变量配置
                    if config.get("smtp_host"):
                        self.smtp_host = config["smtp_host"]
                    if config.get("smtp_port"):
                        self.smtp_port = config["smtp_port"]
                    if config.get("smtp_user"):
                        self.smtp_user = config["smtp_user"]
                    if config.get("smtp_password"):
                        self.smtp_password = config["smtp_password"]
                    if config.get("sender_name"):
                        self.sender_name = config["sender_name"]
                    
                    logger.info("📧 已从数据库加载SMTP配置")
            
            self._db_config_loaded = True
        except Exception as e:
            logger.warning(f"从数据库加载SMTP配置失败: {e}")
    
    @property
    def is_configured(self) -> bool:
        """检查邮件服务是否已配置"""
        return bool(
            self.smtp_host and 
            self.smtp_user and 
            self.smtp_password
        )
    
    async def get_email_signature(self) -> Dict[str, str]:
        """
        获取邮件签名，从公司配置中读取
        返回 HTML 和纯文本两种格式的签名
        """
        from app.models.database import async_session_maker
        import json
        
        # 默认签名
        default_html = f"""
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; font-size: 13px; color: #666;">
            <p style="margin: 5px 0;"><strong>{self.sender_name}</strong></p>
            <p style="margin: 5px 0;">邮箱：{self.smtp_user}</p>
            <p style="margin: 5px 0; font-size: 12px; color: #999;">此邮件由系统自动发送，如需帮助请直接回复</p>
        </div>
        """
        default_text = f"\n\n---\n{self.sender_name}\n邮箱：{self.smtp_user}\n"
        
        try:
            # 获取SMTP配置中的邮件Logo
            email_logo = ""
            try:
                result = await async_session_maker().execute(
                    text("SELECT value FROM system_settings WHERE key = 'smtp'")
                )
                smtp_row = result.fetchone()
                if smtp_row and smtp_row[0]:
                    smtp_config = smtp_row[0] if isinstance(smtp_row[0], dict) else json.loads(smtp_row[0])
                    email_logo = smtp_config.get("email_logo", "")
            except:
                pass
            
            async with async_session_maker() as db:
                # 获取公司配置
                result = await db.execute(
                    text("""SELECT company_name, contact_phone, contact_email, contact_wechat, 
                                   address, company_website, brand_slogan, brand_assets
                            FROM company_config LIMIT 1""")
                )
                row = result.fetchone()
                
                if row:
                    company_name = row[0] or ""
                    contact_phone = row[1] or ""
                    contact_email = row[2] or self.smtp_user
                    contact_wechat = row[3] or ""
                    address = row[4] or ""
                    company_website = row[5] or ""
                    brand_slogan = row[6] or ""
                    # 从 brand_assets 获取微信二维码
                    brand_assets = row[7] if row[7] else {}
                    if isinstance(brand_assets, str):
                        brand_assets = json.loads(brand_assets)
                    wechat_qrcode = brand_assets.get("qrcode", {}).get("wechat", "")
                    
                    # 构建 HTML 签名
                    html_parts = [
                        '<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; font-size: 13px; color: #666; font-family: Arial, sans-serif;">'
                    ]
                    
                    # Logo显示在最上方
                    if email_logo:
                        html_parts.append(f'<p style="margin: 0 0 15px 0;"><img src="{email_logo}" alt="Logo" style="max-height: 50px; width: auto;" /></p>')
                    
                    if brand_slogan:
                        html_parts.append(f'<p style="margin: 0 0 10px 0; color: #333; font-style: italic;">"{brand_slogan}"</p>')
                    
                    html_parts.append(f'<p style="margin: 5px 0; font-size: 14px;"><strong style="color: #333;">{self.sender_name}</strong></p>')
                    
                    if company_name:
                        html_parts.append(f'<p style="margin: 5px 0;">{company_name}</p>')
                    
                    # 地址在电话前面
                    if address:
                        html_parts.append(f'<p style="margin: 5px 0;">📍 地址：{address}</p>')
                    
                    if contact_phone:
                        html_parts.append(f'<p style="margin: 5px 0;">📞 电话：{contact_phone}</p>')
                    
                    if contact_email:
                        html_parts.append(f'<p style="margin: 5px 0;">📧 邮箱：{contact_email}</p>')
                    
                    # 微信号和二维码
                    if contact_wechat:
                        if wechat_qrcode:
                            html_parts.append(f'<p style="margin: 5px 0;">💬 微信：{contact_wechat}</p>')
                            html_parts.append(f'<p style="margin: 10px 0;"><img src="{wechat_qrcode}" alt="微信二维码" style="max-width: 120px; height: auto;" /></p>')
                        else:
                            html_parts.append(f'<p style="margin: 5px 0;">💬 微信：{contact_wechat}</p>')
                    
                    if company_website:
                        html_parts.append(f'<p style="margin: 5px 0;">🌐 官网：<a href="{company_website}" style="color: #0066cc;">{company_website}</a></p>')
                    
                    html_parts.append('</div>')
                    
                    # 构建纯文本签名
                    text_parts = ["\n\n---"]
                    if brand_slogan:
                        text_parts.append(f'"{brand_slogan}"')
                    text_parts.append(f"{self.sender_name}")
                    if company_name:
                        text_parts.append(company_name)
                    if address:
                        text_parts.append(f"地址：{address}")
                    if contact_phone:
                        text_parts.append(f"电话：{contact_phone}")
                    if contact_email:
                        text_parts.append(f"邮箱：{contact_email}")
                    if contact_wechat:
                        text_parts.append(f"微信：{contact_wechat}")
                    if company_website:
                        text_parts.append(f"官网：{company_website}")
                    
                    return {
                        "html": "\n".join(html_parts),
                        "text": "\n".join(text_parts)
                    }
        except Exception as e:
            logger.warning(f"获取邮件签名失败: {e}")
        
        return {"html": default_html, "text": default_text}
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        include_signature: bool = False
    ) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to_emails: 收件人列表
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容（可选）
            include_signature: 是否附加签名（默认False，系统通知邮件不需要签名）
        
        Returns:
            发送结果
        """
        # 尝试从数据库加载配置
        await self.load_config_from_db()
        
        if not self.is_configured:
            logger.warning("邮件服务未配置，跳过发送")
            return {"status": "skipped", "message": "邮件服务未配置"}
        
        try:
            # 如果需要签名，获取并附加
            if include_signature:
                signature = await self.get_email_signature()
                html_content = html_content + signature["html"]
                if text_content:
                    text_content = text_content + signature["text"]
            
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((self.sender_name, self.smtp_user))
            msg["To"] = ", ".join(to_emails)
            
            # 添加纯文本版本（某些邮件客户端不支持HTML）
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                msg.attach(part1)
            
            # 添加HTML版本
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part2)
            
            # 发送邮件
            context = ssl.create_default_context()
            
            if self.smtp_port == 465:
                # SSL连接
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, to_emails, msg.as_string())
            else:
                # TLS连接
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, to_emails, msg.as_string())
            
            logger.info(f"📧 邮件发送成功: {subject} -> {to_emails}")
            return {"status": "sent", "to": to_emails}
            
        except Exception as e:
            logger.error(f"📧 邮件发送失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def send_simple_customer_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送简单客户跟进邮件（自动附加签名）
        用于AI生成的跟进邮件等简单场景
        
        Args:
            to_email: 客户邮箱
            subject: 邮件主题
            body: 邮件正文内容（纯文本）
            customer_name: 客户姓名（可选，用于称呼）
        
        Returns:
            发送结果
        """
        # 构建 HTML 邮件正文
        greeting = f"<p>尊敬的{customer_name}：</p>" if customer_name else "<p>您好：</p>"
        
        # 将纯文本内容转换为 HTML（保留换行）
        body_html = body.replace("\n", "<br>")
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
            {greeting}
            <div style="margin: 15px 0;">
                {body_html}
            </div>
        </div>
        """
        
        # 纯文本版本
        text_greeting = f"尊敬的{customer_name}：\n\n" if customer_name else "您好：\n\n"
        text_content = text_greeting + body
        
        return await self.send_email(
            to_emails=[to_email],
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            include_signature=True  # 客户邮件自动附加签名
        )
    
    # =====================================================
    # 客户营销邮件功能
    # =====================================================
    
    def _render_template(
        self, 
        template: str, 
        variables: Dict[str, str]
    ) -> str:
        """
        渲染邮件模板，替换变量
        
        支持的变量格式: {{variable_name}}
        """
        result = template
        for key, value in variables.items():
            # 替换 {{key}} 格式的变量
            pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
            result = re.sub(pattern, str(value) if value else '', result)
        return result
    
    async def get_email_templates(
        self,
        template_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取邮件模板列表"""
        from app.models.database import async_session_maker
        
        try:
            async with async_session_maker() as db:
                query = """
                    SELECT id, name, template_type, subject, html_content, text_content,
                           variables, is_active, is_default, use_count, last_used_at
                    FROM email_templates
                    WHERE 1=1
                """
                params = {}
                
                if active_only:
                    query += " AND is_active = true"
                
                if template_type:
                    query += " AND template_type = :template_type"
                    params["template_type"] = template_type
                
                query += " ORDER BY is_default DESC, use_count DESC"
                
                result = await db.execute(text(query), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "template_type": row[2],
                        "subject": row[3],
                        "html_content": row[4],
                        "text_content": row[5],
                        "variables": row[6] or [],
                        "is_active": row[7],
                        "is_default": row[8],
                        "use_count": row[9],
                        "last_used_at": row[10].isoformat() if row[10] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取邮件模板失败: {e}")
            return []
    
    async def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取邮件模板"""
        from app.models.database import async_session_maker
        
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT id, name, template_type, subject, html_content, text_content,
                               variables, is_active, is_default
                        FROM email_templates
                        WHERE id = :template_id
                    """),
                    {"template_id": template_id}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "id": str(row[0]),
                        "name": row[1],
                        "template_type": row[2],
                        "subject": row[3],
                        "html_content": row[4],
                        "text_content": row[5],
                        "variables": row[6] or [],
                        "is_active": row[7],
                        "is_default": row[8]
                    }
                return None
        except Exception as e:
            logger.error(f"获取邮件模板失败: {e}")
            return None
    
    async def get_default_template(self, template_type: str = "follow_up") -> Optional[Dict[str, Any]]:
        """获取默认模板"""
        from app.models.database import async_session_maker
        
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT id, name, template_type, subject, html_content, text_content, variables
                        FROM email_templates
                        WHERE template_type = :template_type AND is_active = true
                        ORDER BY is_default DESC, use_count DESC
                        LIMIT 1
                    """),
                    {"template_type": template_type}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "id": str(row[0]),
                        "name": row[1],
                        "template_type": row[2],
                        "subject": row[3],
                        "html_content": row[4],
                        "text_content": row[5],
                        "variables": row[6] or []
                    }
                return None
        except Exception as e:
            logger.error(f"获取默认模板失败: {e}")
            return None
    
    async def _get_company_name(self) -> str:
        """获取公司名称（从配置中）"""
        from app.models.database import async_session_maker
        
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("SELECT company_name FROM company_config LIMIT 1")
                )
                row = result.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as e:
            logger.warning(f"获取公司名称失败: {e}")
        
        return self.default_company_name
    
    async def send_customer_email(
        self,
        customer_id: str,
        to_email: str,
        template_id: Optional[str] = None,
        subject: Optional[str] = None,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        sender_type: str = "ai",
        sender_name: str = "小跟",
        follow_record_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        给客户发送邮件
        
        Args:
            customer_id: 客户ID
            to_email: 收件人邮箱
            template_id: 模板ID（可选，如果提供则使用模板）
            subject: 邮件主题（如果不使用模板则必填）
            html_content: HTML内容（如果不使用模板则必填）
            text_content: 纯文本内容（可选）
            variables: 模板变量（如 {"customer_name": "张三"}）
            sender_type: 发送者类型 (ai/manual)
            sender_name: 发送者名称
            follow_record_id: 关联的跟进记录ID
        
        Returns:
            发送结果
        """
        from app.models.database import async_session_maker
        
        if not self.is_configured:
            logger.warning("邮件服务未配置，跳过发送")
            return {"status": "skipped", "message": "邮件服务未配置，请在设置中配置SMTP"}
        
        # 验证邮箱格式
        if not to_email or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', to_email):
            return {"status": "error", "message": "邮箱格式无效"}
        
        try:
            # 获取公司名称
            company_name = await self._get_company_name()
            
            # 如果使用模板
            if template_id:
                template = await self.get_template_by_id(template_id)
                if not template:
                    return {"status": "error", "message": "模板不存在"}
                
                subject = template["subject"]
                html_content = template["html_content"]
                text_content = template.get("text_content")
            
            if not subject or not html_content:
                return {"status": "error", "message": "缺少邮件主题或内容"}
            
            # 准备变量
            render_vars = variables or {}
            render_vars.setdefault("company_name", company_name)
            
            # 渲染模板
            rendered_subject = self._render_template(subject, render_vars)
            rendered_html = self._render_template(html_content, render_vars)
            rendered_text = self._render_template(text_content, render_vars) if text_content else None
            
            # 记录发送日志
            async with async_session_maker() as db:
                # 创建发送记录
                log_result = await db.execute(
                    text("""
                        INSERT INTO email_logs 
                        (customer_id, template_id, follow_record_id, to_email, subject, content,
                         status, sender_type, sender_name, created_at)
                        VALUES (:customer_id, :template_id, :follow_record_id, :to_email, :subject, :content,
                                'pending', :sender_type, :sender_name, NOW())
                        RETURNING id
                    """),
                    {
                        "customer_id": customer_id,
                        "template_id": template_id,
                        "follow_record_id": follow_record_id,
                        "to_email": to_email,
                        "subject": rendered_subject,
                        "content": rendered_html,
                        "sender_type": sender_type,
                        "sender_name": sender_name
                    }
                )
                log_id = log_result.scalar()
                await db.commit()
            
            # 发送邮件
            send_result = await self.send_email(
                to_emails=[to_email],
                subject=rendered_subject,
                html_content=rendered_html,
                text_content=rendered_text
            )
            
            # 更新发送状态
            async with async_session_maker() as db:
                if send_result.get("status") == "sent":
                    await db.execute(
                        text("""
                            UPDATE email_logs 
                            SET status = 'sent', sent_at = NOW()
                            WHERE id = :log_id
                        """),
                        {"log_id": log_id}
                    )
                    
                    # 更新模板使用次数
                    if template_id:
                        await db.execute(
                            text("""
                                UPDATE email_templates 
                                SET use_count = use_count + 1, last_used_at = NOW()
                                WHERE id = :template_id
                            """),
                            {"template_id": template_id}
                        )
                else:
                    await db.execute(
                        text("""
                            UPDATE email_logs 
                            SET status = 'failed', error_message = :error
                            WHERE id = :log_id
                        """),
                        {"log_id": log_id, "error": send_result.get("message", "发送失败")}
                    )
                
                await db.commit()
            
            logger.info(f"📧 客户邮件{'发送成功' if send_result.get('status') == 'sent' else '发送失败'}: {to_email}")
            
            return {
                "status": send_result.get("status"),
                "message": "邮件发送成功" if send_result.get("status") == "sent" else send_result.get("message"),
                "email_log_id": str(log_id),
                "to_email": to_email
            }
            
        except Exception as e:
            logger.error(f"📧 发送客户邮件异常: {e}")
            return {"status": "error", "message": str(e)}
    
    async def send_follow_email(
        self,
        customer_id: str,
        to_email: str,
        customer_name: str,
        purpose: str = "daily_follow",
        custom_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送跟进邮件（简化接口，小跟使用）
        
        Args:
            customer_id: 客户ID
            to_email: 客户邮箱
            customer_name: 客户姓名
            purpose: 跟进目的 (daily_follow, quote_follow, reactivate)
            custom_content: 自定义内容（如果提供则不使用模板）
        """
        # 根据目的选择模板类型
        template_type_map = {
            "daily_follow": "follow_up",
            "quote_follow": "follow_up",
            "reactivate": "reactivate",
            "promotion": "promotion"
        }
        template_type = template_type_map.get(purpose, "follow_up")
        
        # 如果有自定义内容，直接发送
        if custom_content:
            company_name = await self._get_company_name()
            return await self.send_customer_email(
                customer_id=customer_id,
                to_email=to_email,
                subject=f"来自{company_name}的问候",
                html_content=f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.8; color: #333;">
                    <p>{customer_name}，您好！</p>
                    <p>{custom_content}</p>
                    <br>
                    <p style="color: #666;">---<br>{company_name}<br>您的可靠物流伙伴</p>
                </body>
                </html>
                """,
                text_content=f"{customer_name}，您好！\n\n{custom_content}\n\n---\n{company_name}",
                sender_type="ai",
                sender_name="小跟"
            )
        
        # 使用默认模板
        template = await self.get_default_template(template_type)
        if not template:
            return {"status": "error", "message": f"未找到{template_type}类型的邮件模板"}
        
        return await self.send_customer_email(
            customer_id=customer_id,
            to_email=to_email,
            template_id=template["id"],
            variables={"customer_name": customer_name},
            sender_type="ai",
            sender_name="小跟"
        )
    
    async def get_email_logs(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取邮件发送记录"""
        from app.models.database import async_session_maker
        
        try:
            async with async_session_maker() as db:
                query = """
                    SELECT el.id, el.customer_id, el.to_email, el.subject, el.status,
                           el.sender_type, el.sender_name, el.sent_at, el.error_message,
                           el.open_count, el.click_count, el.created_at,
                           c.name as customer_name, et.name as template_name
                    FROM email_logs el
                    LEFT JOIN customers c ON el.customer_id = c.id
                    LEFT JOIN email_templates et ON el.template_id = et.id
                    WHERE 1=1
                """
                params = {"limit": limit}
                
                if customer_id:
                    query += " AND el.customer_id = :customer_id"
                    params["customer_id"] = customer_id
                
                if status:
                    query += " AND el.status = :status"
                    params["status"] = status
                
                query += " ORDER BY el.created_at DESC LIMIT :limit"
                
                result = await db.execute(text(query), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "customer_id": str(row[1]) if row[1] else None,
                        "to_email": row[2],
                        "subject": row[3],
                        "status": row[4],
                        "sender_type": row[5],
                        "sender_name": row[6],
                        "sent_at": row[7].isoformat() if row[7] else None,
                        "error_message": row[8],
                        "open_count": row[9],
                        "click_count": row[10],
                        "created_at": row[11].isoformat() if row[11] else None,
                        "customer_name": row[12],
                        "template_name": row[13]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取邮件记录失败: {e}")
            return []
    
    async def notify_high_intent_customer(
        self,
        customer_name: str,
        company: Optional[str],
        intent_score: int,
        intent_level: str,
        key_signals: List[str],
        last_message: Optional[str] = None,
        customer_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送高意向客户提醒邮件"""
        if not self.is_configured:
            return {"status": "skipped", "message": "邮件服务未配置"}
        
        subject = f"🔥 高意向客户提醒: {customer_name} ({intent_level}级)"
        
        signals_html = "".join([f"<li>{s}</li>" for s in key_signals]) if key_signals else "<li>无</li>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ color: #e74c3c; font-size: 24px; margin-bottom: 20px; }}
                .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .label {{ color: #666; font-size: 12px; }}
                .value {{ color: #333; font-size: 16px; font-weight: bold; }}
                .score {{ font-size: 36px; color: #e74c3c; font-weight: bold; }}
                .level {{ display: inline-block; padding: 5px 15px; background: #e74c3c; color: white; border-radius: 20px; }}
                .message-box {{ background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                .action {{ background: #27ae60; color: white; padding: 12px 24px; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 20px; }}
                .footer {{ color: #999; font-size: 12px; margin-top: 30px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">🔥 发现高意向客户！</div>
                
                <div class="info-box">
                    <div class="label">客户名称</div>
                    <div class="value">{customer_name}</div>
                    {f'<div class="label" style="margin-top:10px">公司</div><div class="value">{company}</div>' if company else ''}
                    {f'<div class="label" style="margin-top:10px">联系电话</div><div class="value">{customer_phone}</div>' if customer_phone else ''}
                </div>
                
                <div class="info-box" style="text-align: center;">
                    <div class="label">意向评分</div>
                    <div class="score">{intent_score}</div>
                    <div><span class="level">{intent_level}级客户</span></div>
                </div>
                
                <div class="info-box">
                    <div class="label">识别到的关键信号</div>
                    <ul>{signals_html}</ul>
                </div>
                
                {f'''
                <div class="message-box">
                    <div class="label">客户最近消息</div>
                    <div style="margin-top: 8px; color: #333;">"{last_message}"</div>
                </div>
                ''' if last_message else ''}
                
                <div style="text-align: center;">
                    <div style="color: #e74c3c; font-weight: bold;">⚡ 建议立即跟进，促成签约！</div>
                </div>
                
                <div class="footer">
                    <p>此邮件由物流获客AI系统自动发送</p>
                    <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        🔥 发现高意向客户！
        
        客户名称: {customer_name}
        公司: {company or '未知'}
        联系电话: {customer_phone or '未知'}
        
        意向评分: {intent_score}分 ({intent_level}级)
        
        关键信号: {', '.join(key_signals) if key_signals else '无'}
        
        客户最近消息: {last_message or '无'}
        
        建议: 立即跟进，促成签约！
        
        ---
        物流获客AI系统
        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return await self.send_email(
            to_emails=[self.notify_email],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    async def send_daily_summary(
        self,
        date: str,
        new_customers: int,
        high_intent_count: int,
        conversations: int,
        follow_count: int,
        videos_generated: int,
        top_customers: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送每日工作汇总邮件"""
        if not self.is_configured:
            return {"status": "skipped", "message": "邮件服务未配置"}
        
        subject = f"📊 物流获客AI每日汇总 - {date}"
        
        # 生成高意向客户列表
        top_customers_html = ""
        if top_customers:
            rows = "".join([
                f"<tr><td>{c.get('name', '未知')}</td><td>{c.get('company', '-')}</td><td>{c.get('intent_level', 'C')}级</td><td>{c.get('intent_score', 0)}分</td></tr>"
                for c in top_customers[:5]
            ])
            top_customers_html = f"""
            <h3 style="color: #333; margin-top: 30px;">🌟 今日高意向客户</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f8f9fa;">
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">客户</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">公司</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">等级</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">分数</th>
                </tr>
                {rows}
            </table>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ color: #3498db; font-size: 24px; margin-bottom: 20px; }}
                .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }}
                .stat-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; }}
                .stat-label {{ color: #666; font-size: 14px; margin-top: 5px; }}
                .highlight {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .highlight .stat-value {{ color: white; }}
                .highlight .stat-label {{ color: rgba(255,255,255,0.9); }}
                table {{ width: 100%; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
                .footer {{ color: #999; font-size: 12px; margin-top: 30px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">📊 {date} 工作汇总</div>
                
                <div class="stat-grid">
                    <div class="stat-box highlight">
                        <div class="stat-value">{new_customers}</div>
                        <div class="stat-label">新增客户</div>
                    </div>
                    <div class="stat-box highlight">
                        <div class="stat-value">{high_intent_count}</div>
                        <div class="stat-label">高意向客户</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{conversations}</div>
                        <div class="stat-label">对话数量</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{follow_count}</div>
                        <div class="stat-label">跟进次数</div>
                    </div>
                </div>
                
                <div class="stat-box" style="margin-top: 15px;">
                    <div class="stat-value">{videos_generated}</div>
                    <div class="stat-label">视频生成</div>
                </div>
                
                {top_customers_html}
                
                <div class="footer">
                    <p>此邮件由物流获客AI系统自动发送</p>
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        📊 物流获客AI每日汇总 - {date}
        
        ==============================
        今日数据
        ==============================
        新增客户: {new_customers}
        高意向客户: {high_intent_count}
        对话数量: {conversations}
        跟进次数: {follow_count}
        视频生成: {videos_generated}
        
        ---
        物流获客AI系统
        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return await self.send_email(
            to_emails=[self.notify_email],
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    async def send_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送系统告警邮件"""
        if not self.is_configured:
            return {"status": "skipped", "message": "邮件服务未配置"}
        
        subject = f"⚠️ 系统告警: {title}"
        
        details_html = ""
        if details:
            rows = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in details.items()])
            details_html = f"""
            <table style="width: 100%; margin-top: 15px;">
                {rows}
            </table>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ color: #e74c3c; font-size: 24px; margin-bottom: 20px; }}
                .alert-box {{ background: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                table {{ width: 100%; }}
                td {{ padding: 8px; border-bottom: 1px solid #eee; }}
                .footer {{ color: #999; font-size: 12px; margin-top: 30px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">⚠️ 系统告警</div>
                
                <div class="alert-box">
                    <strong>告警类型:</strong> {alert_type}<br>
                    <strong>告警内容:</strong> {message}
                </div>
                
                {details_html}
                
                <div class="footer">
                    <p>此邮件由物流获客AI系统自动发送</p>
                    <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_emails=[self.notify_email],
            subject=subject,
            html_content=html_content
        )


# 创建单例
email_service = EmailService()
