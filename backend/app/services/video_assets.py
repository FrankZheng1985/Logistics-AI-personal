"""
视频素材库管理服务
负责：素材库管理、模板管理、背景音乐管理
"""
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AsyncSessionLocal


class VideoAssetsService:
    """视频素材库服务"""
    
    # 素材分类
    ASSET_CATEGORIES = {
        "warehouse": "仓库场景",
        "port": "港口场景",
        "truck": "货车场景",
        "airplane": "飞机场景",
        "ship": "船舶场景",
        "logistics_hub": "物流枢纽",
        "customs": "海关清关",
        "delivery": "配送场景",
        "office": "办公场景",
        "international": "国际贸易"
    }
    
    # 背景音乐类型
    BGM_TYPES = {
        "corporate": {
            "name": "商务专业",
            "mood": "专业、稳重、可信赖",
            "suitable_for": ["公司介绍", "服务展示", "B2B营销"]
        },
        "upbeat": {
            "name": "活力动感",
            "mood": "积极、活力、年轻",
            "suitable_for": ["促销广告", "快递服务", "年轻客群"]
        },
        "warm": {
            "name": "温馨亲和",
            "mood": "温暖、亲切、信任",
            "suitable_for": ["客户见证", "服务承诺", "品牌故事"]
        },
        "tech": {
            "name": "科技感",
            "mood": "创新、高效、现代",
            "suitable_for": ["技术展示", "智能物流", "数字化"]
        },
        "epic": {
            "name": "史诗大气",
            "mood": "震撼、宏大、国际化",
            "suitable_for": ["全球网络", "大型项目", "实力展示"]
        },
        "international": {
            "name": "国际风格",
            "mood": "多元、开放、全球化",
            "suitable_for": ["跨境服务", "多国客户", "国际贸易"]
        }
    }
    
    # 视频模板类型
    TEMPLATE_TYPES = {
        "opening": "开场片段",
        "main": "主体内容",
        "transition": "转场效果",
        "ending": "结尾片段",
        "full": "完整模板"
    }
    
    async def get_assets_by_category(
        self, 
        category: str,
        asset_type: str = "video_clip",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """根据分类获取素材"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT id, name, file_url, thumbnail_url, duration_seconds, 
                           tags, metadata
                    FROM video_assets 
                    WHERE category = :category 
                    AND asset_type = :asset_type
                    AND is_active = TRUE
                    ORDER BY usage_count DESC
                    LIMIT :limit
                """),
                {"category": category, "asset_type": asset_type, "limit": limit}
            )
            
            rows = result.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "file_url": row[2],
                    "thumbnail_url": row[3],
                    "duration_seconds": row[4],
                    "tags": row[5],
                    "metadata": row[6]
                }
                for row in rows
            ]
    
    async def get_bgm_by_type(
        self, 
        music_type: str,
        min_duration: int = 0
    ) -> List[Dict[str, Any]]:
        """根据类型获取背景音乐"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT id, name, file_url, duration_seconds, bpm, 
                           is_loopable, suitable_for
                    FROM bgm_library 
                    WHERE music_type = :music_type 
                    AND duration_seconds >= :min_duration
                    AND is_active = TRUE
                    ORDER BY usage_count DESC
                """),
                {"music_type": music_type, "min_duration": min_duration}
            )
            
            rows = result.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "file_url": row[2],
                    "duration_seconds": row[3],
                    "bpm": row[4],
                    "is_loopable": row[5],
                    "suitable_for": row[6]
                }
                for row in rows
            ]
    
    async def get_template(
        self, 
        template_type: str = "full",
        category: str = "logistics"
    ) -> Optional[Dict[str, Any]]:
        """获取视频模板"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT id, name, description, structure, default_prompts,
                           duration_seconds, thumbnail_url
                    FROM video_templates 
                    WHERE template_type = :template_type 
                    AND category = :category
                    AND is_active = TRUE
                    ORDER BY usage_count DESC
                    LIMIT 1
                """),
                {"template_type": template_type, "category": category}
            )
            
            row = result.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "name": row[1],
                    "description": row[2],
                    "structure": row[3],
                    "default_prompts": row[4],
                    "duration_seconds": row[5],
                    "thumbnail_url": row[6]
                }
            return None
    
    async def get_tts_voice(
        self, 
        language_code: str,
        gender: str = "female"
    ) -> Optional[Dict[str, Any]]:
        """获取TTS语音配置"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT id, voice_id, voice_name, provider, sample_url
                    FROM tts_voices 
                    WHERE language_code = :language_code 
                    AND (gender = :gender OR gender IS NULL)
                    AND is_active = TRUE
                    ORDER BY is_default DESC
                    LIMIT 1
                """),
                {"language_code": language_code, "gender": gender}
            )
            
            row = result.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "voice_id": row[1],
                    "voice_name": row[2],
                    "provider": row[3],
                    "sample_url": row[4]
                }
            return None
    
    async def get_all_supported_languages(self) -> List[Dict[str, str]]:
        """获取所有支持的语言"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT DISTINCT language_code, language_name
                    FROM tts_voices 
                    WHERE is_active = TRUE
                    ORDER BY language_code
                """)
            )
            
            rows = result.fetchall()
            return [
                {"code": row[0], "name": row[1]}
                for row in rows
            ]
    
    async def increment_usage(
        self, 
        table: str, 
        asset_id: str
    ):
        """增加使用次数"""
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            await db.execute(
                text(f"UPDATE {table} SET usage_count = usage_count + 1 WHERE id = :id"),
                {"id": asset_id}
            )
            await db.commit()
    
    def get_default_prompts_for_scene(self, scene_type: str) -> List[str]:
        """获取场景的默认AI生成提示词"""
        prompts = {
            "warehouse": [
                "Cinematic shot of a modern logistics warehouse interior, neat organized shelves with packages, forklifts moving smoothly, workers in uniform, soft natural lighting, professional commercial quality",
                "Wide angle shot of automated warehouse system, conveyor belts moving packages, robotic arms sorting items, high-tech logistics facility, clean modern aesthetic"
            ],
            "port": [
                "Aerial view of busy container terminal at golden hour, massive gantry cranes loading containers onto cargo ships, professional documentary style",
                "Cinematic drone shot of container port, colorful shipping containers stacked high, ships docked at pier, bustling activity, warm sunset lighting"
            ],
            "truck": [
                "Dynamic tracking shot of fleet of delivery trucks on highway at sunset, smooth camera movement, professional commercial quality, vivid colors",
                "Cinematic shot of logistics trucks leaving distribution center at dawn, convoy formation, misty morning atmosphere"
            ],
            "airplane": [
                "Wide angle shot of cargo aircraft being loaded at airport, ground crew in action, packages on conveyor, cinematic lighting, professional quality",
                "Aerial view of cargo planes at international airport hub, busy tarmac activity, professional aviation footage style"
            ],
            "ship": [
                "Majestic shot of container ship sailing through ocean, aerial drone footage, vast blue sea, professional maritime documentary style",
                "Cinematic shot of cargo ship entering port, tugboats assisting, containers stacked high, golden hour lighting"
            ],
            "delivery": [
                "Heartwarming shot of delivery person handing package to happy customer, residential neighborhood, friendly interaction, warm lighting",
                "Dynamic shot of last-mile delivery in action, delivery van in urban setting, efficient service, modern city backdrop"
            ],
            "customs": [
                "Professional shot of customs clearance process, documents being processed, efficient workflow, modern facility, clean aesthetic",
                "Interior shot of customs inspection area, officials at work, organized procedures, professional environment"
            ],
            "international": [
                "Global montage of international trade, world map with trade routes, diverse locations, professional corporate style",
                "Cinematic shots of various international ports and airports, global connectivity, professional documentary quality"
            ]
        }
        return prompts.get(scene_type, prompts["warehouse"])


