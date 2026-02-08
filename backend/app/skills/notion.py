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

    # Notion 工作台分区定义
    SECTIONS = {
        "project":  {"icon": "📋", "title": "📋 项目方案",  "keywords": ["方案", "项目", "计划", "设计", "架构", "开发", "系统", "技术"]},
        "report":   {"icon": "📊", "title": "📊 报告分析",  "keywords": ["日报", "周报", "月报", "报告", "分析", "调研", "总结", "数据"]},
        "meeting":  {"icon": "📝", "title": "📝 会议纪要",  "keywords": ["会议", "纪要", "讨论", "决策", "会议记录"]},
        "idea":     {"icon": "💡", "title": "💡 创意灵感",  "keywords": ["创意", "灵感", "想法", "脑暴", "思路", "营销"]},
        "knowledge":{"icon": "📚", "title": "📚 知识库",    "keywords": ["文档", "手册", "SOP", "培训", "教程", "操作", "指南"]},
        "archive":  {"icon": "🗂️", "title": "🗂️ 归档",     "keywords": ["归档", "历史", "已完成"]},
    }

    def __init__(self, agent=None):
        super().__init__(agent)
        self._client = None
        self._section_cache: Dict[str, str] = {}  # section_key -> page_id 缓存
        self._task_db_id: Optional[str] = None  # 任务看板 Database ID 缓存

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

    def _detect_section(self, title: str, page_type: str) -> str:
        """根据标题和类型自动判断应该放在哪个分区"""
        # 先按 page_type 映射
        type_to_section = {
            "plan": "project", "proposal": "project",
            "report": "report",
            "meeting": "meeting",
            "document": None,  # 需要进一步判断
        }

        section = type_to_section.get(page_type)
        if section:
            return section

        # 按关键词匹配
        combined = title.lower()
        for key, info in self.SECTIONS.items():
            if any(kw in combined for kw in info["keywords"]):
                return key

        # 默认放到项目方案
        return "project"

    def _ensure_dated_title(self, title: str) -> str:
        """确保标题带日期前缀"""
        # 如果已经有日期前缀，直接返回
        if re.match(r'^\[\d{4}-\d{2}-\d{2}\]', title):
            return title
        today = datetime.now().strftime("%Y-%m-%d")
        return f"[{today}] {title}"

    async def _get_or_create_section(self, section_key: str) -> str:
        """获取或创建分区页面，返回分区的 page_id"""
        # 先查缓存
        if section_key in self._section_cache:
            return self._section_cache[section_key]

        section_info = self.SECTIONS.get(section_key)
        if not section_info:
            return self._get_root_page_id()

        section_title = section_info["title"]

        try:
            client = self._get_client()
            root_id = self._get_root_page_id()

            # 搜索是否已有此分区页面
            search_result = client.search(
                query=section_title,
                filter={"property": "object", "value": "page"},
                page_size=5,
            )

            for item in search_result.get("results", []):
                item_title = self._extract_title(item)
                if item_title == section_title:
                    page_id = item["id"]
                    self._section_cache[section_key] = page_id
                    logger.info(f"[NotionSkill] 找到已有分区: {section_title} -> {page_id}")
                    return page_id

            # 不存在则创建分区页面
            new_section = client.pages.create(
                parent={"page_id": root_id},
                properties={
                    "title": [{"text": {"content": section_title}}]
                },
                icon={"type": "emoji", "emoji": section_info["icon"]},
                children=[
                    self._make_paragraph(
                        f"此分区由 Maria AI 自动创建，用于归类{section_title.split(' ', 1)[-1]}相关文档。",
                        color="gray"
                    )
                ],
            )

            page_id = new_section["id"]
            self._section_cache[section_key] = page_id
            logger.info(f"[NotionSkill] 创建新分区: {section_title} -> {page_id}")
            return page_id

        except Exception as e:
            logger.warning(f"[NotionSkill] 获取/创建分区失败: {e}，使用根页面")
            return self._get_root_page_id()

    async def _handle_create_page(self, args: Dict, message: str, user_id: str) -> Dict[str, Any]:
        """在 Notion 中创建新页面"""
        title = args.get("title", "").strip()
        content = args.get("content", "").strip()
        page_type = args.get("page_type", "document")
        parent_page_id = args.get("parent_page_id", "")

        if not title:
            return self._err("请提供页面标题")

        # 自动加日期前缀
        title = self._ensure_dated_title(title)

        await self.log_step("action", "创建 Notion 页面", title)

        # 如果没有给内容，用 LLM 生成
        if not content and message:
            await self.log_step("think", "正在生成内容", "用 AI 撰写文档...")
            generation_prompt = self._build_generation_prompt(title, page_type, message)
            content = await self.chat(
                generation_prompt,
                "你是一个专业的文档撰写助手。根据用户需求生成结构化的 Markdown 内容。"
                "使用清晰的标题层级（## ###）、列表、加粗等格式。内容要专业、完整、实用。"
                "不要在开头重复标题。直接输出正文内容。"
            )

        try:
            client = self._get_client()

            # 自动归类到对应分区
            if parent_page_id:
                parent_id = parent_page_id
            else:
                section_key = self._detect_section(title, page_type)
                parent_id = await self._get_or_create_section(section_key)
                logger.info(f"[NotionSkill] 页面归类到分区: {section_key}")

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


    # ==================== 任务看板 Database 操作 ====================

    TASK_DB_TITLE = "任务看板"

    AGENT_NAMES_SELECT = [
        {"name": "小调", "color": "gray"},
        {"name": "小影", "color": "purple"},
        {"name": "小文", "color": "pink"},
        {"name": "小销", "color": "orange"},
        {"name": "小跟", "color": "yellow"},
        {"name": "小析", "color": "blue"},
        {"name": "小猎", "color": "green"},
        {"name": "小析2", "color": "gray"},
        {"name": "小欧间谍", "color": "red"},
    ]

    STATUS_SELECT = [
        {"name": "等待中", "color": "yellow"},
        {"name": "进行中", "color": "blue"},
        {"name": "已完成", "color": "green"},
        {"name": "失败", "color": "red"},
    ]

    PRIORITY_SELECT = [
        {"name": "紧急", "color": "red"},
        {"name": "高", "color": "orange"},
        {"name": "中", "color": "blue"},
        {"name": "低", "color": "gray"},
    ]

    # agent_type -> 中文名映射
    AGENT_TYPE_TO_NAME = {
        "coordinator": "小调", "video_creator": "小影",
        "copywriter": "小文", "sales": "小销",
        "follow": "小跟", "analyst": "小析",
        "lead_hunter": "小猎", "analyst2": "小析2",
        "eu_customs_monitor": "小欧间谍",
    }

    async def get_or_create_task_db(self) -> str:
        """获取或创建任务看板 Database，返回 database_id"""
        if self._task_db_id:
            return self._task_db_id

        try:
            client = self._get_client()
            root_id = self._get_root_page_id()

            # 搜索是否已有任务看板 Database
            search_result = client.search(
                query=self.TASK_DB_TITLE,
                filter={"property": "object", "value": "database"},
                page_size=5,
            )

            for item in search_result.get("results", []):
                title_arr = item.get("title", [])
                if title_arr and title_arr[0].get("plain_text", "") == self.TASK_DB_TITLE:
                    self._task_db_id = item["id"]
                    logger.info(f"[NotionSkill] 找到已有任务看板: {self._task_db_id}")
                    return self._task_db_id

            # 不存在，创建新的 Database
            new_db = client.databases.create(
                parent={"page_id": root_id},
                title=[{"text": {"content": self.TASK_DB_TITLE}}],
                icon={"type": "emoji", "emoji": "📊"},
                properties={
                    "任务名称": {"title": {}},
                    "所属项目": {"select": {"options": []}},  # 动态填充
                    "负责人": {"select": {"options": self.AGENT_NAMES_SELECT}},
                    "状态": {"select": {"options": self.STATUS_SELECT}},
                    "优先级": {"select": {"options": self.PRIORITY_SELECT}},
                    "创建时间": {"date": {}},
                    "开始执行": {"date": {}},
                    "完成时间": {"date": {}},
                    "耗时": {"rich_text": {}},
                    "产出物": {"rich_text": {}},
                },
            )

            self._task_db_id = new_db["id"]
            logger.info(f"[NotionSkill] 创建任务看板 Database: {self._task_db_id}")
            return self._task_db_id

        except Exception as e:
            logger.error(f"[NotionSkill] 获取/创建任务看板失败: {e}")
            raise

    async def upsert_task_row(self, task_id: str, data: Dict[str, Any]) -> Optional[str]:
        """
        在任务看板 Database 中插入或更新一行
        
        Args:
            task_id: ai_tasks 表的任务 ID
            data: 字段数据，可包含:
                - title: 任务名称
                - agent_name: 负责人（中文名如"小文"）
                - agent_type: 负责人类型（英文如"copywriter"，会自动转中文）
                - status: 状态（等待中/进行中/已完成/失败）
                - priority: 优先级（紧急/高/中/低）
                - created_at: 创建时间 (ISO格式字符串)
                - started_at: 开始执行时间
                - completed_at: 完成时间
                - duration: 耗时（如"2分30秒"）
                - output: 产出物摘要
                - notion_page_id: 已有的 Notion page_id（用于更新）
                
        Returns:
            notion_page_id (str) 或 None
        """
        try:
            client = self._get_client()
            db_id = await self.get_or_create_task_db()

            # 构建 properties
            properties = {}

            if data.get("title"):
                properties["任务名称"] = {
                    "title": [{"text": {"content": data["title"][:100]}}]
                }

            # 负责人
            agent_name = data.get("agent_name") or self.AGENT_TYPE_TO_NAME.get(data.get("agent_type", ""), "")
            if agent_name:
                properties["负责人"] = {"select": {"name": agent_name}}

            # 所属项目
            project = data.get("project")
            if project:
                properties["所属项目"] = {"select": {"name": project}}

            if data.get("status"):
                properties["状态"] = {"select": {"name": data["status"]}}

            if data.get("priority"):
                # 映射英文优先级到中文
                priority_map = {"urgent": "紧急", "high": "高", "medium": "中", "low": "低"}
                priority_cn = priority_map.get(data["priority"], data["priority"])
                properties["优先级"] = {"select": {"name": priority_cn}}

            if data.get("created_at"):
                properties["创建时间"] = {
                    "date": {"start": self._format_date(data["created_at"])}
                }

            if data.get("started_at"):
                properties["开始执行"] = {
                    "date": {"start": self._format_date(data["started_at"])}
                }

            if data.get("completed_at"):
                properties["完成时间"] = {
                    "date": {"start": self._format_date(data["completed_at"])}
                }

            if data.get("duration"):
                properties["耗时"] = {
                    "rich_text": [{"text": {"content": str(data["duration"])}}]
                }

            if data.get("output"):
                output_text = str(data["output"])[:2000]
                properties["产出物"] = {
                    "rich_text": [{"text": {"content": output_text}}]
                }

            # 判断是新增还是更新
            notion_page_id = data.get("notion_page_id")

            if notion_page_id:
                # 更新已有行
                client.pages.update(
                    page_id=notion_page_id,
                    properties=properties,
                )
                logger.info(f"[NotionSkill] 任务看板更新: {task_id[:8]} -> {data.get('status', '?')}")
                return notion_page_id
            else:
                # 插入新行
                new_page = client.pages.create(
                    parent={"database_id": db_id},
                    properties=properties,
                )
                new_page_id = new_page["id"]
                logger.info(f"[NotionSkill] 任务看板新增: {task_id[:8]} -> {new_page_id}")
                return new_page_id

        except Exception as e:
            logger.error(f"[NotionSkill] 任务看板操作失败: {e}")
            return None

    @staticmethod
    def _format_date(value) -> str:
        """将各种日期格式统一为 ISO 格式字符串"""
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


# 全局单例（供 TaskWorker 等外部模块直接使用）
_notion_skill_instance = NotionSkill()

# 注册
SkillRegistry.register(_notion_skill_instance)


async def get_notion_skill() -> NotionSkill:
    """获取 NotionSkill 单例（供外部模块调用任务看板功能）"""
    return _notion_skill_instance
