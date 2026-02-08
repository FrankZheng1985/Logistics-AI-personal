"""
NotionSkill - Notion 集成技能

职责：
- 在 Notion 中创建页面（方案、文档、项目计划等）
- 向已有页面追加内容（日报、会议纪要等）
- 搜索 Notion 工作空间中的内容
- Markdown 到 Notion Block 的智能转换
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from loguru import logger

from app.skills.base import BaseSkill, SkillRegistry


class NotionSkill(BaseSkill):
    """Notion 集成技能"""

    name = "notion"
    description = "在 Notion 中创建和管理文档、项目、方案，支持搜索和内容追加"
    tool_names = [
        "create_notion_page",
        "append_to_notion_page",
        "search_notion",
    ]

    def __init__(self, agent=None):
        super().__init__(agent)
        self._client = None

    def _get_client(self):
        """懒加载 Notion Client"""
        if self._client is None:
            from app.core.config import settings
            api_key = getattr(settings, 'NOTION_API_KEY', None)
            if not api_key:
                raise RuntimeError("NOTION_API_KEY 未配置，无法连接 Notion")
            from notion_client import Client
            self._client = Client(auth=api_key)
        return self._client

    def _get_root_page_id(self) -> str:
        """获取根页面 ID"""
        from app.core.config import settings
        page_id = getattr(settings, 'NOTION_ROOT_PAGE_ID', None)
        if not page_id:
            raise RuntimeError("NOTION_ROOT_PAGE_ID 未配置，请先设置 Notion 根页面")
        return page_id

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        """路由到具体处理方法"""
        handlers = {
            "create_notion_page": self._handle_create_page,
            "append_to_notion_page": self._handle_append_to_page,
            "search_notion": self._handle_search,
        }
        handler = handlers.get(tool_name)
        if handler:
            return await handler(args=args, message=message, user_id=user_id)
        return self._err(f"未知工具: {tool_name}")

    # ==================== 创建页面 ====================

    async def _handle_create_page(self, args: Dict, message: str, user_id: str) -> Dict[str, Any]:
        """在 Notion 中创建新页面"""
        title = args.get("title", "").strip()
        content = args.get("content", "").strip()
        page_type = args.get("page_type", "document")
        parent_page_id = args.get("parent_page_id", "")

        if not title:
            return self._err("请提供页面标题")

        await self.log_step("action", "创建 Notion 页面", title)

        # 如果没有给内容，用 LLM 生成
        if not content and message:
            await self.log_step("think", "正在生成内容", "用 AI 撰写文档...")
            generation_prompt = self._build_generation_prompt(title, page_type, message)
            content = await self.chat(
                generation_prompt,
                "你是一个专业的文档撰写助手。根据用户需求生成结构化的 Markdown 内容。"
                "使用清晰的标题层级（## ##）、列表、加粗等格式。内容要专业、完整、实用。"
                "不要在开头重复标题。直接输出正文内容。"
            )

        try:
            client = self._get_client()
            parent_id = parent_page_id or self._get_root_page_id()

            # 构建 Notion 页面属性
            page_properties = {
                "title": [{"text": {"content": title}}]
            }

            # 构建页面内容（Markdown -> Notion Blocks）
            children_blocks = self._markdown_to_blocks(content) if content else []

            # 添加页脚元数据
            children_blocks.append(self._make_divider())
            children_blocks.append(self._make_paragraph(
                f"由 Maria AI 创建于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                color="gray"
            ))

            # 创建页面
            new_page = client.pages.create(
                parent={"page_id": parent_id},
                properties=page_properties,
                children=children_blocks[:100],  # Notion API 限制每次最多100个block
            )

            page_id = new_page["id"]
            page_url = new_page.get("url", f"https://notion.so/{page_id.replace('-', '')}")

            # 如果 block 超过 100 个，分批追加
            if len(children_blocks) > 100:
                remaining = children_blocks[100:]
                for i in range(0, len(remaining), 100):
                    batch = remaining[i:i + 100]
                    client.blocks.children.append(
                        block_id=page_id,
                        children=batch,
                    )

            logger.info(f"[NotionSkill] 页面创建成功: {title} -> {page_url}")

            return self._ok(
                f"Notion 页面已创建：「{title}」\n链接：{page_url}",
                page_id=page_id,
                page_url=page_url,
            )

        except RuntimeError as e:
            return self._err(str(e))
        except Exception as e:
            logger.error(f"[NotionSkill] 创建页面失败: {e}")
            return self._err(f"创建 Notion 页面失败：{str(e)[:200]}")

    # ==================== 追加内容 ====================

    async def _handle_append_to_page(self, args: Dict, message: str, user_id: str) -> Dict[str, Any]:
        """向 Notion 页面追加内容"""
        page_id = args.get("page_id", "").strip()
        title_keyword = args.get("title_keyword", "").strip()
        content = args.get("content", "").strip()

        if not content:
            return self._err("请提供要追加的内容")

        await self.log_step("action", "追加 Notion 内容", content[:50])

        try:
            client = self._get_client()

            # 如果没有 page_id，通过标题搜索
            if not page_id and title_keyword:
                search_result = client.search(
                    query=title_keyword,
                    filter={"property": "object", "value": "page"},
                    page_size=1,
                )
                results = search_result.get("results", [])
                if not results:
                    return self._err(f"在 Notion 中找不到标题包含「{title_keyword}」的页面")
                page_id = results[0]["id"]

            if not page_id:
                return self._err("请提供 page_id 或标题关键词来定位页面")

            # Markdown -> Blocks
            blocks = self._markdown_to_blocks(content)

            # 添加时间分隔
            blocks.insert(0, self._make_divider())
            blocks.insert(1, self._make_paragraph(
                f"--- 追加于 {datetime.now().strftime('%Y-%m-%d %H:%M')} ---",
                color="gray"
            ))

            # 追加到页面
            client.blocks.children.append(
                block_id=page_id,
                children=blocks[:100],
            )

            logger.info(f"[NotionSkill] 内容追加成功: page_id={page_id}")
            return self._ok(f"内容已追加到 Notion 页面")

        except RuntimeError as e:
            return self._err(str(e))
        except Exception as e:
            logger.error(f"[NotionSkill] 追加内容失败: {e}")
            return self._err(f"追加失败：{str(e)[:200]}")

    # ==================== 搜索 ====================

    async def _handle_search(self, args: Dict, message: str, user_id: str) -> Dict[str, Any]:
        """搜索 Notion 工作空间"""
        query = args.get("query", "").strip() or message
        search_type = args.get("search_type", "page")

        if not query:
            return self._err("请提供搜索关键词")

        await self.log_step("search", "搜索 Notion", query)

        try:
            client = self._get_client()

            filter_obj = None
            if search_type in ("page", "database"):
                filter_obj = {"property": "object", "value": search_type}

            search_result = client.search(
                query=query,
                filter=filter_obj,
                page_size=5,
            )

            results = search_result.get("results", [])

            if not results:
                return self._ok(f"在 Notion 中没有找到「{query}」相关的内容")

            # 格式化搜索结果
            result_lines = []
            for item in results:
                obj_type = item.get("object", "unknown")
                item_id = item.get("id", "")
                url = item.get("url", "")

                # 提取标题
                title = self._extract_title(item)
                last_edited = item.get("last_edited_time", "")[:10]

                result_lines.append(f"• 「{title}」({obj_type}) - 更新于 {last_edited}")
                if url:
                    result_lines.append(f"  链接: {url}")

            context = f"""用户搜索：{query}