class VideoTemplateManager:
    """视频模板管理器"""
    
    # 默认长视频结构模板（2分钟）
    DEFAULT_2MIN_TEMPLATE = {
        "name": "标准物流宣传片模板",
        "duration_seconds": 120,
        "segments": [
            {
                "type": "opening",
                "duration": 10,
                "description": "开场震撼画面+品牌LOGO",
                "prompt_hint": "dramatic opening shot, logistics industry, modern infrastructure",
                "subtitle_position": "center",
                "transition_in": "fade_in",
                "transition_out": "cross_dissolve"
            },
            {
                "type": "pain_point",
                "duration": 15,
                "description": "客户痛点展示",
                "prompt_hint": "problem illustration, shipping challenges, business difficulties",
                "subtitle_position": "bottom",
                "transition_out": "wipe"
            },
            {
                "type": "solution",
                "duration": 25,
                "description": "解决方案展示",
                "prompt_hint": "professional logistics solutions, efficient operations, modern technology",
                "subtitle_position": "bottom",
                "transition_out": "cross_dissolve"
            },
            {
                "type": "service_1",
                "duration": 15,
                "description": "核心服务展示1",
                "prompt_hint": "specific logistics service, detailed operation, professional quality",
                "subtitle_position": "bottom",
                "transition_out": "slide"
            },
            {
                "type": "service_2",
                "duration": 15,
                "description": "核心服务展示2",
                "prompt_hint": "another logistics service, different aspect, professional quality",
                "subtitle_position": "bottom",
                "transition_out": "slide"
            },
            {
                "type": "global_network",
                "duration": 15,
                "description": "全球网络展示",
                "prompt_hint": "global logistics network, international operations, world map",
                "subtitle_position": "bottom",
                "transition_out": "cross_dissolve"
            },
            {
                "type": "testimonial",
                "duration": 10,
                "description": "客户见证/数据展示",
                "prompt_hint": "customer satisfaction, success metrics, trust building",
                "subtitle_position": "bottom",
                "transition_out": "fade"
            },
            {
                "type": "ending",
                "duration": 15,
                "description": "品牌展示+联系方式+行动号召",
                "prompt_hint": "professional ending, call to action, contact information display",
                "subtitle_position": "center",
                "transition_out": "fade_out"
            }
        ]
    }
    
    # 5分钟深度介绍模板
    DEFAULT_5MIN_TEMPLATE = {
        "name": "深度公司介绍模板",
        "duration_seconds": 300,
        "segments": [
            {"type": "opening", "duration": 15, "description": "品牌开场"},
            {"type": "company_intro", "duration": 30, "description": "公司简介"},
            {"type": "history", "duration": 25, "description": "发展历程"},
            {"type": "service_overview", "duration": 20, "description": "服务概览"},
            {"type": "sea_freight", "duration": 30, "description": "海运服务详解"},
            {"type": "air_freight", "duration": 25, "description": "空运服务详解"},
            {"type": "rail_freight", "duration": 20, "description": "铁路运输"},
            {"type": "customs", "duration": 20, "description": "清关服务"},
            {"type": "warehousing", "duration": 20, "description": "仓储服务"},
            {"type": "technology", "duration": 20, "description": "技术优势"},
            {"type": "global_network", "duration": 20, "description": "全球网络"},
            {"type": "case_study", "duration": 25, "description": "成功案例"},
            {"type": "team", "duration": 15, "description": "团队展示"},
            {"type": "ending", "duration": 15, "description": "联系方式+CTA"}
        ]
    }
    
    def get_template_for_duration(self, target_duration: int) -> Dict[str, Any]:
        """根据目标时长获取合适的模板"""
        if target_duration <= 120:
            return self.DEFAULT_2MIN_TEMPLATE
        else:
            return self.DEFAULT_5MIN_TEMPLATE
    
    def generate_segments_for_duration(
        self, 
        target_duration: int,
        video_type: str = "ad"
    ) -> List[Dict[str, Any]]:
        """为指定时长生成视频片段结构"""
        template = self.get_template_for_duration(target_duration)
        segments = template["segments"].copy()
        
        # 按比例调整每个片段的时长
        template_duration = template["duration_seconds"]
        scale_factor = target_duration / template_duration
        
        for segment in segments:
            segment["duration"] = int(segment["duration"] * scale_factor)
        
        # 确保总时长匹配
        total = sum(s["duration"] for s in segments)
        if total != target_duration:
            # 调整最后一个片段
            segments[-1]["duration"] += (target_duration - total)
        
        return segments


# 创建服务实例
video_assets_service = VideoAssetsService()
video_template_manager = VideoTemplateManager()
