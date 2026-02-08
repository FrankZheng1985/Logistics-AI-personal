"""
EmailSkill - 邮件管理技能

职责：
- 查询/阅读未读邮件
- 深度分析邮件
- 发送邮件
- 同步邮件
- 管理邮箱账户
"""
from typing import Dict, Any
from loguru import logger

from app.skills.base import BaseSkill, SkillRegistry


class EmailSkill(BaseSkill):
    """邮件管理技能"""

    name = "email"
    description = "邮件管理：查询、阅读、发送、同步邮件，管理邮箱账户"
    tool_names = [
        "read_emails",
        "send_email",
        "sync_emails",
        "manage_email_account",
    ]

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        handlers = {
            "read_emails": self._handle_read_emails,
            "send_email": self._handle_send_email,
            "sync_emails": self._handle_sync_emails,
            "manage_email_account": self._handle_manage_email_account,
        }
        handler = handlers.get(tool_name)
        if handler:
            return await handler(message=message, user_id=user_id, args=args)
        return self._err(f"未知工具: {tool_name}")

    # ==================== 读取邮件 ====================

    async def _handle_read_emails(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """查询未读邮件 + 深度分析"""
        from app.services.multi_email_service import multi_email_service

        await self.log_step("search", "查询邮件", "获取未读邮件")

        try:
            summary = await multi_email_service.get_unread_summary()

            if summary.get("total_unread", 0) == 0:
                return self._ok("邮箱里没有新邮件呢，挺清净的~")

            # 判断是否需要深度分析（包含"详细"、"内容"等关键词）
            deep_keywords = ["详细", "内容", "正文", "看看", "读", "分析", "深度"]
            need_deep = any(kw in message for kw in deep_keywords)

            if need_deep:
                return await self._deep_read_emails(summary)

            # 简单汇总
            lines = [f"未读邮件汇总"]

            for account in summary["accounts"]:
                if account["unread_count"] > 0:
                    lines.append(f"\n{account['name']} ({account['unread_count']}封)")
                    for email in account["recent_emails"][:3]:
                        sender = email["from_name"] or email["from_address"]
                        subject = email["subject"][:20] + "..." if len(email["subject"]) > 20 else email["subject"]
                        lines.append(f"  • {sender}: {subject}")

            lines.append(f"\n共{summary['total_unread']}封未读")
            return self._ok("\n".join(lines))

        except Exception as e:
            logger.error(f"[EmailSkill] 查询邮件失败: {e}")
            return self._ok("邮件查询暂时不可用，请稍后再试。")

    async def _deep_read_emails(self, summary: Dict) -> Dict[str, Any]:
        """深度阅读邮件 - 分类、摘要、建议"""
        try:
            from app.services.email_ai_service import email_ai_service

            all_emails = []
            for account in summary.get("accounts", []):
                for email in account.get("recent_emails", []):
                    body_content = email.get("body_text") or email.get("body_preview", "")
                    if len(body_content) > 2000:
                        body_content = body_content[:2000] + "..."

                    all_emails.append({
                        "from": email.get("from_name") or email.get("from_address", ""),
                        "subject": email.get("subject", ""),
                        "body": body_content,
                        "date": email.get("date", "")
                    })

            brief = await email_ai_service.generate_daily_email_brief(all_emails)
            return self._ok(brief)

        except Exception as e:
            logger.error(f"[EmailSkill] 邮件深度阅读失败: {e}")
            return self._ok("邮件服务暂时连不上，我稍后帮您重试一下~")

    # ==================== 发送邮件 ====================

    async def _handle_send_email(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """通过指定邮箱发送邮件"""
        from app.services.multi_email_service import multi_email_service

        args = args or {}
        to_emails = args.get("to_emails", [])
        subject = args.get("subject", "")
        body = args.get("body", "")
        account_name = args.get("account_name")

        if not to_emails or not subject or not body:
            return self._err("收件人、主题、正文都不能为空")

        try:
            accounts = await multi_email_service.get_email_accounts()
            if not accounts:
                return self._err("还没有配置邮箱，请先添加一个邮箱账户")

            target_account = None
            if account_name:
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target_account = acc
                        break

            if not target_account:
                target_account = next((a for a in accounts if a.get("is_default")), accounts[0])

            body_html = body.replace("\n", "<br>")

            result = await multi_email_service.send_email(
                account_id=target_account["id"],
                to_emails=to_emails,
                subject=subject,
                body_html=body_html,
                body_text=body,
            )

            if result.get("success"):
                return self._ok(
                    f"邮件已通过 {target_account['email_address']} 发送给 {', '.join(to_emails)}",
                    from_account=target_account["email_address"],
                )
            else:
                return self._err(f"发送失败: {result.get('error', '未知错误')}")

        except Exception as e:
            logger.error(f"[EmailSkill] 发送邮件失败: {e}")
            return self._err(f"发送邮件出错: {str(e)}")

    # ==================== 同步邮件 ====================

    async def _handle_sync_emails(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """同步邮箱邮件"""
        from app.services.multi_email_service import multi_email_service

        args = args or {}
        account_name = args.get("account_name")

        try:
            if account_name:
                accounts = await multi_email_service.get_email_accounts()
                target = None
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target = acc
                        break

                if not target:
                    return self._err(f"没找到名为 '{account_name}' 的邮箱")

                result = await multi_email_service.sync_account_emails(target["id"])
                if result.get("success"):
                    return self._ok(
                        f"{target['name']} 同步完成，新增 {result.get('new_count', 0)} 封邮件",
                        new_count=result.get("new_count", 0),
                    )
                else:
                    return self._err(f"同步失败: {result.get('error', '')}")
            else:
                result = await multi_email_service.sync_all_accounts()
                total_new = sum(
                    r["result"].get("new_count", 0)
                    for r in result.get("results", [])
                    if r["result"].get("success")
                )
                return self._ok(
                    f"已同步 {result['total_accounts']} 个邮箱，共新增 {total_new} 封邮件",
                    total_new=total_new,
                    accounts_synced=result["total_accounts"],
                )

        except Exception as e:
            logger.error(f"[EmailSkill] 同步邮件失败: {e}")
            return self._err(f"同步出错: {str(e)}")

    # ==================== 管理邮箱账户 ====================

    async def _handle_manage_email_account(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """管理邮箱账户（添加/查看/删除/测试）"""
        from app.services.multi_email_service import multi_email_service

        args = args or {}
        action = args.get("action", "list")

        try:
            if action == "list":
                accounts = await multi_email_service.get_email_accounts(active_only=False)
                if not accounts:
                    return self._ok("还没有配置任何邮箱", accounts=[])

                account_list = []
                for acc in accounts:
                    account_list.append({
                        "name": acc["name"],
                        "email": acc["email_address"],
                        "provider": acc["provider"],
                        "sync_enabled": acc["sync_enabled"],
                        "is_default": acc.get("is_default", False),
                    })
                return self._ok(
                    f"共有 {len(accounts)} 个邮箱账户",
                    accounts=account_list,
                )

            elif action == "add":
                name = args.get("name", "")
                email_address = args.get("email_address", "")
                password = args.get("password", "")
                provider = args.get("provider", "other")

                if not email_address or not password:
                    return self._err("添加邮箱需要提供邮箱地址和密码")

                if not name:
                    name = email_address.split("@")[0] + "邮箱"

                result = await multi_email_service.add_email_account(
                    name=name,
                    email_address=email_address,
                    provider=provider,
                    imap_password=password,
                    smtp_password=password,
                )

                if result.get("success"):
                    await multi_email_service.update_email_account(
                        result["account_id"], sync_enabled=True
                    )
                    return self._ok(
                        f"邮箱 {email_address} ({name}) 添加成功，已启用自动同步",
                        account_id=result["account_id"],
                    )
                else:
                    return self._err(f"添加失败: {result.get('error', '')}")

            elif action == "delete":
                account_name = args.get("account_name", "")
                if not account_name:
                    return self._err("请指定要删除的邮箱名称")

                accounts = await multi_email_service.get_email_accounts(active_only=False)
                target = None
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target = acc
                        break

                if not target:
                    return self._err(f"没找到名为 '{account_name}' 的邮箱")

                await multi_email_service.delete_email_account(target["id"])
                return self._ok(f"邮箱 {target['email_address']} 已删除")

            elif action == "test":
                account_name = args.get("account_name", "")
                accounts = await multi_email_service.get_email_accounts()
                target = None
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target = acc
                        break

                if not target:
                    return self._err(f"没找到名为 '{account_name}' 的邮箱")

                result = await multi_email_service.test_email_account(target["id"])
                if result.get("success"):
                    return self._ok(f"邮箱 {target['email_address']} 连接正常（收发都OK）")
                else:
                    imap_ok = result.get("imap", {}).get("success", False)
                    smtp_ok = result.get("smtp", {}).get("success", False)
                    issues = []
                    if not imap_ok:
                        issues.append(f"收件(IMAP)失败: {result.get('imap', {}).get('error', '')}")
                    if not smtp_ok:
                        issues.append(f"发件(SMTP)失败: {result.get('smtp', {}).get('error', '')}")
                    return self._err(f"邮箱连接有问题: {'; '.join(issues)}")

            else:
                return self._err(f"未知操作: {action}")

        except Exception as e:
            logger.error(f"[EmailSkill] 邮箱管理操作失败: {e}")
            return self._err(f"操作失败: {str(e)}")


# 注册
SkillRegistry.register(EmailSkill())
