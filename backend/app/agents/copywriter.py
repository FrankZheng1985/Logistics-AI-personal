"""
小文 - 文案策划
负责广告文案、视频脚本、营销内容
"""
from typing import Dict, Any, List
from loguru import logger
from sqlalchemy import select

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from app.models.company_config import CompanyConfig
from app.core.prompts.copywriter import (
    COPYWRITER_SYSTEM_PROMPT, 
    SCRIPT_WRITING_PROMPT,
    MOMENTS_COPY_PROMPT
)


class CopywriterAgent(BaseAgent):
    """小文 - 文案策划"""
    
    name = "小文"
    agent_type = AgentType.COPYWRITER
    description = "文案策划 - 负责广告文案、朋友圈文案、视频脚本"
    
    def _build_system_prompt(self) -> str:
        return COPYWRITER_SYSTEM_PROMPT
    
    async def _get_company_context(self) -> str:
        """从数据库获取公司上下文信息"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CompanyConfig).limit(1))
                config = result.scalar_one_or_none()
                
                if not config:
                    return ""
                
                lines = []
                
                if config.company_name:
                    lines.append(f"公司名称：{config.company_name}")
                
                if config.company_intro:
                    lines.append(f"公司简介：{config.company_intro}")
                
                if config.products:
                    products_text = []
                    for p in config.products:
                        name = p.get('name', '')
                        desc = p.get('description', '')
                        features = p.get('features', [])
                        if name:
                            products_text.append(f"- {name}: {desc}")
                    if products_text:
                        lines.append("主营产品服务：")
                        lines.extend(products_text)
                
                if config.service_routes:
                    routes_text = []
                    for r in config.service_routes:
                        from_loc = r.get('from_location', '')
                        to_loc = r.get('to_location', '')
                        transport = r.get('transport', '')
                        if from_loc and to_loc:
                            routes_text.append(f"- {from_loc}→{to_loc} ({transport})")
                    if routes_text:
                        lines.append("服务航线：")
                        lines.extend(routes_text[:5])  # 最多5条
                
                if config.advantages:
                    lines.append(f"公司优势：{', '.join(config.advantages)}")
                
                if config.contact_phone:
                    lines.append(f"联系电话：{config.contact_phone}")
                
                return "\n".join(lines)
        except Exception as e:
            logger.error(f"获取公司配置失败: {e}")
            return ""
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理文案创作任务
        
        Args:
            input_data: {
                "task_type": "script/moments/email/ad",
                "title": "标题",
                "description": "描述",
                ...其他参数
            }
        
        Returns:
            创作结果
        """
        task_type = input_data.get("task_type", "script")
        
        if task_type == "script":
            return await self._write_script(input_data)
        elif task_type == "moments":
            return await self._write_moments(input_data)
        else:
            return await self._write_general(input_data)
    
    async def _write_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写视频脚本"""
        title = input_data.get("title", "物流服务介绍")
        description = input_data.get("description", "")
        video_type = input_data.get("video_type", "ad")
        duration = input_data.get("duration", 30)
        
        # 获取公司上下文
        company_context = await self._get_company_context()
        
        # 增强版提示词，包含公司信息
        prompt = f"""请为视频撰写脚本。

## 公司背景信息
{company_context if company_context else "暂未配置公司信息，请使用通用物流公司背景"}

## 视频要求
- 标题：{title}
- 描述：{description}
- 类型：{video_type}
- 时长：约{duration}秒

## 脚本要求
1. 融入公司名称和优势（如有配置）
2. 突出产品服务特点
3. 适合短视频平台传播
4. 结尾引导留下联系方式

请输出完整的视频脚本，包括画面描述和旁白文字。同时在最后列出5-8个适合AI视频生成的关键词。

格式要求：
【画面描述】...
【旁白/文字】...

关键词：xxx, xxx, xxx
"""
        
        script = await self.think([{"role": "user", "content": prompt}])
        
        # 提取关键词
        keywords = self._extract_keywords(script)
        
        self.log(f"完成脚本撰写: {title}")
        
        return {
            "script": script,
            "keywords": keywords,
            "title": title,
            "video_type": video_type
        }
    
    async def _write_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写朋友圈文案"""
        topic = input_data.get("topic", "物流服务")
        purpose = input_data.get("purpose", "获客引流")
        target_audience = input_data.get("target_audience", "有物流需求的外贸商家")
        
        prompt = MOMENTS_COPY_PROMPT.format(
            topic=topic,
            purpose=purpose,
            target_audience=target_audience
        )
        
        copy = await self.think([{"role": "user", "content": prompt}])
        
        self.log(f"完成朋友圈文案: {topic}")
        
        return {
            "copy": copy,
            "topic": topic
        }
    
    async def _write_general(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """通用文案撰写"""
        requirement = input_data.get("requirement", "")
        
        content = await self.think([{"role": "user", "content": requirement}])
        
        return {"content": content}
    
    def _extract_keywords(self, script: str) -> List[str]:
        """从脚本中提取关键词"""
        # 尝试从脚本中找关键词部分
        keywords = []
        
        if "关键词" in script:
            # 找到关键词行
            lines = script.split("\n")
            for i, line in enumerate(lines):
                if "关键词" in line:
                    # 获取下一行或同一行的关键词
                    keyword_line = line.split("：")[-1].split(":")[-1]
                    if not keyword_line.strip() and i + 1 < len(lines):
                        keyword_line = lines[i + 1]
                    keywords = [k.strip() for k in keyword_line.replace("，", ",").split(",") if k.strip()]
                    break
        
        # 如果没找到，使用默认关键词
        if not keywords:
            keywords = ["物流", "货运", "快速", "安全", "专业"]
        
        return keywords[:8]  # 最多8个关键词


# 创建单例并注册
copywriter_agent = CopywriterAgent()
AgentRegistry.register(copywriter_agent)
