"""
小码 - 前端代码工程师（专家级）
负责网站开发、代码生成、自动部署
"""
from typing import Dict, Any, Optional, List
import json
import asyncio
from loguru import logger
from datetime import datetime

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings
from app.core.prompts.code_engineer import CODE_ENGINEER_SYSTEM_PROMPT


class CodeEngineerAgent(BaseAgent):
    """小码 - 前端代码工程师（专家级）
    
    核心能力：
    1. 生成高质量的前端代码（HTML/CSS/JS/React/Vue）
    2. 响应式设计和移动端适配
    3. SEO 优化和性能优化
    4. 代码自动保存到 COS 项目目录
    5. 自动部署到 GitHub Pages
    """
    
    name = "小码"
    agent_type = AgentType.CODE_ENGINEER
    description = "前端代码工程师 - 负责网站开发、代码生成、自动部署"
    
    # 支持的网站类型
    WEBSITE_TYPES = {
        "corporate": "企业官网",
        "product": "产品展示站",
        "landing": "落地页/营销页",
        "blog": "内容/博客站",
        "ecommerce": "电商展示站",
    }
    
    # 支持的技术栈
    TECH_STACKS = {
        "static": {"name": "纯静态", "desc": "HTML + CSS + JS，最快最简单"},
        "react": {"name": "React", "desc": "React + Tailwind CSS，交互丰富"},
        "nextjs": {"name": "Next.js", "desc": "Next.js + Tailwind，SEO友好"},
        "vue": {"name": "Vue 3", "desc": "Vue 3 + Vite，渐进式框架"},
    }
    
    def __init__(self):
        super().__init__()
        self.github_token = getattr(settings, 'GITHUB_TOKEN', None)
        self.cos_enabled = bool(getattr(settings, 'COS_SECRET_ID', None))
    
    def _build_system_prompt(self) -> str:
        return CODE_ENGINEER_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理代码生成任务
        
        Args:
            input_data: {
                "task_type": "generate|deploy|review",
                "project_name": "项目名称",
                "website_type": "corporate|product|landing|blog",
                "tech_stack": "static|react|nextjs|vue",
                "requirements": "需求描述",
                "design_guide": "设计指南（颜色、风格等）",
                "content": {"homepage": "...", "about": "..."},  # 小文提供的文案
                "assets": {"logo": "url", "images": []},  # 小影提供的素材
                "save_to_cos": True,  # 是否保存到COS
                "auto_deploy": False,  # 是否自动部署
            }
        """
        task_type = input_data.get("task_type", "generate")
        project_name = input_data.get("project_name", "website")
        
        # 开始任务会话
        await self.start_task_session(f"code_{task_type}", f"代码任务: {project_name}")
        
        try:
            if task_type == "generate":
                result = await self._generate_website(input_data)
            elif task_type == "deploy":
                result = await self._deploy_website(input_data)
            elif task_type == "review":
                result = await self._review_code(input_data)
            elif task_type == "component":
                result = await self._generate_component(input_data)
            else:
                result = {"status": "error", "message": f"未知任务类型: {task_type}"}
            
            await self.end_task_session(f"完成: {project_name}")
            return result
        except Exception as e:
            await self.end_task_session(error_message=str(e))
            raise
    
    async def _generate_website(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成完整网站代码"""
        project_name = input_data.get("project_name", "my-website")
        website_type = input_data.get("website_type", "corporate")
        tech_stack = input_data.get("tech_stack", "static")
        requirements = input_data.get("requirements", "")
        design_guide = input_data.get("design_guide", {})
        content = input_data.get("content", {})
        assets = input_data.get("assets", {})
        save_to_cos = input_data.get("save_to_cos", True)
        
        self.log(f"[生成网站] 项目: {project_name}, 类型: {website_type}, 技术栈: {tech_stack}")
        
        # 1. 根据需求生成代码
        self.log("[think] 分析需求，规划网站结构...")
        
        # 构建代码生成提示
        generation_prompt = self._build_generation_prompt(
            project_name=project_name,
            website_type=website_type,
            tech_stack=tech_stack,
            requirements=requirements,
            design_guide=design_guide,
            content=content,
            assets=assets
        )
        
        # 调用 LLM 生成代码
        self.log("[code] 正在生成代码...")
        code_result = await self._call_llm_for_code(generation_prompt)
        
        if not code_result.get("success"):
            return {
                "status": "error",
                "message": "代码生成失败",
                "error": code_result.get("error")
            }
        
        # 解析生成的代码
        generated_files = self._parse_generated_code(code_result.get("content", ""))
        
        self.log(f"[complete] 生成 {len(generated_files)} 个文件")
        
        # 2. 保存到 COS
        cos_urls = {}
        if save_to_cos and self.cos_enabled:
            self.log("[upload] 保存到 COS 项目目录...")
            cos_urls = await self._save_to_cos(project_name, generated_files)
        
        # 3. 生成预览信息
        preview_info = self._generate_preview_info(project_name, generated_files)
        
        return {
            "status": "success",
            "project_name": project_name,
            "website_type": self.WEBSITE_TYPES.get(website_type, website_type),
            "tech_stack": self.TECH_STACKS.get(tech_stack, {}).get("name", tech_stack),
            "files": list(generated_files.keys()),
            "file_count": len(generated_files),
            "cos_urls": cos_urls,
            "preview_info": preview_info,
            "generated_files": generated_files,  # 完整代码内容
            "message": f"网站代码已生成，共 {len(generated_files)} 个文件"
        }
    
    def _build_generation_prompt(self, **kwargs) -> str:
        """构建代码生成提示"""
        project_name = kwargs.get("project_name")
        website_type = kwargs.get("website_type")
        tech_stack = kwargs.get("tech_stack")
        requirements = kwargs.get("requirements")
        design_guide = kwargs.get("design_guide", {})
        content = kwargs.get("content", {})
        assets = kwargs.get("assets", {})
        
        # 设计指南格式化
        design_str = ""
        if design_guide:
            if isinstance(design_guide, dict):
                design_str = "\n".join([f"- {k}: {v}" for k, v in design_guide.items()])
            else:
                design_str = str(design_guide)
        
        # 文案内容格式化
        content_str = ""
        if content:
            if isinstance(content, dict):
                for page, text in content.items():
                    content_str += f"\n### {page} 页面文案:\n{text}\n"
            else:
                content_str = str(content)
        
        # 素材信息
        assets_str = ""
        if assets:
            if isinstance(assets, dict):
                assets_str = json.dumps(assets, ensure_ascii=False, indent=2)
            else:
                assets_str = str(assets)
        
        prompt = f"""请为以下项目生成完整的网站代码：

## 项目信息
- 项目名称：{project_name}
- 网站类型：{self.WEBSITE_TYPES.get(website_type, website_type)}
- 技术栈：{self.TECH_STACKS.get(tech_stack, {}).get("name", tech_stack)}

## 需求描述
{requirements}

## 设计指南
{design_str if design_str else "使用现代、简洁、专业的设计风格"}

## 文案内容
{content_str if content_str else "根据需求自动生成合适的占位文案"}

## 素材信息
{assets_str if assets_str else "使用占位图片，后续替换"}

## 输出要求
1. 生成完整可运行的代码
2. 包含所有必要的文件（HTML/CSS/JS/配置文件）
3. 响应式设计，适配移动端和桌面端
4. SEO 友好（语义化标签、meta 标签）
5. 性能优化（图片懒加载、代码压缩）

请按以下格式输出每个文件：

📁 文件：[文件路径]
---
[代码内容]
---

确保代码可以直接使用，无需修改。
"""
        return prompt
    
    async def _call_llm_for_code(self, prompt: str) -> Dict[str, Any]:
        """调用 LLM 生成代码"""
        try:
            from app.core.llm import LLMManager
            
            llm = LLMManager()
            
            # 使用更强大的模型生成代码
            response = await llm.chat_completion(
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                model="qwen-max",  # 使用强力模型
                temperature=0.3,  # 降低随机性，保证代码质量
                max_tokens=16000  # 允许更长输出
            )
            
            if isinstance(response, str):
                content = response
            elif isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)
            
            return {"success": True, "content": content}
            
        except Exception as e:
            logger.error(f"[CodeEngineer] LLM调用失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_generated_code(self, content: str) -> Dict[str, str]:
        """解析 LLM 生成的代码，提取各个文件"""
        files = {}
        
        # 匹配格式：📁 文件：xxx\n---\n代码\n---
        import re
        pattern = r'📁\s*文件[：:]\s*(.+?)\n---\n(.*?)\n---'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for filepath, code in matches:
            filepath = filepath.strip()
            code = code.strip()
            if filepath and code:
                files[filepath] = code
        
        # 如果没匹配到，尝试其他格式
        if not files:
            # 尝试 ```文件名 格式
            pattern2 = r'```(\w+)?\s*\n?//\s*(.+?)\n(.*?)```'
            matches2 = re.findall(pattern2, content, re.DOTALL)
            for lang, filepath, code in matches2:
                filepath = filepath.strip()
                code = code.strip()
                if filepath and code:
                    files[filepath] = code
        
        # 如果还是没有，返回整体作为 index.html
        if not files and content.strip():
            # 尝试提取 HTML 代码块
            html_match = re.search(r'```html?\n(.*?)```', content, re.DOTALL)
            if html_match:
                files["index.html"] = html_match.group(1).strip()
            else:
                files["index.html"] = content.strip()
        
        return files
    
    async def _save_to_cos(self, project_name: str, files: Dict[str, str]) -> Dict[str, str]:
        """保存代码文件到 COS"""
        try:
            from app.services.cos_storage_service import cos_storage_service
            
            cos_urls = {}
            base_path = f"projects/{project_name}/code"
            
            for filepath, content in files.items():
                # 确定文件类型
                if filepath.endswith('.html'):
                    content_type = 'text/html'
                elif filepath.endswith('.css'):
                    content_type = 'text/css'
                elif filepath.endswith('.js'):
                    content_type = 'application/javascript'
                elif filepath.endswith('.json'):
                    content_type = 'application/json'
                else:
                    content_type = 'text/plain'
                
                # 上传到 COS
                full_path = f"{base_path}/{filepath}"
                success, url = await cos_storage_service.upload_bytes(
                    content.encode('utf-8'),
                    full_path,
                    content_type=content_type
                )
                
                if success:
                    cos_urls[filepath] = url
                    self.log(f"[upload] 已上传: {filepath}")
                else:
                    self.log(f"[warn] 上传失败: {filepath}")
            
            return cos_urls
            
        except Exception as e:
            logger.error(f"[CodeEngineer] COS上传失败: {e}")
            return {}
    
    async def _deploy_website(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """部署网站到 GitHub Pages"""
        project_name = input_data.get("project_name")
        files = input_data.get("files", {})
        repo_name = input_data.get("repo_name", project_name)
        
        self.log(f"[deploy] 部署 {project_name} 到 GitHub Pages...")
        
        if not self.github_token:
            return {
                "status": "error",
                "message": "GitHub Token 未配置，无法自动部署"
            }
        
        try:
            # 使用 GitHub API 创建/更新仓库
            import httpx
            
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                # 1. 检查仓库是否存在
                repo_url = f"https://api.github.com/repos/{settings.GITHUB_USERNAME}/{repo_name}"
                resp = await client.get(repo_url, headers=headers)
                
                if resp.status_code == 404:
                    # 创建新仓库
                    self.log("[deploy] 创建新仓库...")
                    create_resp = await client.post(
                        "https://api.github.com/user/repos",
                        headers=headers,
                        json={
                            "name": repo_name,
                            "description": f"Website: {project_name}",
                            "homepage": f"https://{settings.GITHUB_USERNAME}.github.io/{repo_name}",
                            "private": False,
                            "has_pages": True
                        }
                    )
                    if create_resp.status_code not in [200, 201]:
                        return {"status": "error", "message": f"创建仓库失败: {create_resp.text}"}
                
                # 2. 上传文件
                for filepath, content in files.items():
                    self.log(f"[deploy] 上传文件: {filepath}")
                    
                    import base64
                    content_b64 = base64.b64encode(content.encode()).decode()
                    
                    file_url = f"https://api.github.com/repos/{settings.GITHUB_USERNAME}/{repo_name}/contents/{filepath}"
                    
                    # 检查文件是否存在（获取 sha）
                    file_resp = await client.get(file_url, headers=headers)
                    sha = None
                    if file_resp.status_code == 200:
                        sha = file_resp.json().get("sha")
                    
                    # 创建/更新文件
                    put_data = {
                        "message": f"Update {filepath}",
                        "content": content_b64,
                        "branch": "main"
                    }
                    if sha:
                        put_data["sha"] = sha
                    
                    put_resp = await client.put(file_url, headers=headers, json=put_data)
                    if put_resp.status_code not in [200, 201]:
                        self.log(f"[warn] 上传 {filepath} 失败: {put_resp.text}")
                
                # 3. 启用 GitHub Pages
                pages_url = f"https://api.github.com/repos/{settings.GITHUB_USERNAME}/{repo_name}/pages"
                pages_resp = await client.post(
                    pages_url,
                    headers=headers,
                    json={"source": {"branch": "main", "path": "/"}}
                )
                
                site_url = f"https://{settings.GITHUB_USERNAME}.github.io/{repo_name}"
                
                return {
                    "status": "success",
                    "message": f"网站已部署到 GitHub Pages",
                    "site_url": site_url,
                    "repo_url": f"https://github.com/{settings.GITHUB_USERNAME}/{repo_name}"
                }
                
        except Exception as e:
            logger.error(f"[CodeEngineer] 部署失败: {e}")
            return {"status": "error", "message": f"部署失败: {str(e)}"}
    
    async def _review_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """代码审查"""
        code = input_data.get("code", "")
        review_focus = input_data.get("focus", "all")  # all/performance/seo/accessibility
        
        self.log("[review] 开始代码审查...")
        
        review_prompt = f"""请对以下代码进行专业审查：

```
{code}
```

审查重点：{review_focus}

请从以下方面给出详细评价和改进建议：
1. 代码质量（可读性、可维护性）
2. 性能优化（加载速度、渲染效率）
3. SEO 友好度
4. 可访问性（无障碍）
5. 安全性
6. 最佳实践

对每个方面给出评分（1-10）和具体改进建议。
"""
        
        result = await self._call_llm_for_code(review_prompt)
        
        return {
            "status": "success" if result.get("success") else "error",
            "review": result.get("content", ""),
            "message": "代码审查完成"
        }
    
    async def _generate_component(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成单个组件"""
        component_name = input_data.get("component_name", "Component")
        component_type = input_data.get("component_type", "react")  # react/vue/html
        description = input_data.get("description", "")
        
        self.log(f"[component] 生成组件: {component_name}")
        
        prompt = f"""请生成一个 {component_type} 组件：

组件名称：{component_name}
功能描述：{description}

要求：
1. 代码简洁、可复用
2. 包含必要的 props/参数
3. 响应式设计
4. 包含基本样式
5. 添加注释说明用法

请输出完整的组件代码。
"""
        
        result = await self._call_llm_for_code(prompt)
        
        return {
            "status": "success" if result.get("success") else "error",
            "component_name": component_name,
            "code": result.get("content", ""),
            "message": f"组件 {component_name} 生成完成"
        }
    
    def _generate_preview_info(self, project_name: str, files: Dict[str, str]) -> Dict[str, Any]:
        """生成预览信息"""
        # 统计文件类型
        file_types = {}
        for filepath in files.keys():
            ext = filepath.split('.')[-1] if '.' in filepath else 'other'
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # 计算总代码行数
        total_lines = sum(len(content.split('\n')) for content in files.values())
        
        return {
            "project_name": project_name,
            "file_types": file_types,
            "total_files": len(files),
            "total_lines": total_lines,
            "main_file": "index.html" if "index.html" in files else list(files.keys())[0] if files else None
        }


# 注册 Agent
AgentRegistry.register(CodeEngineerAgent())
