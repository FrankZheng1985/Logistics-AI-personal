"""
邮件通知服务
支持发送各类通知邮件：高意向客户提醒、每日汇总、异常告警等
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from app.core.config import settings


class EmailService:
    """邮件服务"""
    
    def __init__(self):
        self.smtp_host = getattr(settings, 'SMTP_HOST', '')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 465)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.notify_email = getattr(settings, 'NOTIFY_EMAIL', '')
        self.sender_name = getattr(settings, 'EMAIL_SENDER_NAME', '物流获客AI')
    
    @property
    def is_configured(self) -> bool:
        """检查邮件服务是否已配置"""
        return bool(
            self.smtp_host and 
            self.smtp_user and 
            self.smtp_password and 
            self.notify_email
        )
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            to_emails: 收件人列表
            subject: 邮件主题
            html_content: HTML内容
            text_content: 纯文本内容（可选）
        
        Returns:
            发送结果
        """
        if not self.is_configured:
            logger.warning("邮件服务未配置，跳过发送")
            return {"status": "skipped", "message": "邮件服务未配置"}
        
        try:
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
