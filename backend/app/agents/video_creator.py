"""
小视 - 视频创作员
负责生成物流广告视频、产品展示视频
"""
from typing import Dict, Any, Optional
import json
import time
import httpx
import jwt
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
        self.access_key = settings.KELING_ACCESS_KEY
        self.secret_key = settings.KELING_SECRET_KEY
        self.keling_api_url = settings.KELING_API_URL
    
    def _generate_jwt_token(self) -> str:
        """生成可灵AI的JWT认证token"""
        headers = {
            "alg": "HS256",
            "typ": "JWT"
        }
        payload = {
            "iss": self.access_key,
            "exp": int(time.time()) + 1800,  # 30分钟过期
            "nbf": int(time.time()) - 5
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)
    
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
        if self.access_key and self.secret_key:
            video_result = await self._call_video_api(prompt_result)
        else:
            video_result = {
                "status": "api_not_configured",
                "message": "可灵AI API未配置，请设置KELING_ACCESS_KEY和KELING_SECRET_KEY"
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
        """调用可灵AI视频生成API"""
        if not self.access_key or not self.secret_key:
            return {"status": "api_not_configured", "message": "可灵AI API密钥未配置"}
        
        # 生成JWT token
        token = self._generate_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 可灵AI API参数
        payload = {
            "model": "kling-v1",  # 使用v1模型
            "prompt": prompt_data.get("main_prompt", ""),
            "negative_prompt": "",
            "cfg_scale": 0.5,
            "mode": "std",  # std标准模式，pro专业模式
            "aspect_ratio": "16:9",
            "duration": "5"  # 5秒或10秒
        }
        
        try:
            self.log(f"调用可灵AI API: {self.keling_api_url}/v1/videos/text2video")
            
            async with httpx.AsyncClient() as client:
                # 创建视频生成任务
                response = await client.post(
                    f"{self.keling_api_url}/v1/videos/text2video",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                self.log(f"API响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("data", {}).get("task_id")
                    
                    if task_id:
                        self.log(f"视频任务已创建: {task_id}")
                        # 轮询检查任务状态
                        video_url = await self._poll_video_status(task_id, headers)
                        if video_url:
                            return {
                                "status": "success",
                                "task_id": task_id,
                                "video_url": video_url,
                                "message": "视频生成成功"
                            }
                        else:
                            return {
                                "status": "processing",
                                "task_id": task_id,
                                "message": "视频正在生成中，请稍后查看"
                            }
                    else:
                        return {
                            "status": "error",
                            "message": f"API返回异常: {result}"
                        }
                else:
                    error_text = response.text
                    self.log(f"API调用失败: {response.status_code} - {error_text}", "error")
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
    
    async def _poll_video_status(self, task_id: str, headers: dict, max_attempts: int = 60) -> Optional[str]:
        """轮询检查视频生成状态，最长等待5分钟"""
        import asyncio
        async with httpx.AsyncClient() as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(
                        f"{self.keling_api_url}/v1/videos/text2video/{task_id}",
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        data = result.get("data", {})
                        status = data.get("task_status")
                        
                        # 每10次输出一次日志，避免日志过多
                        if attempt % 10 == 0 or status in ["succeed", "failed"]:
                            self.log(f"任务状态: {status} (尝试 {attempt + 1}/{max_attempts})")
                        
                        if status == "succeed":
                            videos = data.get("task_result", {}).get("videos", [])
                            if videos:
                                video_url = videos[0].get("url")
                                self.log(f"视频生成成功！URL长度: {len(video_url) if video_url else 0}")
                                return video_url
                        elif status == "failed":
                            self.log(f"视频生成失败: {data.get('task_status_msg')}", "error")
                            return None
                        
                        # 等待5秒后再次查询
                        await asyncio.sleep(5)
                    else:
                        self.log(f"查询状态失败: {response.status_code}", "error")
                        break
                        
                except Exception as e:
                    self.log(f"轮询异常: {e}", "error")
                    break
        
        self.log(f"轮询超时，任务ID: {task_id}", "warning")
        return None
    
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
