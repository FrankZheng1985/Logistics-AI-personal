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
    description = "邮件管理：查询、阅读、发送、同步邮件，管理邮箱账户，分析邮件附件"
    tool_names = [
        "read_emails",
        "send_email",
        "sync_emails",
        "manage_email_account",
        "analyze_email_attachment",  # 新增：分析邮件附件
        "ignore_email",  # 新增：忽略邮件
    ]

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        handlers = {
            "read_emails": self._handle_read_emails,
            "send_email": self._handle_send_email,
            "sync_emails": self._handle_sync_emails,
            "manage_email_account": self._handle_manage_email_account,
            "analyze_email_attachment": self._handle_analyze_attachment,  # 新增
            "ignore_email": self._handle_ignore_email,  # 新增
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

    # ==================== 分析邮件附件 ====================

    async def _handle_analyze_attachment(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """
        分析邮件中的附件文档
        
        功能：
        1. 根据关键词搜索邮件
        2. 下载附件
        3. 解析文档内容
        4. 用 LLM 进行专业分析
        """
        from app.services.multi_email_service import multi_email_service
        from app.services.document_service import document_service
        from app.core.llm import chat_completion
        import os

        args = args or {}
        search_keyword = args.get("search_keyword", "")
        email_id = args.get("email_id")
        analysis_focus = args.get("analysis_focus", "")

        await self.log_step("search", "搜索邮件附件", f"关键词: {search_keyword or '最近附件'}")

        try:
            # 1. 查找带附件的邮件
            from app.models.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as db:
                if email_id:
                    # 直接用 ID 查找
                    result = await db.execute(
                        text("""
                            SELECT id, subject, from_name, from_address, attachment_names, message_id, account_id
                            FROM email_cache 
                            WHERE id = :email_id AND has_attachments = true
                        """),
                        {"email_id": email_id}
                    )
                elif search_keyword:
                    # 用关键词搜索
                    result = await db.execute(
                        text("""
                            SELECT id, subject, from_name, from_address, attachment_names, message_id, account_id
                            FROM email_cache 
                            WHERE has_attachments = true 
                              AND (subject ILIKE :kw OR array_to_string(attachment_names, ',') ILIKE :kw)
                            ORDER BY received_at DESC
                            LIMIT 1
                        """),
                        {"kw": f"%{search_keyword}%"}
                    )
                else:
                    # 获取最近一封带附件的邮件
                    result = await db.execute(
                        text("""
                            SELECT id, subject, from_name, from_address, attachment_names, message_id, account_id
                            FROM email_cache 
                            WHERE has_attachments = true
                            ORDER BY received_at DESC
                            LIMIT 1
                        """)
                    )

                row = result.fetchone()

            if not row:
                return self._err(f"没找到{'包含\"' + search_keyword + '\"的' if search_keyword else ''}带附件的邮件")

            email_db_id = str(row[0])
            subject = row[1]
            from_name = row[2] or row[3]
            attachment_names = row[4] or []

            await self.log_step("download", "下载附件", f"邮件: {subject}")

            # 2. 下载附件
            download_result = await multi_email_service.download_attachments(
                email_db_id,
                save_dir="/tmp/maria_attachments"
            )

            if not download_result.get("success"):
                return self._err(f"附件下载失败: {download_result.get('error', '未知错误')}")

            attachments = download_result.get("attachments", [])
            if not attachments:
                return self._err("邮件中没有可下载的附件")

            # 3. 读取并分析每个附件
            analysis_results = []

            for att in attachments:
                filename = att.get("filename", "未知文件")
                filepath = att.get("path")
                
                # 只处理文档类型
                if not filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
                    analysis_results.append(f"**{filename}**: 非文档类型，跳过分析")
                    continue

                await self.log_step("analyze", "分析文档", filename)

                # 读取文档内容
                doc_result = await document_service.read_document(filepath, filename)

                if not doc_result.get("success"):
                    analysis_results.append(f"**{filename}**: 无法读取 - {doc_result.get('error', '格式不支持')}")
                    continue

                content = doc_result.get("content", "")
                word_count = len(content)

                if word_count < 50:
                    analysis_results.append(f"**{filename}**: 内容太少（{word_count}字），无法分析")
                    continue

                # 4. 判断文档类型并构建分析提示词
                filename_lower = filename.lower()
                is_contract = any(kw in filename_lower or kw in subject.lower() 
                                for kw in ["合同", "协议", "contract", "agreement"])
                is_finance = any(kw in filename_lower for kw in ["发票", "invoice", "财务", "报表"])
                is_logistics = any(kw in filename_lower or kw in subject.lower() 
                                 for kw in ["运输", "物流", "提单", "报关", "清关", "transport", "shipping"])

                if is_contract:
                    prompt = f"""【合同法专家模式】请以资深合同律师的视角分析以下合同：

📄 文件名：{filename}
📧 邮件主题：{subject}
👤 发件人：{from_name}
{f'🎯 分析重点：{analysis_focus}' if analysis_focus else ''}

📝 合同内容：
{content[:15000]}

---
请分析：
1. 合同类型和主要条款概览
2. 关键商业条款（价格、付款、期限）
3. 风险条款识别（违约、责任限制、不可抗力）
4. 对我方的利弊分析
5. 修改建议"""
                elif is_logistics:
                    prompt = f"""【跨境物流专家模式】请以国际物流专家的视角分析：

📄 文件名：{filename}
📧 邮件主题：{subject}
👤 发件人：{from_name}
{f'🎯 分析重点：{analysis_focus}' if analysis_focus else ''}

📝 文档内容：
{content[:15000]}

---
请分析：
1. 文档类型和关键信息
2. 运输条款/贸易条款
3. 潜在风险和注意事项
4. 后续需要跟进的事项"""
                else:
                    prompt = f"""请分析以下文档：

📄 文件名：{filename}
📧 邮件主题：{subject}
👤 发件人：{from_name}
{f'🎯 分析重点：{analysis_focus}' if analysis_focus else ''}

📝 文档内容：
{content[:15000]}

---
请分析：
1. 文档的主要内容和目的
2. 关键信息摘要
3. 需要关注或决策的事项
4. 建议的处理方式"""

                # 5. 调用 LLM 分析
                try:
                    import asyncio
                    
                    # 选择合适的模型
                    if is_contract:
                        model_preference = "legal"
                    elif is_finance:
                        model_preference = "finance"
                    elif is_logistics:
                        model_preference = "reasoning"
                    else:
                        model_preference = None

                    response = await asyncio.wait_for(
                        chat_completion(
                            messages=[{"role": "user", "content": prompt}],
                            model_preference=model_preference,
                            use_advanced=True
                        ),
                        timeout=120
                    )

                    if isinstance(response, str):
                        analysis = response
                    elif isinstance(response, dict):
                        analysis = response.get("content", str(response))
                    else:
                        analysis = str(response)

                    analysis_results.append(f"## 📄 {filename}（{word_count}字）\n\n{analysis}")

                    # 保存到邮件上下文（以便后续引用）
                    try:
                        from app.services.email_context_service import email_context_service
                        
                        doc_type = "contract" if is_contract else ("logistics" if is_logistics else "general")
                        await email_context_service.save_email_context(
                            user_id=user_id or "Frank.Z",
                            email_id=email_db_id,
                            subject=subject,
                            from_address=row[3],
                            from_name=from_name,
                            attachment_name=filename,
                            attachment_content=content,
                            analysis_result=analysis,
                            doc_type=doc_type
                        )
                    except Exception as ctx_err:
                        logger.warning(f"[EmailSkill] 保存邮件上下文失败: {ctx_err}")

                except asyncio.TimeoutError:
                    analysis_results.append(f"**{filename}**: 分析超时（文档可能太长）")
                except Exception as llm_err:
                    logger.error(f"[EmailSkill] LLM分析失败: {llm_err}")
                    analysis_results.append(f"**{filename}**: 分析出错 - {str(llm_err)[:100]}")

            # 6. 返回结果
            if not analysis_results:
                return self._err("没有可分析的文档附件")

            return self._ok(f"📧 **{subject}** 附件分析\n\n" + "\n\n---\n\n".join(analysis_results))

        except Exception as e:
            logger.error(f"[EmailSkill] 分析附件失败: {e}", exc_info=True)
            return self._err(f"分析附件失败: {str(e)}")

    # ==================== 忽略邮件 ====================

    async def _handle_ignore_email(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """
        将邮件加入忽略列表，以后不再提醒
        当用户说"不处理"、"已读"、"过滤"等时调用
        """
        from app.scheduler.maria_tasks import ignore_email_by_user

        args = args or {}
        identifier = args.get("identifier", "")
        reason = args.get("reason", "用户要求忽略")

        if not identifier:
            # 如果没有指定，尝试从消息中提取关键词
            return self._err("请告诉我要忽略哪些邮件？可以是邮件主题关键词或发件人邮箱。")

        await self.log_step("action", "添加忽略规则", f"忽略: {identifier}")

        try:
            result = await ignore_email_by_user(identifier)
            
            if result.get("success"):
                return self._ok(f"好的，已将「{identifier}」加入忽略列表，以后不会再提醒您这类邮件了。")
            else:
                return self._err(result.get("message", "添加忽略失败"))
                
        except Exception as e:
            logger.error(f"[EmailSkill] 忽略邮件失败: {e}")
            return self._err(f"忽略邮件失败: {str(e)}")


# 注册
SkillRegistry.register(EmailSkill())
