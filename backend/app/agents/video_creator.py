"""
小视 - 视频创作员
负责生成物流广告视频、产品展示视频
"""
from typing import Dict, Any, Optional
import json
import httpx
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings
from app.core.prompts.video_creator import (
    VIDEO_CREATOR_SYSTEM_PROMPT,
    VIDEO_PROMPT_GENERATION
)


class VideoCreatorAgent(BaseAgent):
    """小视 - 视频创作员"""
    
    name = "小视"
    agent_type = AgentType.VIDEO_CREATOR
    description = "视频创作员 - 生成物流广告视频、产品展示视频"
    
    def __init__(self):
        super().__init__()
        self.keling_api_key = settings.KELING_API_KEY
        self.keling_api_url = settings.KELING_API_URL
    
    def _build_system_prompt(self) -> str:
        return VIDEO_CREATOR_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频生成任务
        
        Args:
            input_data: {
                "title": "视频标题",
                "script": "视频脚本",
                "keywords": ["关键词列表"]
            }
        
        Returns:
            {
                "video_prompt": "生成的提示词",
                "video_url": "视频URL（如果生成成功）",
                "status": "状态"
            }
        """
        title = input_data.get("title", "")
        script = input_data.get("script", "")
        keywords = input_data.get("keywords", [])
        
        # 第一步：生成视频提示词
        prompt_result = await self._generate_video_prompt(title, script, keywords)
        
        # 第二步：调用视频生成API
        if self.keling_api_key:
            video_result = await self._call_video_api(prompt_result)
        else:
            video_result = {
                "status": "api_not_configured",
                "message": "可灵API未配置，请在环境变量中设置KELING_API_KEY"
            }
        
        self.log(f"视频任务处理完成: {title}")
        
        return {
            "video_prompt": prompt_result,
            **video_result
        }
    
    async def _generate_video_prompt(
        self, 
        title: str, 
        script: str, 
        keywords: list
    ) -> Dict[str, Any]:
        """生成视频提示词"""
        prompt = VIDEO_PROMPT_GENERATION.format(
            title=title,
            script=script,
            keywords=", ".join(keywords)
        )
        
        response = await self.think([{"role": "user", "content": prompt}])
        
        # 解析JSON
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass
        
        # 解析失败，返回默认结构
        return {
            "main_prompt": f"物流宣传视频：{title}，专业高效的物流服务",
            "style": "商务专业",
            "music_suggestion": "轻快企业宣传风格",
            "visual_effects": ["平滑过渡", "文字标注"]
        }
    
    async def _call_video_api(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用可灵视频生成API"""
        if not self.keling_api_key:
            return {"status": "error", "message": "API密钥未配置"}
        
        # 可灵API调用（示例结构，实际需根据API文档调整）
        headers = {
            "Authorization": f"Bearer {self.keling_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt_data.get("main_prompt", ""),
            "style": prompt_data.get("style", "商务专业"),
            "duration": 30,  # 30秒视频
            "aspect_ratio": "16:9"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.keling_api_url}/video/generate",
                    headers=headers,
                    json=payload,
                    timeout=120.0  # 视频生成需要较长时间
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "task_id": result.get("task_id"),
                        "video_url": result.get("video_url"),
                        "message": "视频生成任务已提交"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"API调用失败: {response.status_code}"
                    }
        except Exception as e:
            self.log(f"视频API调用失败: {e}", "error")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def check_video_status(self, task_id: str) -> Dict[str, Any]:
        """检查视频生成状态"""
        if not self.keling_api_key:
            return {"status": "error", "message": "API密钥未配置"}
        
        headers = {
            "Authorization": f"Bearer {self.keling_api_key}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.keling_api_url}/video/status/{task_id}",
                    headers=headers
                )
                return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}


# 创建单例并注册
video_creator_agent = VideoCreatorAgent()
AgentRegistry.register(video_creator_agent)
