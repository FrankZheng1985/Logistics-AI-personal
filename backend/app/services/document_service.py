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
            # 尝试处理 .doc (旧格式通常很难直接用 python 读取，建议提示用户转 docx)
            if filepath.endswith(".doc"):
                raise ValueError("暂不支持旧版 .doc 格式，请另存为 .docx 后重试")
            raise e

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
