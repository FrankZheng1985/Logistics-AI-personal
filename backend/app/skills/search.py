"""
SearchSkill - 联网搜索技能

职责：
- Google搜索（通过Serper API）
- 网页内容抓取
"""
from typing import Dict, Any
from loguru import logger

from app.skills.base import BaseSkill, SkillRegistry


class SearchSkill(BaseSkill):
    """联网搜索技能"""

    name = "search"
    description = "联网搜索：Google搜索、新闻搜索、网页内容抓取"
    tool_names = [
        "web_search",
        "fetch_webpage",
    ]

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        handlers = {
            "web_search": self._handle_web_search,
            "fetch_webpage": self._handle_fetch_webpage,
        }
        handler = handlers.get(tool_name)
        if handler:
            return await handler(args=args)
        return self._err(f"未知工具: {tool_name}")

    # ==================== Google 搜索 ====================

    async def _handle_web_search(self, args: Dict = None) -> Dict[str, Any]:
        """通过 Serper API 搜索 Google"""
        from app.core.config import settings
        import httpx

        args = args or {}
        query = args.get("query", "")
        search_type = args.get("search_type", "search")
        num_results = args.get("num_results", 5)

        if not query:
            return self._err("搜索关键词不能为空")

        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return self._err("搜索服务暂不可用（API未配置）")

        endpoint = "https://google.serper.dev/news" if search_type == "news" else "https://google.serper.dev/search"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "gl": "cn",
                        "hl": "zh-cn",
                        "num": min(num_results, 10)
                    }
                )

                if response.status_code != 200:
                    return self._err(f"搜索请求失败（HTTP {response.status_code}）")

                data = response.json()

                results = []
                source_key = "news" if search_type == "news" else "organic"

                for item in data.get(source_key, [])[:num_results]:
                    result_item = {
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", "") or item.get("description", ""),
                        "url": item.get("link", "") or item.get("url", ""),
                    }
                    if search_type == "news":
                        result_item["source"] = item.get("source", "")
                        result_item["date"] = item.get("date", "")
                    results.append(result_item)

                answer_box = data.get("answerBox", {})
                knowledge_graph = data.get("knowledgeGraph", {})

                summary_parts = []
                if answer_box:
                    summary_parts.append(f"快速答案: {answer_box.get('answer', '') or answer_box.get('snippet', '')}")
                if knowledge_graph:
                    kg_desc = knowledge_graph.get("description", "")
                    if kg_desc:
                        summary_parts.append(f"知识摘要: {kg_desc}")

                return {
                    "status": "success",
                    "query": query,
                    "result_count": len(results),
                    "results": results,
                    "quick_answer": "\n".join(summary_parts) if summary_parts else None,
                    "message": f"搜索到 {len(results)} 条结果"
                }

        except Exception as e:
            if "Timeout" in str(type(e).__name__):
                return self._err("搜索超时，请稍后再试")
            logger.error(f"[SearchSkill] 搜索失败: {e}")
            return self._err(f"搜索出错: {str(e)}")

    # ==================== 网页内容抓取 ====================

    async def _handle_fetch_webpage(self, args: Dict = None) -> Dict[str, Any]:
        """抓取网页内容并提取正文"""
        import httpx

        args = args or {}
        url = args.get("url", "")

        if not url or not url.startswith(("http://", "https://")):
            return self._err("无效的网址")

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            ) as client:
                response = await client.get(url)

                if response.status_code != 200:
                    return self._err(f"无法访问该网页（HTTP {response.status_code}）")

                html = response.text

                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")

                    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
                        tag.decompose()

                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    text_content = soup.get_text(separator="\n", strip=True)

                    lines = [line.strip() for line in text_content.splitlines() if line.strip()]
                    clean_text = "\n".join(lines)

                    max_chars = 3000
                    if len(clean_text) > max_chars:
                        clean_text = clean_text[:max_chars] + "\n...(内容已截断)"

                    return {
                        "status": "success",
                        "url": url,
                        "title": title,
                        "content": clean_text,
                        "content_length": len(clean_text),
                        "message": f"已抓取网页内容（{len(clean_text)}字）"
                    }

                except ImportError:
                    import re as _re
                    text_content = _re.sub(r'<[^>]+>', ' ', html)
                    text_content = _re.sub(r'\s+', ' ', text_content).strip()
                    if len(text_content) > 3000:
                        text_content = text_content[:3000] + "...(已截断)"
                    return {
                        "status": "success",
                        "url": url,
                        "title": "",
                        "content": text_content,
                        "content_length": len(text_content),
                        "message": f"已抓取网页内容（{len(text_content)}字）"
                    }

        except Exception as e:
            if "Timeout" in str(type(e).__name__):
                return self._err("网页加载超时")
            logger.error(f"[SearchSkill] 抓取网页失败: {e}")
            return self._err(f"抓取失败: {str(e)}")


# 注册
SkillRegistry.register(SearchSkill())
