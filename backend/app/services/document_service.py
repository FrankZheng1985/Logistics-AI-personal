"""
文档处理服务
负责解析 Word, PDF, TXT 等文档内容，赋予 Maria "阅读" 能力
"""
import os
import io
from typing import Optional, Dict, Any
from loguru import logger

class DocumentService:
    
    def __init__(self):
        pass

    async def read_document(self, filepath: str, filename: str) -> Dict[str, Any]:
        """
        读取文档内容
        
        Args:
            filepath: 文件本地路径
            filename: 原始文件名
            
        Returns:
            {
                "success": bool,
                "content": str,  # 提取的文本内容
                "type": str,     # 文档类型
                "error": str
            }
        """
        if not os.path.exists(filepath):
            return {"success": False, "error": "文件不存在"}
        
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            content = ""
            
            if ext in [".docx", ".doc"]:
                content = self._read_docx(filepath)
            elif ext == ".pdf":
                content = self._read_pdf(filepath)
            elif ext in [".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".html"]:
                content = self._read_text(filepath)
            else:
                return {"success": False, "error": f"不支持的文件格式: {ext}"}
            
            # 限制内容长度，避免 Token 溢出 (例如限制前 50000 字符)
            # 如果需要处理超长文档，可能需要 RAG 分块，这里先做简单截断
            if len(content) > 50000:
                content = content[:50000] + "\n\n...(文档过长，已截断)..."
                
            return {
                "success": True,
                "content": content,
                "type": ext,
                "length": len(content)
            }
            
        except Exception as e:
            logger.error(f"文档解析失败: {filename} - {e}")
            return {"success": False, "error": f"解析失败: {str(e)}"}

    def _read_docx(self, filepath: str) -> str:
        """解析 Word 文档"""
        # 先尝试用 python-docx 读取 (适用于 .docx)
        try:
            import docx
            doc = docx.Document(filepath)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
        except ImportError:
            raise ImportError("请安装 python-docx 库")
        except Exception as e:
            # 如果失败且是 .doc 文件，尝试用 antiword
            if filepath.endswith(".doc") or "Package not found" in str(e) or "not a valid" in str(e).lower():
                return self._read_doc_with_antiword(filepath)
            raise e
    
    def _read_doc_with_antiword(self, filepath: str) -> str:
        """使用 antiword 解析旧版 .doc 文件"""
        import subprocess
        try:
            # 使用 antiword 命令行工具
            result = subprocess.run(
                ['antiword', filepath],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                content = result.stdout
                if content.strip():
                    logger.info(f"[Document] antiword 成功解析 .doc 文件: {len(content)} 字符")
                    return content
            
            # antiword 失败，尝试 catdoc
            result = subprocess.run(
                ['catdoc', '-w', filepath],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info(f"[Document] catdoc 成功解析 .doc 文件: {len(result.stdout)} 字符")
                return result.stdout
            
            # 都失败了，提示用户
            raise ValueError("无法读取 .doc 文件内容，请另存为 .docx 格式后重试")
            
        except FileNotFoundError:
            raise ValueError("服务器缺少 antiword/catdoc 工具，无法处理旧版 .doc 文件")
        except subprocess.TimeoutExpired:
            raise ValueError("处理 .doc 文件超时")
        except Exception as e:
            raise ValueError(f"解析 .doc 文件失败: {e}")

    def _read_pdf(self, filepath: str) -> str:
        """解析 PDF 文档"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise ImportError("请安装 pypdf 库")

    def _read_text(self, filepath: str) -> str:
        """解析纯文本文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    return f.read()
            except:
                raise ValueError("无法识别文件编码")

# 单例
document_service = DocumentService()
