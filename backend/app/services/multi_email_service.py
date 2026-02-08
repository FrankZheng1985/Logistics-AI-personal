"""
多邮箱管理服务
支持多个邮箱账户的统一管理、邮件同步、邮件发送
"""
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parseaddr, formataddr
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import text
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from app.models.database import AsyncSessionLocal
from app.core.config import settings

# 线程池用于同步IMAP操作
_executor = ThreadPoolExecutor(max_workers=5)


class MultiEmailService:
    """多邮箱管理服务"""
    
    # 常见邮箱服务商的默认配置
    PROVIDER_CONFIGS = {
        "qq_enterprise": {
            "imap_host": "imap.exmail.qq.com",
            "imap_port": 993,
            "smtp_host": "smtp.exmail.qq.com",
            "smtp_port": 465,
            "imap_ssl": True,
            "smtp_ssl": True
        },
        "aliyun": {
            "imap_host": "imap.qiye.aliyun.com",
            "imap_port": 993,
            "smtp_host": "smtp.qiye.aliyun.com",
            "smtp_port": 465,
            "imap_ssl": True,
            "smtp_ssl": True
        },
        "163": {
            "imap_host": "imap.163.com",
            "imap_port": 993,
            "smtp_host": "smtp.163.com",
            "smtp_port": 465,
            "imap_ssl": True,
            "smtp_ssl": True
        },
        "gmail": {
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "imap_ssl": True,
            "smtp_ssl": False  # Gmail使用STARTTLS
        },
        "outlook": {
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "imap_ssl": True,
            "smtp_ssl": False
        },
        "qq": {
            "imap_host": "imap.qq.com",
            "imap_port": 993,
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
            "imap_ssl": True,
            "smtp_ssl": True
        },
        "icloud": {
            "imap_host": "imap.mail.me.com",
            "imap_port": 993,
            "smtp_host": "smtp.mail.me.com",
            "smtp_port": 587,
            "imap_ssl": True,
            "smtp_ssl": False  # iCloud使用STARTTLS
        }
    }
    
    # ==================== 邮箱账户管理 ====================
    
    async def add_email_account(
        self,
        name: str,
        email_address: str,
        provider: str = "other",
        imap_host: Optional[str] = None,
        imap_port: int = 993,
        imap_user: Optional[str] = None,
        imap_password: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 465,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        imap_ssl: bool = True,
        smtp_ssl: bool = True
    ) -> Dict[str, Any]:
        """添加邮箱账户"""
        # 如果选择了已知服务商，自动填充配置
        if provider in self.PROVIDER_CONFIGS:
            config = self.PROVIDER_CONFIGS[provider]
            imap_host = imap_host or config["imap_host"]
            imap_port = imap_port or config["imap_port"]
            smtp_host = smtp_host or config["smtp_host"]
            smtp_port = smtp_port or config["smtp_port"]
            imap_ssl = config["imap_ssl"]
            smtp_ssl = config["smtp_ssl"]
        
        # 默认用户名为邮箱地址
        imap_user = imap_user or email_address
        smtp_user = smtp_user or email_address
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO email_accounts 
                        (name, email_address, provider,
                         imap_host, imap_port, imap_user, imap_password, imap_ssl,
                         smtp_host, smtp_port, smtp_user, smtp_password, smtp_ssl)
                        VALUES 
                        (:name, :email_address, :provider,
                         :imap_host, :imap_port, :imap_user, :imap_password, :imap_ssl,
                         :smtp_host, :smtp_port, :smtp_user, :smtp_password, :smtp_ssl)
                        RETURNING id
                    """),
                    {
                        "name": name,
                        "email_address": email_address,
                        "provider": provider,
                        "imap_host": imap_host,
                        "imap_port": imap_port,
                        "imap_user": imap_user,
                        "imap_password": imap_password,  # TODO: 加密存储
                        "imap_ssl": imap_ssl,
                        "smtp_host": smtp_host,
                        "smtp_port": smtp_port,
                        "smtp_user": smtp_user,
                        "smtp_password": smtp_password,  # TODO: 加密存储
                        "smtp_ssl": smtp_ssl
                    }
                )
                row = result.fetchone()
                await db.commit()
                
                logger.info(f"添加邮箱账户成功: {name} ({email_address})")
                return {"success": True, "account_id": str(row[0])}
                
        except Exception as e:
            logger.error(f"添加邮箱账户失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_email_accounts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取邮箱账户列表"""
        active_filter = "WHERE is_active = TRUE" if active_only else ""
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(f"""
                    SELECT id, name, email_address, provider, 
                           sync_enabled, last_sync_at, last_sync_error,
                           is_default, is_active
                    FROM email_accounts
                    {active_filter}
                    ORDER BY is_default DESC, name ASC
                """)
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "name": row[1],
                "email_address": row[2],
                "provider": row[3],
                "sync_enabled": row[4],
                "last_sync_at": row[5].isoformat() if row[5] else None,
                "last_sync_error": row[6],
                "is_default": row[7],
                "is_active": row[8]
            }
            for row in rows
        ]
    
    async def get_email_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取邮箱账户详情（包含配置信息）"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, name, email_address, provider,
                           imap_host, imap_port, imap_user, imap_ssl,
                           smtp_host, smtp_port, smtp_user, smtp_ssl,
                           sync_enabled, sync_interval_minutes, is_default
                    FROM email_accounts
                    WHERE id = :id
                """),
                {"id": account_id}
            )
            row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "email_address": row[2],
            "provider": row[3],
            "imap_host": row[4],
            "imap_port": row[5],
            "imap_user": row[6],
            "imap_ssl": row[7],
            "smtp_host": row[8],
            "smtp_port": row[9],
            "smtp_user": row[10],
            "smtp_ssl": row[11],
            "sync_enabled": row[12],
            "sync_interval_minutes": row[13],
            "is_default": row[14]
        }
    
    async def update_email_account(
        self, 
        account_id: str, 
        **kwargs
    ) -> bool:
        """更新邮箱账户配置"""
        allowed_fields = [
            "name", "imap_host", "imap_port", "imap_user", "imap_password", "imap_ssl",
            "smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_ssl",
            "sync_enabled", "sync_interval_minutes", "is_active", "is_default"
        ]
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        if not updates:
            return True
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        updates["id"] = account_id
        
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"UPDATE email_accounts SET {set_clause}, updated_at = NOW() WHERE id = :id"),
                    updates
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"更新邮箱账户失败: {e}")
            return False
    
    async def delete_email_account(self, account_id: str) -> bool:
        """删除邮箱账户"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("DELETE FROM email_accounts WHERE id = :id"),
                    {"id": account_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"删除邮箱账户失败: {e}")
            return False
    
    async def test_email_account(self, account_id: str) -> Dict[str, Any]:
        """测试邮箱账户连接"""
        account = await self._get_account_with_password(account_id)
        if not account:
            return {"success": False, "error": "账户不存在"}
        
        # 测试IMAP连接
        imap_result = await self._test_imap_connection(account)
        
        # 测试SMTP连接
        smtp_result = await self._test_smtp_connection(account)
        
        return {
            "success": imap_result["success"] and smtp_result["success"],
            "imap": imap_result,
            "smtp": smtp_result
        }
    
    async def _test_imap_connection(self, account: Dict) -> Dict[str, Any]:
        """测试IMAP连接"""
        def _test():
            try:
                if account["imap_ssl"]:
                    conn = imaplib.IMAP4_SSL(account["imap_host"], account["imap_port"])
                else:
                    conn = imaplib.IMAP4(account["imap_host"], account["imap_port"])
                
                conn.login(account["imap_user"], account["imap_password"])
                conn.select("INBOX")
                conn.logout()
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _test)
    
    async def _test_smtp_connection(self, account: Dict) -> Dict[str, Any]:
        """测试SMTP连接"""
        def _test():
            try:
                if account["smtp_ssl"]:
                    context = ssl.create_default_context()
                    conn = smtplib.SMTP_SSL(account["smtp_host"], account["smtp_port"], context=context)
                else:
                    conn = smtplib.SMTP(account["smtp_host"], account["smtp_port"])
                    conn.starttls()
                
                conn.login(account["smtp_user"], account["smtp_password"])
                conn.quit()
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _test)
    
    # ==================== 邮件同步 ====================
    
    async def sync_account_emails(
        self, 
        account_id: str,
        days_back: int = 7,
        max_emails: int = 100
    ) -> Dict[str, Any]:
        """同步指定账户的邮件"""
        account = await self._get_account_with_password(account_id)
        if not account:
            return {"success": False, "error": "账户不存在"}
        
        logger.info(f"开始同步邮件: {account['name']} ({account['email_address']})")
        
        try:
            # 执行同步
            result = await self._fetch_emails_imap(account, days_back, max_emails)
            
            # 更新同步状态
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE email_accounts 
                        SET last_sync_at = NOW(), last_sync_error = NULL
                        WHERE id = :id
                    """),
                    {"id": account_id}
                )
                await db.commit()
            
            logger.info(f"邮件同步完成: {account['name']}, 新增 {result['new_count']} 封")
            return result
            
        except Exception as e:
            logger.error(f"同步邮件失败: {account['name']} - {e}")
            
            # 记录错误
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE email_accounts 
                        SET last_sync_error = :error
                        WHERE id = :id
                    """),
                    {"id": account_id, "error": str(e)}
                )
                await db.commit()
            
            return {"success": False, "error": str(e)}
    
    async def _fetch_emails_imap(
        self, 
        account: Dict, 
        days_back: int,
        max_emails: int
    ) -> Dict[str, Any]:
        """从IMAP服务器获取邮件"""
        def _fetch():
            emails = []
            
            if account["imap_ssl"]:
                conn = imaplib.IMAP4_SSL(account["imap_host"], account["imap_port"])
            else:
                conn = imaplib.IMAP4(account["imap_host"], account["imap_port"])
            
            try:
                conn.login(account["imap_user"], account["imap_password"])
                conn.select("INBOX")
                
                # 搜索最近N天的邮件（强制英文月份格式 + 字节串编码，避免中文环境locale和编码问题）
                date_obj = datetime.now() - timedelta(days=days_back)
                month_names_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                since_date = f"{date_obj.day:02d}-{month_names_en[date_obj.month - 1]}-{date_obj.year}"
                # IMAP search需要bytes或ASCII字符串，明确编码为ASCII
                search_criterion = f'(SINCE {since_date})'.encode('ascii')
                _, message_numbers = conn.search(None, search_criterion)
                
                email_ids = message_numbers[0].split()[-max_emails:]  # 取最新的N封
                
                for email_id in email_ids:
                    try:
                        # 优先用 BODY.PEEK[]（不标记已读），iCloud不支持RFC822
                        _, msg_data = conn.fetch(email_id, "(BODY.PEEK[])")
                        
                        # 从返回数据中提取邮件bytes
                        email_body = None
                        for part in msg_data:
                            if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes):
                                email_body = part[1]
                                break
                        
                        if not email_body:
                            # 降级尝试 RFC822
                            _, msg_data = conn.fetch(email_id, "(RFC822)")
                            for part in msg_data:
                                if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes):
                                    email_body = part[1]
                                    break
                        
                        if not email_body:
                            continue
                        
                        msg = email.message_from_bytes(email_body)
                        
                        # 解析邮件
                        parsed = self._parse_email(msg)
                        if parsed:
                            emails.append(parsed)
                    except Exception as fetch_err:
                        logger.warning(f"获取单封邮件失败: {fetch_err}")
                        continue
                
                conn.logout()
                
            except Exception as e:
                if conn:
                    try:
                        conn.logout()
                    except:
                        pass
                raise e
            
            return emails
        
        loop = asyncio.get_event_loop()
        emails = await loop.run_in_executor(_executor, _fetch)
        
        # 保存到数据库
        new_count = 0
        for email_data in emails:
            saved = await self._save_email_to_cache(account["id"], email_data)
            if saved:
                new_count += 1
        
        return {
            "success": True,
            "total_fetched": len(emails),
            "new_count": new_count
        }
    
    def _parse_email(self, msg) -> Optional[Dict[str, Any]]:
        """解析邮件内容"""
        try:
            # 解析Message-ID
            message_id = msg.get("Message-ID", "")
            if not message_id:
                return None
            
            # 解析发件人
            from_header = msg.get("From", "")
            from_name, from_address = parseaddr(from_header)
            from_name = self._decode_header(from_name)
            
            # 解析收件人
            to_header = msg.get("To", "")
            
            # 解析主题
            subject = self._decode_header(msg.get("Subject", ""))
            
            # 解析日期
            date_str = msg.get("Date", "")
            received_at = None
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_str)
                except:
                    pass
            
            # 解析正文
            body_text = ""
            body_html = ""
            has_attachments = False
            attachment_names = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    if "attachment" in content_disposition:
                        has_attachments = True
                        filename = part.get_filename()
                        if filename:
                            attachment_names.append(self._decode_header(filename))
                    elif content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text = payload.decode("utf-8", errors="ignore")
                    elif content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_html = payload.decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode("utf-8", errors="ignore")
            
            return {
                "message_id": message_id,
                "subject": subject,
                "from_address": from_address,
                "from_name": from_name,
                "to_addresses": to_header,
                "body_text": body_text[:50000] if body_text else "",  # 限制长度
                "body_html": body_html[:100000] if body_html else "",
                "has_attachments": has_attachments,
                "attachment_names": attachment_names,
                "received_at": received_at
            }
            
        except Exception as e:
            logger.warning(f"解析邮件失败: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """解码邮件头"""
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_string += part.decode(encoding or "utf-8", errors="ignore")
                else:
                    decoded_string += part
            return decoded_string
        except:
            return header_value
    
    async def _save_email_to_cache(
        self, 
        account_id: str, 
        email_data: Dict[str, Any]
    ) -> bool:
        """保存邮件到缓存表"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO email_cache 
                        (account_id, message_id, subject, from_address, from_name,
                         to_addresses, body_text, body_html, has_attachments, 
                         attachment_names, received_at)
                        VALUES 
                        (:account_id, :message_id, :subject, :from_address, :from_name,
                         :to_addresses, :body_text, :body_html, :has_attachments,
                         :attachment_names, :received_at)
                        ON CONFLICT (account_id, message_id) DO NOTHING
                    """),
                    {
                        "account_id": account_id,
                        "message_id": email_data["message_id"],
                        "subject": email_data["subject"],
                        "from_address": email_data["from_address"],
                        "from_name": email_data["from_name"],
                        "to_addresses": email_data["to_addresses"],
                        "body_text": email_data["body_text"],
                        "body_html": email_data["body_html"],
                        "has_attachments": email_data["has_attachments"],
                        "attachment_names": email_data["attachment_names"],
                        "received_at": email_data["received_at"]
                    }
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"保存邮件缓存失败: {e}")
            return False
    
    async def sync_all_accounts(self) -> Dict[str, Any]:
        """同步所有启用同步的邮箱账户"""
        accounts = await self.get_email_accounts(active_only=True)
        sync_accounts = [a for a in accounts if a["sync_enabled"]]
        
        results = []
        for account in sync_accounts:
            result = await self.sync_account_emails(account["id"])
            results.append({
                "account": account["name"],
                "email": account["email_address"],
                "result": result
            })
        
        return {
            "total_accounts": len(sync_accounts),
            "results": results
        }
    
    # ==================== 邮件查询 ====================
    
    async def get_unread_summary(self) -> Dict[str, Any]:
        """获取所有邮箱的未读邮件摘要"""
        async with AsyncSessionLocal() as db:
            # 获取每个账户的未读邮件统计
            result = await db.execute(
                text("""
                    SELECT 
                        ea.id, ea.name, ea.email_address,
                        COUNT(CASE WHEN ec.is_read = FALSE THEN 1 END) as unread_count
                    FROM email_accounts ea
                    LEFT JOIN email_cache ec ON ea.id = ec.account_id
                    WHERE ea.is_active = TRUE
                    GROUP BY ea.id, ea.name, ea.email_address
                    ORDER BY ea.is_default DESC, ea.name ASC
                """)
            )
            account_stats = result.fetchall()
        
        total_unread = 0
        accounts = []
        
        for row in account_stats:
            account_id = str(row[0])
            unread = row[3] or 0
            total_unread += unread
            
            # 获取最近的未读邮件
            recent_emails = await self.get_unread_emails(account_id, limit=5)
            
            accounts.append({
                "id": account_id,
                "name": row[1],
                "email_address": row[2],
                "unread_count": unread,
                "recent_emails": recent_emails
            })
        
        return {
            "total_unread": total_unread,
            "accounts": accounts
        }
    
    async def get_unread_emails(
        self, 
        account_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取未读邮件列表"""
        account_filter = "AND ec.account_id = :account_id" if account_id else ""
        params = {"limit": limit}
        if account_id:
            params["account_id"] = account_id
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(f"""
                    SELECT ec.id, ec.subject, ec.from_address, ec.from_name,
                           ec.received_at, ec.has_attachments, ec.is_important,
                           ea.name as account_name
                    FROM email_cache ec
                    JOIN email_accounts ea ON ec.account_id = ea.id
                    WHERE ec.is_read = FALSE
                    {account_filter}
                    ORDER BY ec.received_at DESC
                    LIMIT :limit
                """),
                params
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "subject": row[1],
                "from_address": row[2],
                "from_name": row[3],
                "received_at": row[4].isoformat() if row[4] else None,
                "has_attachments": row[5],
                "is_important": row[6],
                "account_name": row[7]
            }
            for row in rows
        ]
    
    async def get_email_detail(self, email_id: str) -> Optional[Dict[str, Any]]:
        """获取邮件详情"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT ec.*, ea.name as account_name, ea.email_address as account_email
                    FROM email_cache ec
                    JOIN email_accounts ea ON ec.account_id = ea.id
                    WHERE ec.id = :id
                """),
                {"id": email_id}
            )
            row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": str(row.id),
            "account_id": str(row.account_id),
            "account_name": row.account_name,
            "account_email": row.account_email,
            "message_id": row.message_id,
            "subject": row.subject,
            "from_address": row.from_address,
            "from_name": row.from_name,
            "to_addresses": row.to_addresses,
            "body_text": row.body_text,
            "body_html": row.body_html,
            "has_attachments": row.has_attachments,
            "attachment_names": row.attachment_names,
            "is_read": row.is_read,
            "is_important": row.is_important,
            "category": row.category,
            "received_at": row.received_at.isoformat() if row.received_at else None
        }
    
    async def mark_email_read(self, email_id: str) -> bool:
        """标记邮件已读"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("UPDATE email_cache SET is_read = TRUE WHERE id = :id"),
                    {"id": email_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"标记邮件已读失败: {e}")
            return False
    
    async def mark_email_important(self, email_id: str, important: bool = True) -> bool:
        """标记邮件重要"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("UPDATE email_cache SET is_important = :important WHERE id = :id"),
                    {"id": email_id, "important": important}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"标记邮件重要失败: {e}")
            return False
    
    # ==================== 邮件发送 ====================
    
    async def send_email(
        self,
        account_id: str,
        to_emails: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        reply_to_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """通过指定邮箱账户发送邮件"""
        account = await self._get_account_with_password(account_id)
        if not account:
            return {"success": False, "error": "邮箱账户不存在"}
        
        def _send():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((account["name"], account["email_address"]))
            msg["To"] = ", ".join(to_emails)
            
            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            
            if account["smtp_ssl"]:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(account["smtp_host"], account["smtp_port"], context=context) as server:
                    server.login(account["smtp_user"], account["smtp_password"])
                    server.sendmail(account["email_address"], to_emails, msg.as_string())
            else:
                with smtplib.SMTP(account["smtp_host"], account["smtp_port"]) as server:
                    server.starttls()
                    server.login(account["smtp_user"], account["smtp_password"])
                    server.sendmail(account["email_address"], to_emails, msg.as_string())
            
            return {"success": True}
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_executor, _send)
            
            # 记录发送操作
            if reply_to_id:
                await self._log_email_action(reply_to_id, account_id, "reply", {
                    "to": to_emails,
                    "subject": subject
                })
            
            logger.info(f"邮件发送成功: {account['email_address']} -> {to_emails}")
            return result
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _log_email_action(
        self, 
        email_id: str, 
        account_id: str, 
        action_type: str,
        action_data: Dict
    ):
        """记录邮件操作"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO email_actions (email_id, account_id, action_type, action_data)
                        VALUES (:email_id, :account_id, :action_type, :action_data)
                    """),
                    {
                        "email_id": email_id,
                        "account_id": account_id,
                        "action_type": action_type,
                        "action_data": json.dumps(action_data, ensure_ascii=False)
                    }
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"记录邮件操作失败: {e}")
    
    # ==================== 工具方法 ====================
    
    async def _get_account_with_password(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取邮箱账户（包含密码）"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, name, email_address, provider,
                           imap_host, imap_port, imap_user, imap_password, imap_ssl,
                           smtp_host, smtp_port, smtp_user, smtp_password, smtp_ssl
                    FROM email_accounts
                    WHERE id = :id
                """),
                {"id": account_id}
            )
            row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "email_address": row[2],
            "provider": row[3],
            "imap_host": row[4],
            "imap_port": row[5],
            "imap_user": row[6],
            "imap_password": row[7],
            "imap_ssl": row[8],
            "smtp_host": row[9],
            "smtp_port": row[10],
            "smtp_user": row[11],
            "smtp_password": row[12],
            "smtp_ssl": row[13]
        }


# 创建单例
multi_email_service = MultiEmailService()