搜索结果（共{len(results)}条）：
{chr(10).join(result_lines)}"""

            # 用 LLM 生成自然语言回复
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。把 Notion 搜索结果用简洁口语告诉老板。不要用 markdown。"
            )

            return self._ok(smart_response, data={"results_count": len(results)})

        except RuntimeError as e:
            return self._err(str(e))
        except Exception as e:
            logger.error(f"[NotionSkill] 搜索失败: {e}")
            return self._err(f"搜索失败：{str(e)[:200]}")

    # ==================== Markdown -> Notion Blocks 转换引擎 ====================

    def _markdown_to_blocks(self, markdown_text: str) -> List[Dict]:
        """
        将 Markdown 文本转换为 Notion Block 列表
        
        支持：H1/H2/H3 标题、有序/无序列表、代码块、分割线、
              加粗、斜体、行内代码、普通段落、待办事项
        """
        blocks = []
        lines = markdown_text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 空行跳过
            if not stripped:
                i += 1
                continue

            # 代码块（```）
            if stripped.startswith("```"):
                language = stripped[3:].strip() or "plain text"
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # 跳过结束的 ```
                blocks.append(self._make_code_block("\n".join(code_lines), language))
                continue

            # 标题
            if stripped.startswith("### "):
                blocks.append(self._make_heading(stripped[4:], level=3))
                i += 1
                continue
            if stripped.startswith("## "):
                blocks.append(self._make_heading(stripped[3:], level=2))
                i += 1
                continue
            if stripped.startswith("# "):
                blocks.append(self._make_heading(stripped[2:], level=1))
                i += 1
                continue

            # 分割线
            if stripped in ("---", "***", "___"):
                blocks.append(self._make_divider())
                i += 1
                continue

            # 待办事项 (- [ ] / - [x])
            todo_match = re.match(r'^-\s*\[([ xX])\]\s*(.*)', stripped)
            if todo_match:
                checked = todo_match.group(1).lower() == 'x'
                text = todo_match.group(2)
                blocks.append(self._make_todo(text, checked))
                i += 1
                continue

            # 有序列表 (1. xxx)
            ol_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
            if ol_match:
                blocks.append(self._make_numbered_list(ol_match.group(2)))
                i += 1
                continue

            # 无序列表 (- xxx / * xxx)
            if stripped.startswith("- ") or stripped.startswith("* "):
                blocks.append(self._make_bulleted_list(stripped[2:]))
                i += 1
                continue

            # 引用 (> xxx)
            if stripped.startswith("> "):
                blocks.append(self._make_quote(stripped[2:]))
                i += 1
                continue

            # 普通段落
            blocks.append(self._make_paragraph(stripped))
            i += 1

        return blocks

    # ==================== Notion Block 构建器 ====================

    def _parse_rich_text(self, text: str) -> List[Dict]:
        """
        解析 Markdown 行内格式为 Notion rich_text 数组
        
        支持：**加粗**、*斜体*、`行内代码`
        """
        result = []
        # 用正则拆分: 加粗、斜体、行内代码
        pattern = r'(\*\*(.+?)\*\*|`(.+?)`|\*(.+?)\*)'
        last_end = 0

        for match in re.finditer(pattern, text):
            # 前缀普通文本
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    result.append({"type": "text", "text": {"content": plain}})

            full = match.group(0)
            if full.startswith("**"):
                # 加粗
                result.append({
                    "type": "text",
                    "text": {"content": match.group(2)},
                    "annotations": {"bold": True}
                })
            elif full.startswith("`"):
                # 行内代码
                result.append({
                    "type": "text",
                    "text": {"content": match.group(3)},
                    "annotations": {"code": True}
                })
            elif full.startswith("*"):
                # 斜体
                result.append({
                    "type": "text",
                    "text": {"content": match.group(4)},
                    "annotations": {"italic": True}
                })

            last_end = match.end()

        # 剩余普通文本
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                result.append({"type": "text", "text": {"content": remaining}})

        # 如果没有任何匹配，返回纯文本
        if not result:
            result.append({"type": "text", "text": {"content": text}})

        return result

    def _make_heading(self, text: str, level: int = 2) -> Dict:
        """创建标题 Block"""
        key = f"heading_{level}"
        return {
            "object": "block",
            "type": key,
            key: {"rich_text": self._parse_rich_text(text)},
        }

    def _make_paragraph(self, text: str, color: str = "default") -> Dict:
        """创建段落 Block"""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": self._parse_rich_text(text),
                "color": color,
            },
        }

    def _make_bulleted_list(self, text: str) -> Dict:
        """创建无序列表 Block"""
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _make_numbered_list(self, text: str) -> Dict:
        """创建有序列表 Block"""
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _make_todo(self, text: str, checked: bool = False) -> Dict:
        """创建待办事项 Block"""
        return {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": self._parse_rich_text(text),
                "checked": checked,
            },
        }

    def _make_quote(self, text: str) -> Dict:
        """创建引用 Block"""
        return {
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _make_code_block(self, code: str, language: str = "plain text") -> Dict:
        """创建代码块 Block"""
        # Notion 支持的语言映射
        lang_map = {
            "python": "python", "py": "python",
            "javascript": "javascript", "js": "javascript",
            "typescript": "typescript", "ts": "typescript",
            "sql": "sql", "bash": "bash", "shell": "bash",
            "html": "html", "css": "css", "json": "json",
            "java": "java", "go": "go", "rust": "rust",
            "plain text": "plain text", "text": "plain text",
        }
        notion_lang = lang_map.get(language.lower(), "plain text")

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": code[:2000]}}],
                "language": notion_lang,
            },
        }

    @staticmethod
    def _make_divider() -> Dict:
        """创建分割线 Block"""
        return {"object": "block", "type": "divider", "divider": {}}

    # ==================== 辅助方法 ====================

    @staticmethod
    def _extract_title(item: Dict) -> str:
        """从 Notion 搜索结果中提取标题"""
        properties = item.get("properties", {})

        # 尝试从 title 属性获取
        for key, val in properties.items():
            if val.get("type") == "title":
                title_arr = val.get("title", [])
                if title_arr:
                    return title_arr[0].get("plain_text", "无标题")

        # 尝试从 child_page 获取
        if item.get("type") == "child_page":
            return item.get("child_page", {}).get("title", "无标题")

        return "无标题"

    @staticmethod
    def _build_generation_prompt(title: str, page_type: str, user_message: str) -> str:
        """构建内容生成的 LLM 提示"""
        type_instructions = {
            "document": "生成一份结构清晰的文档，包含背景、正文、总结。",
            "plan": "生成一份项目计划，包含目标、阶段划分、时间安排、资源需求。",
            "report": "生成一份报告，包含概述、数据分析、结论和建议。",
            "meeting": "生成会议纪要格式，包含参会人、议题、讨论内容、行动项。",
            "proposal": "生成提案/方案，包含背景分析、方案设计、优劣对比、实施步骤。",
        }

        instruction = type_instructions.get(page_type, type_instructions["document"])

        return f"""请根据以下要求，为 Notion 页面「{title}」生成内容。

用户原始需求：{user_message}
文档类型：{page_type}

要求：
{instruction}

格式要求：
- 使用 Markdown 格式
- 用 ## 和 ### 做层级标题
- 重点内容用 **加粗**
- 步骤用有序列表（1. 2. 3.）
- 要点用无序列表（- ）
- 待办事项用 - [ ] 格式
- 内容要专业、详细、可操作
"""


# 注册
SkillRegistry.register(NotionSkill())
