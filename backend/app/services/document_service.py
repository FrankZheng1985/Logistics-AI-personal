"""
文档生成服务 - 支持 Word 和 PPT 生成
Clauwdbot 的专业文档输出能力
"""
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.llm import chat_completion


# 文档输出目录
DOCUMENT_OUTPUT_DIR = os.environ.get("DOCUMENT_OUTPUT_DIR", "/tmp/documents")
os.makedirs(DOCUMENT_OUTPUT_DIR, exist_ok=True)


class DocumentService:
    """文档生成服务：Word 计划书 / PPT 演示文档"""
    
    async def generate_word(self, topic: str, requirements: str = "", style: str = "professional") -> Dict[str, Any]:
        """
        生成 Word 文档（计划书、报告、方案等）
        
        Args:
            topic: 文档主题
            requirements: 额外要求
            style: 风格（professional/简洁/详细）
        
        Returns:
            {"success": bool, "filepath": str, "filename": str, "summary": str}
        """
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            return {"success": False, "error": "python-docx 未安装，无法生成Word文档"}
        
        try:
            # 用 LLM 生成文档结构和内容
            content_prompt = f"""请为以下主题生成一份专业的商业文档内容。

主题：{topic}
额外要求：{requirements or '无'}
风格：{style}

请返回JSON格式，包含以下结构：
{{
    "title": "文档标题",
    "subtitle": "副标题（可选）",
    "sections": [
        {{
            "heading": "章节标题",
            "content": "章节正文内容（详细、专业，每段100-200字）",
            "bullet_points": ["要点1", "要点2"]
        }}
    ],
    "conclusion": "总结",
    "date": "日期"
}}

要求：
1. 内容要专业、有深度，体现行业洞察
2. 至少5个章节
3. 每个章节要有实质内容，不要空话
4. 如果涉及物流行业，要用专业术语
只返回JSON，不要其他内容。"""

            import json
            import re
            
            response = await chat_completion(
                messages=[{"role": "user", "content": content_prompt}],
                use_advanced=True,
                max_tokens=4000,
                temperature=0.7
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"success": False, "error": "LLM 未能生成有效的文档内容"}
            
            doc_data = json.loads(json_match.group())
            
            # 创建 Word 文档
            doc = Document()
            
            # 设置默认字体
            style_obj = doc.styles['Normal']
            font = style_obj.font
            font.name = 'Microsoft YaHei'
            font.size = Pt(11)
            
            # 标题
            title = doc.add_heading(doc_data.get("title", topic), level=0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 副标题
            if doc_data.get("subtitle"):
                subtitle = doc.add_paragraph(doc_data["subtitle"])
                subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
                subtitle.runs[0].font.size = Pt(14)
                subtitle.runs[0].font.color.rgb = RGBColor(100, 100, 100)
            
            # 日期
            date_para = doc.add_paragraph(doc_data.get("date", datetime.now().strftime("%Y年%m月%d日")))
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            date_para.runs[0].font.size = Pt(10)
            date_para.runs[0].font.color.rgb = RGBColor(150, 150, 150)
            
            doc.add_paragraph("")  # 空行
            
            # 章节内容
            for i, section in enumerate(doc_data.get("sections", []), 1):
                doc.add_heading(f"{i}. {section['heading']}", level=1)
                
                # 正文
                if section.get("content"):
                    doc.add_paragraph(section["content"])
                
                # 要点列表
                if section.get("bullet_points"):
                    for point in section["bullet_points"]:
                        doc.add_paragraph(point, style='List Bullet')
                
                doc.add_paragraph("")  # 段间空行
            
            # 总结
            if doc_data.get("conclusion"):
                doc.add_heading("总结", level=1)
                doc.add_paragraph(doc_data["conclusion"])
            
            # 保存文件
            safe_title = "".join(c for c in doc_data.get("title", topic)[:20] if c.isalnum() or c in " _-")
            filename = f"{safe_title}_{uuid.uuid4().hex[:6]}.docx"
            filepath = os.path.join(DOCUMENT_OUTPUT_DIR, filename)
            doc.save(filepath)
            
            logger.info(f"[DocumentService] Word文档生成成功: {filepath}")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "title": doc_data.get("title", topic),
                "sections_count": len(doc_data.get("sections", [])),
                "summary": f"已生成《{doc_data.get('title', topic)}》，共{len(doc_data.get('sections', []))}个章节"
            }
            
        except Exception as e:
            logger.error(f"[DocumentService] Word文档生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_ppt(self, topic: str, requirements: str = "", slides_count: int = 10) -> Dict[str, Any]:
        """
        生成 PPT 演示文稿
        
        Args:
            topic: 演示主题
            requirements: 额外要求
            slides_count: 页数
        
        Returns:
            {"success": bool, "filepath": str, "filename": str, "summary": str}
        """
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
        except ImportError:
            return {"success": False, "error": "python-pptx 未安装，无法生成PPT"}
        
        try:
            # 用 LLM 生成 PPT 内容
            content_prompt = f"""请为以下主题生成一份专业的PPT演示文稿内容。

主题：{topic}
额外要求：{requirements or '无'}
页数要求：{slides_count}页

请返回JSON格式：
{{
    "title": "演示标题",
    "subtitle": "副标题",
    "slides": [
        {{
            "title": "页面标题",
            "content": ["要点1", "要点2", "要点3"],
            "notes": "演讲备注（可选）"
        }}
    ]
}}

要求：
1. 每页3-5个要点，每个要点简洁有力（10-25字）
2. 内容要有逻辑递进关系
3. 包含：背景/现状 -> 分析/问题 -> 方案/策略 -> 行动计划 -> 总结
4. 最后一页是总结或行动号召
只返回JSON，不要其他内容。"""

            import json
            import re
            
            response = await chat_completion(
                messages=[{"role": "user", "content": content_prompt}],
                use_advanced=True,
                max_tokens=4000,
                temperature=0.7
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"success": False, "error": "LLM 未能生成有效的PPT内容"}
            
            ppt_data = json.loads(json_match.group())
            
            # 创建 PPT
            prs = Presentation()
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)
            
            # 封面页
            slide_layout = prs.slide_layouts[0]  # 标题布局
            slide = prs.slides.add_slide(slide_layout)
            title_shape = slide.shapes.title
            subtitle_shape = slide.placeholders[1]
            
            title_shape.text = ppt_data.get("title", topic)
            subtitle_shape.text = ppt_data.get("subtitle", datetime.now().strftime("%Y年%m月"))
            
            # 设置封面样式
            for paragraph in title_shape.text_frame.paragraphs:
                paragraph.font.size = Pt(40)
                paragraph.font.bold = True
                paragraph.font.color.rgb = RGBColor(44, 62, 80)
            
            # 内容页
            for slide_data in ppt_data.get("slides", []):
                slide_layout = prs.slide_layouts[1]  # 标题+内容布局
                slide = prs.slides.add_slide(slide_layout)
                
                # 页面标题
                title_shape = slide.shapes.title
                title_shape.text = slide_data.get("title", "")
                for paragraph in title_shape.text_frame.paragraphs:
                    paragraph.font.size = Pt(28)
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = RGBColor(44, 62, 80)
                
                # 内容要点
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                tf.clear()
                
                for i, point in enumerate(slide_data.get("content", [])):
                    if i == 0:
                        tf.paragraphs[0].text = point
                        p = tf.paragraphs[0]
                    else:
                        p = tf.add_paragraph()
                        p.text = point
                    
                    p.font.size = Pt(18)
                    p.space_after = Pt(12)
                    p.font.color.rgb = RGBColor(52, 73, 94)
                
                # 演讲备注
                if slide_data.get("notes"):
                    slide.notes_slide.notes_text_frame.text = slide_data["notes"]
            
            # 保存文件
            safe_title = "".join(c for c in ppt_data.get("title", topic)[:20] if c.isalnum() or c in " _-")
            filename = f"{safe_title}_{uuid.uuid4().hex[:6]}.pptx"
            filepath = os.path.join(DOCUMENT_OUTPUT_DIR, filename)
            prs.save(filepath)
            
            total_slides = len(ppt_data.get("slides", [])) + 1  # +1 封面
            logger.info(f"[DocumentService] PPT生成成功: {filepath}, {total_slides}页")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "title": ppt_data.get("title", topic),
                "slides_count": total_slides,
                "summary": f"已生成《{ppt_data.get('title', topic)}》PPT，共{total_slides}页"
            }
            
        except Exception as e:
            logger.error(f"[DocumentService] PPT生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_code(self, requirement: str, language: str = "python") -> Dict[str, Any]:
        """
        生成代码
        
        Args:
            requirement: 代码需求描述
            language: 编程语言
        
        Returns:
            {"success": bool, "code": str, "explanation": str}
        """
        try:
            code_prompt = f"""请根据以下需求编写{language}代码。

需求：{requirement}

要求：
1. 代码要简洁、高效、可运行
2. 关键逻辑加注释
3. 包含错误处理
4. 如果需要第三方库，在开头注明

返回格式：
```{language}
// 代码内容
```

说明：简要解释代码做了什么"""

            response = await chat_completion(
                messages=[{"role": "user", "content": code_prompt}],
                use_advanced=True,
                max_tokens=4000,
                temperature=0.3
            )
            
            return {
                "success": True,
                "code": response,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"[DocumentService] 代码生成失败: {e}")
            return {"success": False, "error": str(e)}


# 单例
document_service = DocumentService()
