"""
小视 - 视频创作员
负责生成物流广告视频、产品展示视频
支持混合方案：AI生成画面 + 后期叠加文字 + TTS配音 + 背景音乐
"""
from typing import Dict, Any, Optional, List
import json
import time
import os
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
    """小视 - 视频创作员（混合方案版本）"""
    
    name = "小视"
    agent_type = AgentType.VIDEO_CREATOR
    description = "视频创作员 - 生成高质量物流广告视频（AI画面+清晰文字+配音）"
    
    def __init__(self):
        super().__init__()
        self.access_key = settings.KELING_ACCESS_KEY
        self.secret_key = settings.KELING_SECRET_KEY
        self.keling_api_url = settings.KELING_API_URL
        # 是否启用后期处理
        self.enable_post_processing = getattr(settings, 'VIDEO_POST_PROCESSING', True)
    
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
        处理视频生成任务（混合方案）
        
        流程：
        1. 生成视频提示词（纯画面，不含文字）
        2. 调用可灵AI生成原始视频
        3. 后期处理：叠加文字 + TTS配音 + 背景音乐
        
        Args:
            input_data: {
                "title": "视频标题",
                "script": "视频脚本",
                "keywords": ["关键词列表"],
                "voice": "zh_female|zh_male|en_female|en_male" (可选)
            }
        
        Returns:
            {
                "video_prompt": "生成的提示词",
                "video_url": "最终视频URL",
                "raw_video_url": "原始AI视频URL",
                "status": "状态"
            }
        """
        title = input_data.get("title", "")
        script = input_data.get("script", "")
        keywords = input_data.get("keywords", [])
        voice = input_data.get("voice", "zh_female")
        
        self.log(f"开始处理视频任务: {title}")
        
        # 第一步：生成视频提示词
        self.log("步骤1: 生成视频提示词...")
        prompt_result = await self._generate_video_prompt(title, script, keywords)
        
        # 第二步：调用视频生成API
        if self.access_key and self.secret_key:
            self.log("步骤2: 调用可灵AI生成画面...")
            video_result = await self._call_video_api(prompt_result)
        else:
            video_result = {
                "status": "api_not_configured",
                "message": "可灵AI API未配置，请设置KELING_ACCESS_KEY和KELING_SECRET_KEY"
            }
        
        # 第三步：后期处理（如果原始视频生成成功）
        raw_video_url = video_result.get("video_url")
        if raw_video_url and self.enable_post_processing:
            self.log("步骤3: 进行后期处理（文字+配音+音乐）...")
            final_result = await self._post_process_video(
                video_url=raw_video_url,
                prompt_result=prompt_result,
                script=script,
                voice=voice
            )
            
            if final_result.get("status") == "success":
                video_result["raw_video_url"] = raw_video_url
                video_result["video_url"] = final_result.get("video_url")
                video_result["message"] = "视频生成并后期处理完成"
            else:
                # 后期处理失败，仍然返回原始视频
                self.log(f"后期处理失败: {final_result.get('message')}，返回原始视频", "warning")
                video_result["message"] = f"视频已生成，但后期处理失败: {final_result.get('message')}"
        
        self.log(f"视频任务处理完成: {title}")
        
        return {
            "video_prompt": prompt_result,
            **video_result
        }
    
    async def _post_process_video(
        self,
        video_url: str,
        prompt_result: Dict[str, Any],
        script: str,
        voice: str
    ) -> Dict[str, Any]:
        """
        后期处理视频：叠加文字、添加配音、合成背景音乐
        """
        try:
            from app.services.video_processor import VideoProcessor
            
            processor = VideoProcessor()
            
            # 获取字幕文字
            subtitle_texts = prompt_result.get("subtitle_texts", [])
            if not subtitle_texts:
                # 如果没有生成字幕，从脚本中提取
                subtitle_texts = self._extract_subtitles_from_script(script)
            
            # 获取音乐类型
            music_type = prompt_result.get("music_type", "bgm_corporate")
            
            # 生成TTS文本（使用脚本或简短版本）
            tts_text = self._prepare_tts_text(script, subtitle_texts)
            
            # 执行后期处理
            result = await processor.process_video(
                video_url=video_url,
                subtitle_texts=subtitle_texts,
                tts_text=tts_text,
                music_type=music_type,
                voice=voice
            )
            
            # 如果处理成功，需要上传处理后的视频
            if result.get("status") == "success":
                output_path = result.get("output_path")
                if output_path and os.path.exists(output_path):
                    # TODO: 上传到云存储并返回URL
                    # 暂时返回本地路径，后续集成云存储
                    result["video_url"] = f"file://{output_path}"
                    self.log(f"后期处理完成，输出: {output_path}")
            
            # 清理临时文件
            processor.cleanup()
            
            return result
            
        except ImportError as e:
            self.log(f"后期处理模块导入失败: {e}", "warning")
            return {"status": "error", "message": "后期处理模块未安装"}
        except Exception as e:
            self.log(f"后期处理异常: {e}", "error")
            return {"status": "error", "message": str(e)}
    
    def _extract_subtitles_from_script(self, script: str, max_lines: int = 5) -> List[str]:
        """从脚本中提取字幕文字"""
        if not script:
            return []
        
        # 按句号、感叹号、问号分割
        import re
        sentences = re.split(r'[。！？\n]', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 选择前几条作为字幕
        subtitles = []
        for s in sentences[:max_lines]:
            # 截断过长的句子
            if len(s) > 30:
                s = s[:27] + "..."
            subtitles.append(s)
        
        return subtitles
    
    def _prepare_tts_text(self, script: str, subtitle_texts: List[str]) -> str:
        """准备TTS配音文本"""
        # 优先使用脚本（如果不太长）
        if script and len(script) < 200:
            return script
        
        # 否则使用字幕文字组合
        if subtitle_texts:
            return "。".join(subtitle_texts) + "。"
        
        return ""
    
    async def _generate_video_prompt(
        self, 
        title: str, 
        script: str, 
        keywords: list
    ) -> Dict[str, Any]:
        """生成视频提示词（纯画面，不含文字）"""
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
                result = json.loads(response[json_start:json_end])
                self.log(f"提示词生成成功: {result.get('style', 'N/A')}")
                return result
        except json.JSONDecodeError as e:
            self.log(f"JSON解析失败: {e}", "warning")
        
        # 解析失败，返回默认结构（纯画面，无文字）
        return {
            "main_prompt": f"Cinematic shot of modern logistics warehouse, cargo trucks, professional commercial quality, smooth camera movement, no text or titles",
            "style": "商务专业",
            "music_type": "bgm_corporate",
            "camera_movement": "smooth pan",
            "subtitle_texts": [
                title,
                "专业物流服务",
                "高效准时可靠"
            ]
        }
    
    async def _call_video_api(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用可灵AI视频生成API（使用pro模式获得更高画质）"""
        if not self.access_key or not self.secret_key:
            return {"status": "api_not_configured", "message": "可灵AI API密钥未配置"}
        
        # 生成JWT token
        token = self._generate_jwt_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 获取主提示词，确保不含文字描述
        main_prompt = prompt_data.get("main_prompt", "")
        
        # 添加负向提示词，明确排除文字
        negative_prompt = "text, title, subtitle, watermark, logo, words, letters, characters, caption, blurry, low quality"
        
        # 可灵AI API参数 - 使用pro模式获得更高画质
        payload = {
            "model": "kling-v1-5",  # 使用v1.5模型，画质更好
            "prompt": main_prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "mode": "pro",  # 使用pro专业模式，画质更高
            "aspect_ratio": "16:9",
            "duration": "5"  # 5秒
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
