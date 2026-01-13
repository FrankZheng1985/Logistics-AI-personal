"""
小文 - 文案策划
负责广告文案、视频脚本、营销内容
"""
from typing import Dict, Any, List
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
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
        
        prompt = SCRIPT_WRITING_PROMPT.format(
            title=title,
            description=description,
            video_type=video_type,
            duration=duration
        )
        
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
