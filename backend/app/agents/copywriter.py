"""
小文 - 文案策划 (天下第一笔升级版)
顶级文案大师，负责广告文案、视频脚本、营销内容、多语言创作
"""
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy import select
import json

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from app.models.company_config import CompanyConfig
from app.core.prompts.copywriter import (
    COPYWRITER_SYSTEM_PROMPT, 
    SCRIPT_WRITING_PROMPT,
    MOMENTS_COPY_PROMPT,
    LONG_VIDEO_SCRIPT_PROMPT,
    AD_COPY_PROMPT,
    EMAIL_SEQUENCE_PROMPT,
    MULTILINGUAL_TEMPLATES,
    PAIN_POINTS,
    TERMINOLOGY_SIMPLIFIED
)


class CopywriterAgent(BaseAgent):
    """小文 - 文案策划 (天下第一笔)
    
    核心能力：
    1. 大师级文案写作（AIDA/PAS/BAB/4P/QUEST模型）
    2. 1.5-5分钟专业视频脚本创作
    3. 多语言文案创作（12+语言）
    4. 病毒式传播内容设计
    5. 物流行业深度专业内容
    """
    
    name = "小文"
    agent_type = AgentType.COPYWRITER
    description = "文案策划(天下第一笔) - 负责广告文案、视频脚本、营销内容、多语言创作"
    
    # 支持的语言
    SUPPORTED_LANGUAGES = [
        "zh-CN", "en-US", "de-DE", "fr-FR", "es-ES", 
        "ja-JP", "ko-KR", "ar-SA", "pt-BR", "ru-RU",
        "it-IT", "nl-NL"
    ]
    
    # 文案模型
    COPYWRITING_MODELS = {
        "AIDA": "注意-兴趣-欲望-行动，适合广告和销售页面",
        "PAS": "问题-激化-解决方案，适合痛点营销",
        "BAB": "之前-之后-桥梁，适合效果展示",
        "4P": "承诺-画面-证明-推动，适合高转化文案",
        "QUEST": "资格-理解-教育-刺激-转化，适合教育型营销"
    }
    
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
                        lines.extend(routes_text[:5])
                
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
                "task_type": "script/moments/email/ad/long_script/translate",
                "title": "标题",
                "description": "描述",
                "duration": 120,  # 视频时长（秒）
                "language": "zh-CN",  # 目标语言
                "copywriting_model": "AIDA",  # 文案模型
                ...其他参数
            }
        """
        task_type = input_data.get("task_type", "script")
        
        if task_type == "script":
            return await self._write_script(input_data)
        elif task_type == "long_script":
            return await self._write_long_script(input_data)
        elif task_type == "moments":
            return await self._write_moments(input_data)
        elif task_type == "ad":
            return await self._write_ad_copy(input_data)
        elif task_type == "email":
            return await self._write_email_sequence(input_data)
        elif task_type == "translate":
            return await self._translate_copy(input_data)
        else:
            return await self._write_general(input_data)
    
    async def _write_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写标准视频脚本（30-90秒）"""
        title = input_data.get("title", "物流服务介绍")
        description = input_data.get("description", "")
        video_type = input_data.get("video_type", "ad")
        duration = input_data.get("duration", 60)
        target_audience = input_data.get("target_audience", "有物流需求的企业客户")
        key_selling_points = input_data.get("key_selling_points", "专业、快速、安全")
        
        company_context = await self._get_company_context()
        
        prompt = f"""请为视频撰写专业级脚本。

## 公司背景信息
{company_context if company_context else "暂未配置公司信息，请使用通用物流公司背景"}

## 视频要求
- 标题：{title}
- 描述：{description}
- 类型：{video_type}
- 时长：约{duration}秒
- 目标受众：{target_audience}
- 核心卖点：{key_selling_points}

## 创作要求
1. 运用AIDA模型构建叙事结构
2. 开场5秒必须用钩子抓住注意力
3. 融入公司名称和优势（如有配置）
4. 突出产品服务特点
5. 结尾有明确的行动号召
6. 提取8-10个关键词用于AI视频生成

## 输出格式
请按照以下格式输出完整脚本：

【标题】xxx
【时长】{duration}秒
【风格】xxx

===== 分镜脚本 =====
[00:00-00:05] 开场
【画面】xxx
【旁白】xxx
【字幕】xxx

[00:05-xx:xx] 主体
...

===== 关键词 =====
关键词1, 关键词2, ...
"""
        
        script = await self.think([{"role": "user", "content": prompt}])
        keywords = self._extract_keywords(script)
        
        self.log(f"完成脚本撰写: {title} ({duration}秒)")
        
        return {
            "script": script,
            "keywords": keywords,
            "title": title,
            "video_type": video_type,
            "duration": duration
        }
    
    async def _write_long_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写长视频脚本（1.5-5分钟）"""
        title = input_data.get("title", "公司宣传片")
        duration = input_data.get("duration", 180)  # 默认3分钟
        video_goal = input_data.get("video_goal", "展示公司实力，吸引潜在客户")
        target_audience = input_data.get("target_audience", "有物流需求的企业客户")
        special_requirements = input_data.get("special_requirements", "")
        
        company_context = await self._get_company_context()
        
        # 确定脚本结构
        if duration <= 120:
            structure = "短片结构（开场-问题-方案-CTA）"
        elif duration <= 180:
            structure = "标准结构（开场-问题-方案-服务展示-案例-CTA）"
        else:
            structure = "深度结构（开场-问题深化-方案详解-多服务展示-网络实力-案例见证-团队-CTA）"
        
        prompt = f"""请为以下物流公司创作{duration // 60}分{duration % 60}秒的专业宣传视频脚本：

## 公司信息
{company_context if company_context else "专业国际物流公司，提供海运、空运、铁路、清关等一站式服务"}

## 视频目标
{video_goal}

## 目标受众
{target_audience}

## 推荐结构
{structure}

## 特别要求
{special_requirements if special_requirements else "突出专业性和可信赖感"}

## 创作要求
1. 按照电影级标准设计分镜
2. 每个场景包含：画面描述（英文，用于AI生成）、旁白文案、字幕、音乐情绪
3. 设计情感曲线，在{duration // 2}秒左右达到情感高潮
4. 开场必须震撼，结尾必须有力
5. 提取15-20个关键词用于AI视频生成

## 输出格式
【标题】{title}
【时长】{duration}秒
【风格】电影级专业品质
【情感曲线】开场震撼 → 问题共鸣 → 希望建立 → 信任强化 → 行动激励

===== 完整分镜脚本 =====

[00:00-00:15] 第一幕：震撼开场
【画面】(英文，电影级场景描述)
【旁白】xxx
【字幕】xxx
【音乐】xxx
【情绪】xxx

...（继续完整输出所有分镜）

===== AI视频生成关键词 =====
xxx, xxx, xxx...

===== 行动号召 =====
xxx
"""
        
        script = await self.think([{"role": "user", "content": prompt}], temperature=0.8)
        keywords = self._extract_keywords(script)
        
        # 解析分镜结构
        segments = self._parse_script_segments(script)
        
        self.log(f"完成长视频脚本: {title} ({duration}秒, {len(segments)}个分镜)")
        
        return {
            "script": script,
            "keywords": keywords,
            "title": title,
            "duration": duration,
            "segments": segments,
            "segment_count": len(segments)
        }
    
    async def _write_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写朋友圈爆款文案"""
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
            "topic": topic,
            "purpose": purpose
        }
    
    async def _write_ad_copy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写高转化广告文案"""
        product = input_data.get("product", "国际物流服务")
        selling_points = input_data.get("selling_points", "快速、安全、实惠")
        target_audience = input_data.get("target_audience", "跨境电商卖家")
        platform = input_data.get("platform", "信息流广告")
        length = input_data.get("length", 200)
        copywriting_model = input_data.get("copywriting_model", "AIDA")
        
        company_context = await self._get_company_context()
        
        prompt = f"""请为以下物流服务创作高转化广告文案：

## 公司背景
{company_context if company_context else "专业国际物流公司"}

## 广告信息
- 产品/服务：{product}
- 核心卖点：{selling_points}
- 目标受众：{target_audience}
- 投放平台：{platform}
- 文案长度：{length}字以内

## 创作要求
1. 运用{copywriting_model}模型构建文案
2. 标题要有数字或疑问，制造好奇
3. 正文突出痛点和解决方案
4. 行动号召明确有力

请输出3个版本的广告文案，并说明每个版本的策略重点。

输出格式：
【版本1：xxx策略】
标题：xxx
正文：xxx
CTA：xxx
策略说明：xxx

【版本2】...
【版本3】...
"""
        
        copy = await self.think([{"role": "user", "content": prompt}])
        
        self.log(f"完成广告文案: {product}")
        
        return {
            "copy": copy,
            "product": product,
            "platform": platform,
            "model_used": copywriting_model
        }
    
    async def _write_email_sequence(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """撰写邮件营销序列"""
        trigger_event = input_data.get("trigger_event", "新客户询价")
        customer_segment = input_data.get("customer_segment", "询价未下单客户")
        marketing_goal = input_data.get("marketing_goal", "促成首单")
        sequence_length = input_data.get("sequence_length", 5)
        
        company_context = await self._get_company_context()
        
        prompt = f"""请设计一套{sequence_length}封邮件的营销序列：

## 公司信息
{company_context if company_context else "专业国际物流公司"}

## 场景信息
- 触发事件：{trigger_event}
- 目标客户：{customer_segment}
- 营销目标：{marketing_goal}
- 序列长度：{sequence_length}封

## 创作要求
每封邮件包含：
1. 发送时间（距触发事件的时间）
2. 邮件主题（高打开率标题）
3. 邮件正文（价值内容+CTA）
4. 预期目标

## 序列策略
- 第1封：及时响应，建立专业形象
- 第2封：提供价值，解决疑虑
- 第3封：案例分享，建立信任
- 第4封：限时优惠，制造紧迫
- 第5封：最后跟进，降低门槛

请输出完整的邮件序列。
"""
        
        sequence = await self.think([{"role": "user", "content": prompt}])
        
        self.log(f"完成邮件序列: {trigger_event} ({sequence_length}封)")
        
        return {
            "sequence": sequence,
            "trigger_event": trigger_event,
            "email_count": sequence_length
        }
    
    async def _translate_copy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """多语言文案翻译和本地化"""
        original_copy = input_data.get("copy", "")
        source_language = input_data.get("source_language", "zh-CN")
        target_language = input_data.get("target_language", "en-US")
        copy_type = input_data.get("copy_type", "ad")
        
        if target_language not in self.SUPPORTED_LANGUAGES:
            return {"error": f"不支持的目标语言: {target_language}"}
        
        prompt = f"""请将以下{source_language}文案翻译并本地化为{target_language}：

## 原文
{original_copy}

## 文案类型
{copy_type}

## 本地化要求
1. 不是逐字翻译，要符合目标语言的表达习惯
2. 保持原文的营销力度和情感张力
3. 调整文化相关的表达（如成语、俚语）
4. 保持品牌调性一致
5. CTA要符合目标市场习惯

## 输出格式
【翻译版本】
xxx

【本地化调整说明】
xxx

【文化适配建议】
xxx
"""
        
        translation = await self.think([{"role": "user", "content": prompt}])
        
        self.log(f"完成翻译: {source_language} → {target_language}")
        
        return {
            "translation": translation,
            "source_language": source_language,
            "target_language": target_language
        }
    
    async def _write_general(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """通用文案撰写"""
        requirement = input_data.get("requirement", "")
        company_context = await self._get_company_context()
        
        enhanced_prompt = f"""作为"天下第一笔"文案大师，请完成以下创作：

## 公司背景
{company_context if company_context else "专业国际物流公司"}

## 创作要求
{requirement}

## 创作标准
- 文字精炼有力
- 情感共鸣强烈
- 行动号召明确
- 品牌调性一致
"""
        
        content = await self.think([{"role": "user", "content": enhanced_prompt}])
        
        return {"content": content}
    
    def _extract_keywords(self, script: str) -> List[str]:
        """从脚本中提取关键词"""
        keywords = []
        
        if "关键词" in script:
            lines = script.split("\n")
            for i, line in enumerate(lines):
                if "关键词" in line:
                    keyword_line = line.split("：")[-1].split(":")[-1]
                    if not keyword_line.strip() and i + 1 < len(lines):
                        keyword_line = lines[i + 1]
                    keywords = [k.strip() for k in keyword_line.replace("，", ",").split(",") if k.strip()]
                    break
        
        if not keywords:
            keywords = ["物流", "货运", "快速", "安全", "专业", "全球", "可靠", "高效"]
        
        return keywords[:15]
    
    def _parse_script_segments(self, script: str) -> List[Dict[str, Any]]:
        """解析脚本中的分镜结构"""
        segments = []
        import re
        
        # 匹配时间码格式 [00:00-00:15]
        pattern = r'\[(\d{2}:\d{2})-(\d{2}:\d{2})\]\s*([^\n]+)'
        matches = re.findall(pattern, script)
        
        for start_time, end_time, title in matches:
            segments.append({
                "start_time": start_time,
                "end_time": end_time,
                "title": title.strip(),
                "duration": self._time_to_seconds(end_time) - self._time_to_seconds(start_time)
            })
        
        return segments
    
    def _time_to_seconds(self, time_str: str) -> int:
        """将时间字符串转换为秒数"""
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass
        return 0
    
    def get_pain_point_copy(self, pain_type: str) -> Dict[str, str]:
        """获取痛点文案素材"""
        return PAIN_POINTS.get(pain_type, PAIN_POINTS["time_sensitive"])
    
    def get_terminology_explanation(self, term: str) -> str:
        """获取术语的简化解释"""
        return TERMINOLOGY_SIMPLIFIED.get(term.upper(), term)


# 创建单例并注册
copywriter_agent = CopywriterAgent()
AgentRegistry.register(copywriter_agent)
