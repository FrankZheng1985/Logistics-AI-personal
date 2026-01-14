"""
视频后期处理服务
负责：文字叠加、TTS配音、背景音乐合成
"""
import os
import asyncio
import tempfile
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

# 尝试导入视频处理库
try:
    from moviepy.editor import (
        VideoFileClip, AudioFileClip, CompositeVideoClip, 
        TextClip, CompositeAudioClip, concatenate_audioclips
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("moviepy未安装，视频后期处理功能将受限")

# 尝试导入edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts未安装，TTS配音功能将不可用")


class VideoProcessor:
    """视频后期处理器"""
    
    # 背景音乐文件路径（可配置）
    BGM_DIR = Path(__file__).parent.parent.parent / "assets" / "bgm"
    
    # 预设的背景音乐类型
    BGM_TYPES = {
        "bgm_corporate": "corporate.mp3",   # 商务企业风
        "bgm_upbeat": "upbeat.mp3",         # 活力动感
        "bgm_warm": "warm.mp3",             # 温馨亲和
        "bgm_tech": "tech.mp3",             # 科技感
    }
    
    # TTS语音选项
    TTS_VOICES = {
        "zh_male": "zh-CN-YunxiNeural",      # 中文男声
        "zh_female": "zh-CN-XiaoxiaoNeural", # 中文女声
        "en_male": "en-US-GuyNeural",        # 英文男声
        "en_female": "en-US-JennyNeural",    # 英文女声
    }
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="video_proc_")
        logger.info(f"视频处理临时目录: {self.temp_dir}")
    
    async def process_video(
        self,
        video_url: str,
        subtitle_texts: List[str],
        tts_text: Optional[str] = None,
        music_type: str = "bgm_corporate",
        voice: str = "zh_female",
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理视频：添加字幕、配音、背景音乐
        
        Args:
            video_url: 原始视频URL
            subtitle_texts: 要叠加的字幕文字列表
            tts_text: TTS配音文本（可选）
            music_type: 背景音乐类型
            voice: TTS语音类型
            output_path: 输出路径（可选）
        
        Returns:
            处理结果字典
        """
        if not MOVIEPY_AVAILABLE:
            return {
                "status": "error",
                "message": "moviepy未安装，无法进行视频后期处理"
            }
        
        try:
            # 1. 下载原始视频
            logger.info("正在下载原始视频...")
            video_path = await self._download_video(video_url)
            if not video_path:
                return {"status": "error", "message": "视频下载失败"}
            
            # 2. 生成TTS配音（如果需要）
            tts_path = None
            if tts_text and EDGE_TTS_AVAILABLE:
                logger.info("正在生成TTS配音...")
                tts_path = await self._generate_tts(tts_text, voice)
            
            # 3. 合成视频
            logger.info("正在合成视频...")
            output = output_path or os.path.join(self.temp_dir, "output.mp4")
            result = await self._compose_video(
                video_path=video_path,
                subtitle_texts=subtitle_texts,
                tts_path=tts_path,
                music_type=music_type,
                output_path=output
            )
            
            return result
            
        except Exception as e:
            logger.error(f"视频处理失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _download_video(self, url: str) -> Optional[str]:
        """下载视频文件"""
        try:
            output_path = os.path.join(self.temp_dir, "original.mp4")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=120.0)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"视频下载完成: {output_path}")
                    return output_path
                else:
                    logger.error(f"视频下载失败: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"视频下载异常: {e}")
            return None
    
    async def _generate_tts(self, text: str, voice: str = "zh_female") -> Optional[str]:
        """使用edge-tts生成配音"""
        if not EDGE_TTS_AVAILABLE:
            return None
        
        try:
            voice_name = self.TTS_VOICES.get(voice, self.TTS_VOICES["zh_female"])
            output_path = os.path.join(self.temp_dir, "tts.mp3")
            
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(output_path)
            
            logger.info(f"TTS生成完成: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"TTS生成失败: {e}")
            return None
    
    async def _compose_video(
        self,
        video_path: str,
        subtitle_texts: List[str],
        tts_path: Optional[str],
        music_type: str,
        output_path: str
    ) -> Dict[str, Any]:
        """合成最终视频"""
        try:
            # 在线程池中运行moviepy（因为它是同步的）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._compose_video_sync,
                video_path, subtitle_texts, tts_path, music_type, output_path
            )
            return result
        except Exception as e:
            logger.error(f"视频合成失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _compose_video_sync(
        self,
        video_path: str,
        subtitle_texts: List[str],
        tts_path: Optional[str],
        music_type: str,
        output_path: str
    ) -> Dict[str, Any]:
        """同步方式合成视频（在线程池中执行）"""
        video = None
        try:
            # 加载原始视频
            video = VideoFileClip(video_path)
            duration = video.duration
            
            # 创建字幕clips
            subtitle_clips = []
            if subtitle_texts:
                # 计算每条字幕的显示时间
                time_per_subtitle = duration / len(subtitle_texts)
                
                for i, text in enumerate(subtitle_texts):
                    # 创建文字clip - 使用系统中文字体
                    # Docker容器中安装了: WenQuanYi-Zen-Hei, Noto-Sans-CJK
                    font_name = self._get_chinese_font()
                    txt_clip = TextClip(
                        text,
                        fontsize=48,
                        color='white',
                        font=font_name,
                        stroke_color='black',
                        stroke_width=2,
                        size=(video.w - 100, None),  # 留边距
                        method='caption'
                    )
                    # 设置位置和时间
                    txt_clip = txt_clip.set_position(('center', video.h - 120))
                    txt_clip = txt_clip.set_start(i * time_per_subtitle)
                    txt_clip = txt_clip.set_duration(time_per_subtitle)
                    # 添加淡入淡出效果
                    txt_clip = txt_clip.crossfadein(0.3).crossfadeout(0.3)
                    subtitle_clips.append(txt_clip)
            
            # 合成视频和字幕
            if subtitle_clips:
                final_video = CompositeVideoClip([video] + subtitle_clips)
            else:
                final_video = video
            
            # 处理音频
            audio_clips = []
            
            # 添加TTS配音
            if tts_path and os.path.exists(tts_path):
                tts_audio = AudioFileClip(tts_path)
                # 如果TTS比视频长，截断；如果短，就用原长度
                if tts_audio.duration > duration:
                    tts_audio = tts_audio.subclip(0, duration)
                audio_clips.append(tts_audio)
            
            # 添加背景音乐
            bgm_path = self._get_bgm_path(music_type)
            if bgm_path and os.path.exists(bgm_path):
                bgm_audio = AudioFileClip(bgm_path)
                # 循环或截断背景音乐以匹配视频长度
                if bgm_audio.duration < duration:
                    # 循环背景音乐
                    loops_needed = int(duration / bgm_audio.duration) + 1
                    bgm_clips = [bgm_audio] * loops_needed
                    bgm_audio = concatenate_audioclips(bgm_clips).subclip(0, duration)
                else:
                    bgm_audio = bgm_audio.subclip(0, duration)
                
                # 降低背景音乐音量（如果有配音的话）
                if audio_clips:
                    bgm_audio = bgm_audio.volumex(0.3)  # 30%音量
                else:
                    bgm_audio = bgm_audio.volumex(0.7)  # 70%音量
                
                audio_clips.append(bgm_audio)
            
            # 合成音频
            if audio_clips:
                if len(audio_clips) > 1:
                    final_audio = CompositeAudioClip(audio_clips)
                else:
                    final_audio = audio_clips[0]
                final_video = final_video.set_audio(final_audio)
            
            # 导出视频
            logger.info(f"正在导出视频到: {output_path}")
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=24,
                preset='medium',
                threads=4,
                logger=None  # 禁用moviepy的进度日志
            )
            
            # 清理资源
            video.close()
            if subtitle_clips:
                for clip in subtitle_clips:
                    clip.close()
            
            logger.info(f"视频合成完成: {output_path}")
            return {
                "status": "success",
                "output_path": output_path,
                "duration": duration,
                "message": "视频后期处理完成"
            }
            
        except Exception as e:
            logger.error(f"视频合成异常: {e}")
            if video:
                video.close()
            return {"status": "error", "message": str(e)}
    
    def _get_bgm_path(self, music_type: str) -> Optional[str]:
        """获取背景音乐文件路径"""
        filename = self.BGM_TYPES.get(music_type)
        if filename:
            path = self.BGM_DIR / filename
            if path.exists():
                return str(path)
            else:
                logger.warning(f"背景音乐文件不存在: {path}")
        return None
    
    def _get_chinese_font(self) -> str:
        """获取系统中可用的中文字体"""
        # 按优先级排列的中文字体列表
        chinese_fonts = [
            # Linux (Docker容器中安装的字体)
            "WenQuanYi-Zen-Hei",
            "WenQuanYi-Micro-Hei", 
            "Noto-Sans-CJK-SC",
            "Noto-Sans-CJK",
            # macOS
            "PingFang-SC",
            "Heiti-SC",
            "STHeiti",
            # Windows
            "SimHei",
            "Microsoft-YaHei",
            # 通用后备
            "DejaVu-Sans",
            "Arial"
        ]
        
        # 尝试获取系统字体列表
        try:
            from moviepy.editor import TextClip
            available_fonts = TextClip.list('font')
            
            for font in chinese_fonts:
                # 检查完全匹配或部分匹配
                for available in available_fonts:
                    if font.lower().replace('-', '') in available.lower().replace('-', ''):
                        logger.info(f"使用字体: {available}")
                        return available
        except Exception as e:
            logger.warning(f"获取字体列表失败: {e}")
        
        # 默认返回第一个选项
        logger.warning(f"未找到中文字体，使用默认: {chinese_fonts[0]}")
        return chinese_fonts[0]
    
    def cleanup(self):
        """清理临时文件"""
        import shutil
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"已清理临时目录: {self.temp_dir}")
        except Exception as e:
            logger.error(f"清理临时目录失败: {e}")


# 创建处理器实例
video_processor = VideoProcessor()
