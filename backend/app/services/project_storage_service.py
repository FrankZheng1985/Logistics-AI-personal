"""
项目存储服务 - 管理项目文件的自动保存与分类
基于腾讯云 COS，为每个项目创建结构化目录
"""
import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.services.cos_storage_service import cos_storage_service


class ProjectStorageService:
    """项目存储服务
    
    目录结构：
    projects/
    ├── {project_name}/
    │   ├── docs/           # 架构文档、规划文档（小调）
    │   ├── content/        # 文案内容（小文）
    │   ├── assets/         # 素材文件（小影）
    │   │   ├── images/
    │   │   ├── videos/
    │   │   └── icons/
    │   ├── code/           # 代码文件（小码）
    │   │   ├── src/
    │   │   └── dist/
    │   ├── deploy/         # 部署相关
    │   └── metadata.json   # 项目元数据
    """
    
    # 目录映射：员工 -> 子目录
    AGENT_DIRECTORIES = {
        "coordinator": "docs",       # 小调 -> 文档
        "copywriter": "content",     # 小文 -> 文案
        "video_creator": "assets/videos",  # 小影视频 -> 素材/视频
        "asset_collector": "assets/images",  # 小影图片 -> 素材/图片
        "code_engineer": "code",     # 小码 -> 代码
        "analyst": "docs/analysis",  # 小析 -> 文档/分析
        "sales": "docs/sales",       # 小销 -> 文档/销售
        "lead_hunter": "docs/leads", # 小猎 -> 文档/线索
        "knowledge_curator": "docs/knowledge",  # 小知 -> 文档/知识
    }
    
    # 文件类型映射
    FILE_TYPE_DIRS = {
        # 文档类
        ".md": "docs",
        ".txt": "docs",
        ".doc": "docs",
        ".docx": "docs",
        ".pdf": "docs",
        # 代码类
        ".html": "code",
        ".css": "code",
        ".js": "code",
        ".jsx": "code",
        ".ts": "code",
        ".tsx": "code",
        ".vue": "code",
        ".json": "code",
        # 图片类
        ".jpg": "assets/images",
        ".jpeg": "assets/images",
        ".png": "assets/images",
        ".gif": "assets/images",
        ".svg": "assets/images",
        ".webp": "assets/images",
        # 视频类
        ".mp4": "assets/videos",
        ".webm": "assets/videos",
        ".mov": "assets/videos",
        # 音频类
        ".mp3": "assets/audio",
        ".wav": "assets/audio",
    }
    
    def __init__(self):
        self.base_path = "projects"
    
    @property
    def is_ready(self) -> bool:
        """检查服务是否可用"""
        return cos_storage_service.is_configured
    
    async def create_project(
        self,
        project_name: str,
        description: str = "",
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        创建新项目目录结构
        
        Args:
            project_name: 项目名称（英文，用于目录名）
            description: 项目描述
            created_by: 创建者
        
        Returns:
            项目信息
        """
        if not self.is_ready:
            return {"success": False, "error": "COS 服务未配置"}
        
        # 规范化项目名
        safe_name = self._safe_project_name(project_name)
        project_path = f"{self.base_path}/{safe_name}"
        
        # 创建元数据
        metadata = {
            "name": project_name,
            "safe_name": safe_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "created_by": created_by,
            "files": [],
            "directory_structure": {
                "docs": "架构文档、规划文档",
                "content": "文案内容",
                "assets": {
                    "images": "图片素材",
                    "videos": "视频素材",
                    "icons": "图标素材",
                    "audio": "音频素材"
                },
                "code": {
                    "src": "源代码",
                    "dist": "构建产物"
                },
                "deploy": "部署配置"
            }
        }
        
        # 上传元数据文件
        metadata_key = f"{project_path}/metadata.json"
        success, url = await cos_storage_service.upload_bytes(
            json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'),
            metadata_key,
            folder="",  # 已经包含完整路径
            content_type="application/json"
        )
        
        if success:
            logger.info(f"[ProjectStorage] 项目创建成功: {safe_name}")
            return {
                "success": True,
                "project_name": project_name,
                "safe_name": safe_name,
                "path": project_path,
                "metadata_url": url
            }
        else:
            return {"success": False, "error": url}
    
    async def save_file(
        self,
        project_name: str,
        content: bytes,
        filename: str,
        agent_type: str = None,
        subfolder: str = None,
        content_type: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        保存文件到项目目录
        
        Args:
            project_name: 项目名称
            content: 文件内容（字节）
            filename: 文件名
            agent_type: 员工类型（自动决定目录）
            subfolder: 指定子目录（覆盖自动判断）
            content_type: 内容类型
            metadata: 额外元数据
        
        Returns:
            保存结果
        """
        if not self.is_ready:
            return {"success": False, "error": "COS 服务未配置"}
        
        safe_name = self._safe_project_name(project_name)
        
        # 决定存储目录
        if subfolder:
            directory = subfolder
        elif agent_type and agent_type in self.AGENT_DIRECTORIES:
            directory = self.AGENT_DIRECTORIES[agent_type]
        else:
            # 根据文件扩展名判断
            ext = os.path.splitext(filename)[1].lower()
            directory = self.FILE_TYPE_DIRS.get(ext, "misc")
        
        # 构建完整路径
        file_key = f"{self.base_path}/{safe_name}/{directory}/{filename}"
        
        # 上传文件
        success, url = await cos_storage_service.upload_bytes(
            content,
            file_key,
            folder="",  # 已经包含完整路径
            content_type=content_type
        )
        
        if success:
            logger.info(f"[ProjectStorage] 文件保存成功: {file_key}")
            
            # 更新项目元数据
            await self._update_project_metadata(safe_name, {
                "file": filename,
                "path": file_key,
                "url": url,
                "agent": agent_type,
                "saved_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            })
            
            return {
                "success": True,
                "filename": filename,
                "path": file_key,
                "url": url,
                "directory": directory
            }
        else:
            return {"success": False, "error": url}
    
    async def save_text_file(
        self,
        project_name: str,
        content: str,
        filename: str,
        agent_type: str = None,
        subfolder: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        保存文本文件（便捷方法）
        """
        # 根据扩展名决定content_type
        ext = os.path.splitext(filename)[1].lower()
        content_type_map = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".xml": "application/xml",
        }
        content_type = content_type_map.get(ext, "text/plain")
        
        return await self.save_file(
            project_name=project_name,
            content=content.encode('utf-8'),
            filename=filename,
            agent_type=agent_type,
            subfolder=subfolder,
            content_type=content_type,
            metadata=metadata
        )
    
    async def save_multiple_files(
        self,
        project_name: str,
        files: Dict[str, str],  # {filename: content}
        agent_type: str = None,
        subfolder: str = None
    ) -> Dict[str, Any]:
        """
        批量保存多个文件
        
        Args:
            project_name: 项目名称
            files: 文件字典 {文件名: 内容}
            agent_type: 员工类型
            subfolder: 子目录
        
        Returns:
            保存结果汇总
        """
        results = {
            "success": True,
            "saved": [],
            "failed": [],
            "total": len(files)
        }
        
        for filename, content in files.items():
            result = await self.save_text_file(
                project_name=project_name,
                content=content,
                filename=filename,
                agent_type=agent_type,
                subfolder=subfolder
            )
            
            if result.get("success"):
                results["saved"].append({
                    "filename": filename,
                    "url": result.get("url"),
                    "path": result.get("path")
                })
            else:
                results["failed"].append({
                    "filename": filename,
                    "error": result.get("error")
                })
                results["success"] = False
        
        results["saved_count"] = len(results["saved"])
        results["failed_count"] = len(results["failed"])
        
        logger.info(f"[ProjectStorage] 批量保存完成: {results['saved_count']}/{results['total']} 成功")
        return results
    
    async def get_project_info(self, project_name: str) -> Dict[str, Any]:
        """
        获取项目信息
        """
        safe_name = self._safe_project_name(project_name)
        metadata_key = f"{self.base_path}/{safe_name}/metadata.json"
        
        try:
            # 从COS读取元数据
            response = cos_storage_service.client.get_object(
                Bucket=cos_storage_service.bucket,
                Key=metadata_key
            )
            content = response['Body'].get_raw_stream().read()
            metadata = json.loads(content.decode('utf-8'))
            
            return {
                "success": True,
                "project": metadata
            }
        except Exception as e:
            logger.warning(f"[ProjectStorage] 获取项目信息失败: {e}")
            return {
                "success": False,
                "error": f"项目不存在或无法访问: {str(e)}"
            }
    
    async def list_project_files(
        self,
        project_name: str,
        directory: str = None
    ) -> Dict[str, Any]:
        """
        列出项目文件
        """
        safe_name = self._safe_project_name(project_name)
        prefix = f"{self.base_path}/{safe_name}/"
        if directory:
            prefix += f"{directory}/"
        
        try:
            response = cos_storage_service.client.list_objects(
                Bucket=cos_storage_service.bucket,
                Prefix=prefix,
                MaxKeys=1000
            )
            
            files = []
            for item in response.get('Contents', []):
                key = item.get('Key', '')
                if key.endswith('/'):
                    continue
                files.append({
                    "key": key,
                    "filename": os.path.basename(key),
                    "size": item.get('Size', 0),
                    "last_modified": str(item.get('LastModified', '')),
                    "url": f"https://{cos_storage_service.bucket}.cos.{cos_storage_service.region}.myqcloud.com/{key}"
                })
            
            return {
                "success": True,
                "project": safe_name,
                "directory": directory,
                "files": files,
                "count": len(files)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_project_metadata(
        self,
        safe_name: str,
        file_info: Dict[str, Any]
    ) -> bool:
        """更新项目元数据"""
        try:
            # 读取现有元数据
            metadata_key = f"{self.base_path}/{safe_name}/metadata.json"
            
            try:
                response = cos_storage_service.client.get_object(
                    Bucket=cos_storage_service.bucket,
                    Key=metadata_key
                )
                content = response['Body'].get_raw_stream().read()
                metadata = json.loads(content.decode('utf-8'))
            except:
                # 元数据不存在，创建新的
                metadata = {
                    "name": safe_name,
                    "safe_name": safe_name,
                    "created_at": datetime.now().isoformat(),
                    "files": []
                }
            
            # 添加文件信息
            metadata["files"].append(file_info)
            metadata["updated_at"] = datetime.now().isoformat()
            metadata["file_count"] = len(metadata["files"])
            
            # 保存更新后的元数据
            await cos_storage_service.upload_bytes(
                json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8'),
                metadata_key,
                folder="",
                content_type="application/json"
            )
            
            return True
        except Exception as e:
            logger.error(f"[ProjectStorage] 更新元数据失败: {e}")
            return False
    
    def _safe_project_name(self, name: str) -> str:
        """转换为安全的项目目录名"""
        import re
        # 转小写，替换空格和特殊字符
        safe = name.lower().strip()
        safe = re.sub(r'[^a-z0-9\-_]', '-', safe)
        safe = re.sub(r'-+', '-', safe)  # 多个连字符合并
        safe = safe.strip('-')
        return safe or "unnamed-project"


# 创建单例
project_storage_service = ProjectStorageService()


# ========== 便捷函数（供其他 Agent 调用） ==========

async def save_project_document(
    project_name: str,
    content: str,
    filename: str,
    agent_type: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    保存项目文档的便捷函数
    
    示例用法（在 Agent 中）:
        from app.services.project_storage_service import save_project_document
        
        result = await save_project_document(
            project_name="sogoodtea-website",
            content=document_content,
            filename="architecture.md",
            agent_type="coordinator",
            description="网站架构设计文档"
        )
    """
    return await project_storage_service.save_text_file(
        project_name=project_name,
        content=content,
        filename=filename,
        agent_type=agent_type,
        metadata={"description": description}
    )


async def save_project_code(
    project_name: str,
    files: Dict[str, str],
    description: str = ""
) -> Dict[str, Any]:
    """
    保存项目代码的便捷函数
    
    示例用法:
        from app.services.project_storage_service import save_project_code
        
        result = await save_project_code(
            project_name="sogoodtea-website",
            files={
                "index.html": html_content,
                "styles.css": css_content,
                "app.js": js_content
            },
            description="首页代码"
        )
    """
    return await project_storage_service.save_multiple_files(
        project_name=project_name,
        files=files,
        agent_type="code_engineer"
    )


async def save_project_content(
    project_name: str,
    content: str,
    filename: str,
    page_name: str = ""
) -> Dict[str, Any]:
    """
    保存项目文案的便捷函数
    
    示例用法:
        from app.services.project_storage_service import save_project_content
        
        result = await save_project_content(
            project_name="sogoodtea-website",
            content=copy_content,
            filename="homepage-copy.md",
            page_name="首页"
        )
    """
    return await project_storage_service.save_text_file(
        project_name=project_name,
        content=content,
        filename=filename,
        agent_type="copywriter",
        metadata={"page": page_name}
    )


async def ensure_project_exists(
    project_name: str,
    description: str = "",
    created_by: str = "maria"
) -> Dict[str, Any]:
    """
    确保项目存在（不存在则创建）
    """
    # 先检查项目是否存在
    info = await project_storage_service.get_project_info(project_name)
    
    if info.get("success"):
        return {
            "success": True,
            "exists": True,
            "project": info.get("project")
        }
    
    # 不存在，创建新项目
    result = await project_storage_service.create_project(
        project_name=project_name,
        description=description,
        created_by=created_by
    )
    
    if result.get("success"):
        return {
            "success": True,
            "exists": False,
            "created": True,
            "project": result
        }
    
    return result
