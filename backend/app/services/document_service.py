"""
文档生成服务 - 支持 Word 和 PPT 生成
Clauwdbot 的专业文档输出能力

字体规范：
- 中文正文：微软雅黑 (Microsoft YaHei) 11pt
- 中文标题：微软雅黑 (Microsoft YaHei) Bold
- 英文/数字：Calibri
- 服务器回退字体：WenQuanYi Micro Hei
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

# ==================== 字体常量 ====================
# 中文字体（东亚字体，用于 CJK 字符）
CN_FONT = "Microsoft YaHei"
# 英文字体（拉丁字体，用于英文和数字）
EN_FONT = "Calibri"


class DocumentService:
    """文档生成服务：Word 计划书 / PPT 演示文档"""
    
    # ==================== 字体工具方法 ====================
    
    @staticmethod
    def _set_run_font(run, cn_font=CN_FONT, en_font=EN_FONT, size=None, bold=False, color=None):
        """
        统一设置 run 的中英文字体（解决 python-docx 不设置东亚字体导致中文乱码的问题）
        
        python-docx 的 font.name 只设置拉丁字体(w:ascii, w:hAnsi)，
        中文字符需要单独设置东亚字体(w:eastAsia)。
        """
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor
        
        # 设置拉丁字体（英文、数字）
        run.font.name = en_font
        
        # 设置东亚字体（中文）—— 这是关键！
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = run._element.makeelement(qn('w:rFonts'), {})
            rPr.insert(0, rFonts)
        rFonts.set(qn('w:eastAsia'), cn_font)
        rFonts.set(qn('w:ascii'), en_font)
        rFonts.set(qn('w:hAnsi'), en_font)
        
        if size:
            run.font.size = Pt(size)
        if bold:
            run.font.bold = True
        if color:
            run.font.color.rgb = RGBColor(*color)
    
    @staticmethod
    def _set_style_font(style_obj, cn_font=CN_FONT, en_font=EN_FONT, size=None):
        """设置 Word 样式的中英文字体"""
        from docx.oxml.ns import qn
        from docx.shared import Pt
        
        style_obj.font.name = en_font
        if size:
            style_obj.font.size = Pt(size)
        
        # 设置东亚字体
        rPr = style_obj.element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = style_obj.element.makeelement(qn('w:rFonts'), {})
            rPr.insert(0, rFonts)
        rFonts.set(qn('w:eastAsia'), cn_font)
    
    @staticmethod
    def _set_ppt_run_font(run, cn_font=CN_FONT, en_font=EN_FONT, size=None, bold=False, color=None):
        """
        统一设置 PPT run 的中英文字体
        python-pptx 的 font.name 只设置拉丁字体，需要通过 XML 设置东亚字体
        """
        from pptx.util import Pt
        from pptx.dml.color import RGBColor
        from lxml import etree
        
        # 设置拉丁字体
        run.font.name = en_font
        if size:
            run.font.size = Pt(size)
        if bold:
            run.font.bold = bold
        if color:
            run.font.color.rgb = RGBColor(*color)
        
        # 设置东亚字体 —— 通过 XML
        rPr = run._r.get_or_add_rPr()
        nsmap = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        
        # 移除现有的 ea 字体设置
        for ea in rPr.findall('.//a:ea', nsmap):
            rPr.remove(ea)
        
        # 添加东亚字体
        ea_elem = etree.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}ea')
        ea_elem.set('typeface', cn_font)
        
        # 同时确保拉丁字体也设置了
        for latin in rPr.findall('.//a:latin', nsmap):
            rPr.remove(latin)
        latin_elem = etree.SubElement(rPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}latin')
        latin_elem.set('typeface', en_font)
    
    # ==================== Word 文档生成 ====================
    
    async def generate_word(self, topic: str, requirements: str = "", style: str = "professional") -> Dict[str, Any]:
        """
        生成 Word 文档（计划书、报告、方案等）
        
        字体：正文 微软雅黑 11pt / 标题 微软雅黑 Bold
        """
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor, Cm
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.oxml.ns import qn
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
            
            # ===== 创建 Word 文档 =====
            doc = Document()
            
            # ----- 全局字体设置：覆盖所有内置样式 -----
            for style_name in ['Normal', 'List Bullet', 'List Number']:
                try:
                    self._set_style_font(doc.styles[style_name], size=11)
                except KeyError:
                    pass
            
            # 设置 Heading 样式的字体
            for i in range(4):
                try:
                    heading_style = doc.styles[f'Heading {i}']
                    heading_sizes = {0: 22, 1: 16, 2: 14, 3: 12}
                    self._set_style_font(heading_style, size=heading_sizes.get(i, 14))
                    heading_style.font.bold = True
                    heading_style.font.color.rgb = RGBColor(31, 56, 100)
                except KeyError:
                    pass
            
            # ----- 页面边距 -----
            for section in doc.sections:
                section.top_margin = Cm(2.5)
                section.bottom_margin = Cm(2.5)
                section.left_margin = Cm(3)
                section.right_margin = Cm(3)
            
            # ----- 文档标题 -----
            title_para = doc.add_heading(doc_data.get("title", topic), level=0)
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in title_para.runs:
                self._set_run_font(run, size=24, bold=True, color=(31, 56, 100))
            
            # ----- 副标题 -----
            if doc_data.get("subtitle"):
                subtitle_para = doc.add_paragraph()
                subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = subtitle_para.add_run(doc_data["subtitle"])
                self._set_run_font(run, size=14, color=(100, 100, 100))
            
            # ----- 日期 -----
            date_para = doc.add_paragraph()
            date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            date_text = doc_data.get("date", datetime.now().strftime("%Y 年 %m 月 %d 日"))
            run = date_para.add_run(date_text)
            self._set_run_font(run, size=10, color=(150, 150, 150))
            
            doc.add_paragraph("")  # 空行
            
            # ----- 章节内容 -----
            for i, section_data in enumerate(doc_data.get("sections", []), 1):
                # 章节标题
                heading_para = doc.add_heading(f"{i}. {section_data['heading']}", level=1)
                for run in heading_para.runs:
                    self._set_run_font(run, size=16, bold=True, color=(31, 56, 100))
                
                # 章节正文
                if section_data.get("content"):
                    body_para = doc.add_paragraph()
                    # 设置段落格式：首行缩进、行距
                    body_para.paragraph_format.first_line_indent = Cm(0.74)  # 两个字符缩进
                    body_para.paragraph_format.line_spacing = 1.5
                    run = body_para.add_run(section_data["content"])
                    self._set_run_font(run, size=11)
                
                # 要点列表
                if section_data.get("bullet_points"):
                    for point in section_data["bullet_points"]:
                        bullet_para = doc.add_paragraph(style='List Bullet')
                        bullet_para.clear()
                        run = bullet_para.add_run(point)
                        self._set_run_font(run, size=11)
                        bullet_para.paragraph_format.line_spacing = 1.3
                
                doc.add_paragraph("")  # 段间空行
            
            # ----- 总结 -----
            if doc_data.get("conclusion"):
                conclusion_heading = doc.add_heading("总结", level=1)
                for run in conclusion_heading.runs:
                    self._set_run_font(run, size=16, bold=True, color=(31, 56, 100))
                
                conclusion_para = doc.add_paragraph()
                conclusion_para.paragraph_format.first_line_indent = Cm(0.74)
                conclusion_para.paragraph_format.line_spacing = 1.5
                run = conclusion_para.add_run(doc_data["conclusion"])
                self._set_run_font(run, size=11)
            
            # ----- 保存文件 -----
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
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
    
    # ==================== PPT 生成 ====================
    
    async def generate_ppt(self, topic: str, requirements: str = "", slides_count: int = 10) -> Dict[str, Any]:
        """
        生成 PPT 演示文稿
        
        字体：标题 微软雅黑 Bold / 内容 微软雅黑
        配色：深蓝系（#1F3864 标题，#2C3E50 内容）
        """
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt, Cm, Emu
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
            
            # ===== 创建 PPT =====
            prs = Presentation()
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)
            
            # ----- 封面页 -----
            slide_layout = prs.slide_layouts[0]  # 标题布局
            slide = prs.slides.add_slide(slide_layout)
            title_shape = slide.shapes.title
            subtitle_shape = slide.placeholders[1]
            
            # 封面标题
            title_shape.text_frame.clear()
            p = title_shape.text_frame.paragraphs[0]
            p.text = ppt_data.get("title", topic)
            p.alignment = PP_ALIGN.CENTER
            for run in p.runs:
                self._set_ppt_run_font(run, size=40, bold=True, color=(31, 56, 100))
            
            # 封面副标题
            subtitle_shape.text_frame.clear()
            p = subtitle_shape.text_frame.paragraphs[0]
            p.text = ppt_data.get("subtitle", datetime.now().strftime("%Y年%m月"))
            p.alignment = PP_ALIGN.CENTER
            for run in p.runs:
                self._set_ppt_run_font(run, size=20, color=(100, 100, 100))
            
            # ----- 内容页 -----
            for slide_data in ppt_data.get("slides", []):
                slide_layout = prs.slide_layouts[1]  # 标题+内容布局
                slide = prs.slides.add_slide(slide_layout)
                
                # 页面标题
                title_shape = slide.shapes.title
                title_shape.text_frame.clear()
                p = title_shape.text_frame.paragraphs[0]
                p.text = slide_data.get("title", "")
                for run in p.runs:
                    self._set_ppt_run_font(run, size=28, bold=True, color=(31, 56, 100))
                
                # 内容要点
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                tf.clear()
                
                for i, point in enumerate(slide_data.get("content", [])):
                    if i == 0:
                        p = tf.paragraphs[0]
                    else:
                        p = tf.add_paragraph()
                    
                    p.text = f"• {point}"
                    p.space_after = Pt(14)
                    p.line_spacing = 1.4
                    
                    for run in p.runs:
                        self._set_ppt_run_font(run, size=18, color=(52, 73, 94))
                
                # 演讲备注
                if slide_data.get("notes"):
                    slide.notes_slide.notes_text_frame.text = slide_data["notes"]
            
            # ----- 保存文件 -----
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
            import traceback
            logger.error(traceback.format_exc())
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
