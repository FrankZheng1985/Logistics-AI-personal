"""
小影 - 视频创作员 (升级版)
支持电影级长视频制作、多语言配音、专业后期处理
视频时长：1.5分钟 - 5分钟
"""
from typing import Dict, Any, Optional, List
import json
import time
import os
import asyncio
import httpx
import jwt
from loguru import logger
from datetime import datetime

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings
from app.core.prompts.video_creator import (
    VIDEO_CREATOR_SYSTEM_PROMPT,
    VIDEO_PROMPT_GENERATION,
    MOVIE_STYLE_PROMPT,
    SEGMENT_PROMPT_TEMPLATE
)


class VideoCreatorAgent(BaseAgent):
    """小影 - 视频创作员（电影级升级版）
    
    核心能力：
    1. 生成1.5-5分钟的电影级视频
    2. 多片段AI生成 + 素材库补充
    3. 多语言配音支持（中/英/德/法/西/日/韩/阿等）
    4. 专业后期处理（字幕、配音、背景音乐、转场）
    """
    
    name = "小影"
    agent_type = AgentType.VIDEO_CREATOR
    description = "视频创作员 - 生成电影级物流广告视频（1.5-5分钟，多语言支持）"
    
    # 视频配置
    MIN_DURATION_SECONDS = 90   # 最短1.5分钟
    MAX_DURATION_SECONDS = 300  # 最长5分钟
    DEFAULT_DURATION_SECONDS = 120  # 默认2分钟
    
    # AI视频片段时长（可灵AI单次生成时长）
    AI_SEGMENT_DURATION = 5  # 5秒
    
    def __init__(self):
        super().__init__()
        self.access_key = settings.KELING_ACCESS_KEY
        self.secret_key = settings.KELING_SECRET_KEY
        self.keling_api_url = settings.KELING_API_URL
        self.enable_post_processing = getattr(settings, 'VIDEO_POST_PROCESSING', True)
    
    def _generate_jwt_token(self) -> str:
        """生成可灵AI的JWT认证token"""
        headers = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.access_key,
            "exp": int(time.time()) + 1800,
            "nbf": int(time.time()) - 5
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)
    
    def _build_system_prompt(self) -> str:
        return VIDEO_CREATOR_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频生成任务
        
        支持两种模式：
        1. 快速模式（mode="quick"）：生成5-10秒短视频
        2. 电影模式（mode="movie"）：生成1.5-5分钟长视频
        
        Args:
            input_data: {
                "title": "视频标题",
                "script": "视频脚本",
                "keywords": ["关键词列表"],
                "mode": "quick|movie",  # 默认movie
                "duration": 120,  # 目标时长（秒），默认120
                "language": "zh-CN",  # 语言代码
                "voice_gender": "female|male",  # 配音性别
                "bgm_type": "corporate|upbeat|warm|tech|epic",  # 背景音乐类型
                "video_type": "ad|intro|route|case_study"  # 视频类型
            }
        """
        mode = input_data.get("mode", "movie")
        title = input_data.get("title", "视频生成")
        
        # 开始任务会话（实时直播）
        await self.start_task_session(f"video_{mode}", f"视频生成: {title}")
        
        try:
            if mode == "quick":
                result = await self._process_quick_video(input_data)
            else:
                result = await self._process_movie_video(input_data)
            
            await self.end_task_session(f"完成视频生成: {title}")
            return result
        except Exception as e:
            await self.end_task_session(error_message=str(e))
            raise
    
    async def _process_quick_video(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """快速生成短视频（5-10秒）"""
        title = input_data.get("title", "")
        script = input_data.get("script", "")
        keywords = input_data.get("keywords", [])
        voice = input_data.get("voice", "zh_female")
        
        self.log(f"[快速模式] 开始生成短视频: {title}")
        
        # 生成提示词
        prompt_result = await self._generate_video_prompt(title, script, keywords)
        
        # 调用AI生成
        if self.access_key and self.secret_key:
            video_result = await self._call_video_api(prompt_result)
        else:
            video_result = {"status": "api_not_configured", "message": "可灵AI API未配置"}
        
        # 后期处理
        raw_video_url = video_result.get("video_url")
        if raw_video_url and self.enable_post_processing:
            final_result = await self._post_process_video(
                video_url=raw_video_url,
                prompt_result=prompt_result,
                script=script,
                voice=voice
            )
            if final_result.get("status") == "success":
                video_result["raw_video_url"] = raw_video_url
                video_result["video_url"] = final_result.get("video_url")
        
        return {"video_prompt": prompt_result, **video_result}
    
    async def _process_movie_video(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        电影模式：生成1.5-5分钟的专业级视频
        
        流程：
        1. 解析脚本，规划视频结构
        2. 为每个片段生成AI视频提示词
        3. 并行生成多个AI视频片段
        4. 下载并拼接所有片段
        5. 添加专业后期效果
        """
        title = input_data.get("title", "")
        script = input_data.get("script", "")
        keywords = input_data.get("keywords", [])
        duration = input_data.get("duration", self.DEFAULT_DURATION_SECONDS)
        language = input_data.get("language", "zh-CN")
        voice_gender = input_data.get("voice_gender", "female")
        bgm_type = input_data.get("bgm_type", "corporate")
        video_type = input_data.get("video_type", "ad")
        
        # 验证时长
        duration = max(self.MIN_DURATION_SECONDS, min(self.MAX_DURATION_SECONDS, duration))
        
        self.log(f"[电影模式] 开始生成{duration}秒视频: {title}")
        start_time = time.time()
        
        result = {
            "title": title,
            "mode": "movie",
            "target_duration": duration,
            "language": language,
            "status": "processing",
            "segments": [],
            "progress": 0
        }
        
        try:
            # 步骤1：规划视频结构
            self.log("步骤1: 规划视频结构...")
            video_structure = await self._plan_video_structure(
                title=title,
                script=script,
                keywords=keywords,
                duration=duration,
                video_type=video_type
            )
            result["structure"] = video_structure
            result["progress"] = 10
            
            # 步骤2：为每个片段生成提示词
            self.log(f"步骤2: 生成{len(video_structure['segments'])}个片段的提示词...")
            segment_prompts = await self._generate_segment_prompts(video_structure)
            result["progress"] = 20
            
            # 步骤3：并行生成AI视频片段（使用批次控制并发）
            self.log("步骤3: 生成AI视频片段...")
            generated_segments = await self._generate_video_segments_batch(segment_prompts)
            result["segments"] = generated_segments
            result["progress"] = 70
            
            # 步骤4：后期处理（拼接、配音、字幕、音乐）
            self.log("步骤4: 专业后期处理...")
            final_video = await self._compose_final_video(
                segments=generated_segments,
                structure=video_structure,
                language=language,
                voice_gender=voice_gender,
                bgm_type=bgm_type,
                script=script
            )
            result["progress"] = 100
            
            # 计算耗时
            elapsed = time.time() - start_time
            result["generation_time_seconds"] = int(elapsed)
            result["status"] = "success" if final_video.get("video_url") else "partial"
            result["video_url"] = final_video.get("video_url")
            result["message"] = f"视频生成完成，耗时{int(elapsed)}秒"
            
            self.log(f"[电影模式] 视频生成完成: {title}, 耗时{int(elapsed)}秒")
            
        except Exception as e:
            self.log(f"[电影模式] 视频生成失败: {e}", "error")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    async def _plan_video_structure(
        self,
        title: str,
        script: str,
        keywords: List[str],
        duration: int,
        video_type: str
    ) -> Dict[str, Any]:
        """规划视频结构，确定每个片段的内容"""
        from app.services.video_assets import video_template_manager
        
        # 获取模板
        segments = video_template_manager.generate_segments_for_duration(duration, video_type)
        
        # 使用AI优化结构
        planning_prompt = f"""请为以下视频规划详细的分镜结构：

视频标题：{title}
视频脚本：{script}
关键词：{', '.join(keywords)}
目标时长：{duration}秒
视频类型：{video_type}

基础结构：
{json.dumps(segments, ensure_ascii=False, indent=2)}

请为每个片段补充：
1. 具体的画面描述（用于AI视频生成）
2. 该片段的字幕文案
3. 镜头运动方式

输出JSON格式：
{{
    "segments": [
        {{
            "type": "片段类型",
            "duration": 时长秒数,
            "scene_description": "详细的画面描述（英文，用于AI生成）",
            "subtitle": "字幕文案（中文）",
            "camera_movement": "镜头运动",
            "mood": "情绪氛围"
        }}
    ],
    "overall_style": "整体风格",
    "color_tone": "色调"
}}
"""
        
        response = await self.think([{"role": "user", "content": planning_prompt}])
        
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                structure = json.loads(response[json_start:json_end])
                return structure
        except json.JSONDecodeError:
            pass
        
        # 默认结构
        return {
            "segments": segments,
            "overall_style": "professional_corporate",
            "color_tone": "warm_business"
        }
    
    async def _generate_segment_prompts(
        self, 
        video_structure: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """为每个视频片段生成AI提示词"""
        segments = video_structure.get("segments", [])
        style = video_structure.get("overall_style", "professional")
        
        prompts = []
        for i, segment in enumerate(segments):
            # 计算该片段需要生成多少个5秒的AI视频
            duration = segment.get("duration", 5)
            ai_clips_needed = max(1, duration // self.AI_SEGMENT_DURATION)
            
            scene = segment.get("scene_description", "")
            if not scene:
                scene = f"Professional logistics scene, {segment.get('type', 'generic')}"
            
            # 确保提示词是英文且专业
            base_prompt = f"""Cinematic {style} shot, {scene}, 
                professional commercial quality, 4K resolution, 
                smooth camera movement, no text or watermark, 
                film color grading, high production value"""
            
            prompts.append({
                "segment_index": i,
                "segment_type": segment.get("type", "main"),
                "duration": duration,
                "ai_clips_needed": ai_clips_needed,
                "main_prompt": base_prompt.replace("\n", " ").strip(),
                "subtitle": segment.get("subtitle", ""),
                "camera_movement": segment.get("camera_movement", "smooth pan"),
                "transition": segment.get("transition_out", "cross_dissolve")
            })
        
        return prompts
    
    async def _generate_video_segments_batch(
        self, 
        segment_prompts: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """批量生成视频片段，控制并发数量"""
        if not self.access_key or not self.secret_key:
            self.log("API未配置，使用占位符", "warning")
            return [{"status": "api_not_configured", **p} for p in segment_prompts]
        
        results = []
        
        # 分批处理
        for i in range(0, len(segment_prompts), max_concurrent):
            batch = segment_prompts[i:i+max_concurrent]
            self.log(f"生成批次 {i//max_concurrent + 1}/{(len(segment_prompts)-1)//max_concurrent + 1}")
            
            # 并行生成这批片段
            tasks = [self._generate_single_segment(p) for p in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        **batch[j],
                        "status": "failed",
                        "error": str(result)
                    })
                else:
                    results.append(result)
            
            # 批次间短暂延迟，避免API限流
            if i + max_concurrent < len(segment_prompts):
                await asyncio.sleep(2)
        
        return results
    
    async def _generate_single_segment(
        self, 
        prompt_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成单个视频片段"""
        token = self._generate_jwt_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "kling-v1-5",
            "prompt": prompt_data["main_prompt"],
            "negative_prompt": "text, title, subtitle, watermark, logo, blurry, low quality, amateur",
            "cfg_scale": 0.5,
            "mode": "pro",
            "aspect_ratio": "16:9",
            "duration": "5"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.keling_api_url}/v1/videos/text2video",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("data", {}).get("task_id")
                    
                    if task_id:
                        video_url = await self._poll_video_status(task_id, headers)
                        return {
                            **prompt_data,
                            "status": "success" if video_url else "processing",
                            "task_id": task_id,
                            "video_url": video_url
                        }
                
                return {
                    **prompt_data,
                    "status": "failed",
                    "error": f"API返回: {response.status_code}"
                }
                
        except Exception as e:
            return {
                **prompt_data,
                "status": "failed",
                "error": str(e)
            }
    
    async def _poll_video_status(
        self, 
        task_id: str, 
        headers: dict, 
        max_attempts: int = 60
    ) -> Optional[str]:
        """轮询视频生成状态"""
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
                        
                        if status == "succeed":
                            videos = data.get("task_result", {}).get("videos", [])
                            if videos:
                                return videos[0].get("url")
                        elif status == "failed":
                            return None
                        
                        await asyncio.sleep(5)
                except Exception:
                    break
        
        return None
    
    async def _compose_final_video(
        self,
        segments: List[Dict[str, Any]],
        structure: Dict[str, Any],
        language: str,
        voice_gender: str,
        bgm_type: str,
        script: str
    ) -> Dict[str, Any]:
        """合成最终视频"""
        try:
            from app.services.video_processor import VideoProcessor
            from app.services.video_assets import video_assets_service
            
            # 收集成功生成的片段
            successful_segments = [s for s in segments if s.get("video_url")]
            
            if not successful_segments:
                return {"status": "error", "message": "没有成功生成的视频片段"}
            
            # 获取TTS配置
            voice_config = await video_assets_service.get_tts_voice(language, voice_gender)
            voice_id = voice_config["voice_id"] if voice_config else None
            
            # 获取背景音乐
            bgm_list = await video_assets_service.get_bgm_by_type(bgm_type)
            bgm_url = bgm_list[0]["file_url"] if bgm_list else None
            
            # 提取字幕
            subtitles = [s.get("subtitle", "") for s in structure.get("segments", [])]
            
            processor = VideoProcessor()
            
            # 合成视频
            result = await processor.compose_long_video(
                segment_urls=[s["video_url"] for s in successful_segments],
                subtitles=subtitles,
                tts_text=script,
                voice_id=voice_id,
                bgm_url=bgm_url,
                transitions=[s.get("transition", "cross_dissolve") for s in segments]
            )
            
            processor.cleanup()
            return result
            
        except Exception as e:
            self.log(f"视频合成失败: {e}", "error")
            return {"status": "error", "message": str(e)}
    
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
        
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass
        
        return {
            "main_prompt": f"Cinematic shot of modern logistics warehouse, professional commercial quality",
            "style": "商务专业",
            "music_type": "bgm_corporate",
            "camera_movement": "smooth pan",
            "subtitle_texts": [title, "专业物流服务"]
        }
    
    async def _post_process_video(
        self,
        video_url: str,
        prompt_result: Dict[str, Any],
        script: str,
        voice: str
    ) -> Dict[str, Any]:
        """后期处理视频"""
        try:
            from app.services.video_processor import VideoProcessor
            
            processor = VideoProcessor()
            subtitle_texts = prompt_result.get("subtitle_texts", [])
            if not subtitle_texts:
                subtitle_texts = self._extract_subtitles_from_script(script)
            
            music_type = prompt_result.get("music_type", "bgm_corporate")
            tts_text = self._prepare_tts_text(script, subtitle_texts)
            
            result = await processor.process_video(
                video_url=video_url,
                subtitle_texts=subtitle_texts,
                tts_text=tts_text,
                music_type=music_type,
                voice=voice
            )
            
            processor.cleanup()
            return result
            
        except Exception as e:
            self.log(f"后期处理异常: {e}", "error")
            return {"status": "error", "message": str(e)}
    
    def _extract_subtitles_from_script(self, script: str, max_lines: int = 5) -> List[str]:
        """从脚本中提取字幕"""
        if not script:
            return []
        
        import re
        sentences = re.split(r'[。！？\n]', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        subtitles = []
        for s in sentences[:max_lines]:
            if len(s) > 30:
                s = s[:27] + "..."
            subtitles.append(s)
        
        return subtitles
    
    def _prepare_tts_text(self, script: str, subtitle_texts: List[str]) -> str:
        """准备TTS配音文本"""
        if script and len(script) < 500:
            return script
        if subtitle_texts:
            return "。".join(subtitle_texts) + "。"
        return ""
    
    async def get_supported_languages(self) -> List[Dict[str, str]]:
        """获取支持的语言列表"""
        from app.services.video_assets import video_assets_service
        return await video_assets_service.get_all_supported_languages()


# 创建单例并注册
video_creator_agent = VideoCreatorAgent()
AgentRegistry.register(video_creator_agent)
