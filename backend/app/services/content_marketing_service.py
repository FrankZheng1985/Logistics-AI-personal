"""
内容营销服务
负责自动生成多平台营销内容
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from loguru import logger
from sqlalchemy import text
import json
import uuid

from app.models.database import async_session_maker
from app.agents.copywriter import copywriter_agent


class ContentMarketingService:
    """内容营销服务"""
    
    # 内容类型配置（对应星期几）
    CONTENT_SCHEDULE = {
        1: {"type": "knowledge", "name": "物流知识", "emoji": "📚"},
        2: {"type": "pricing", "name": "运价播报", "emoji": "💰"},
        3: {"type": "case", "name": "成功案例", "emoji": "✅"},
        4: {"type": "policy", "name": "政策解读", "emoji": "📢"},
        5: {"type": "faq", "name": "热门问答", "emoji": "❓"},
        6: {"type": "story", "name": "公司故事", "emoji": "🏢"},
        7: {"type": "weekly", "name": "周报总结", "emoji": "📊"},
    }
    
    # 支持的平台
    PLATFORMS = ["douyin", "xiaohongshu", "wechat_article", "wechat_moments"]
    
    # 平台名称映射
    PLATFORM_NAMES = {
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "wechat_article": "公众号文章",
        "wechat_moments": "朋友圈",
        "video_account": "视频号"
    }
    
    async def generate_daily_content(self, target_date: date = None) -> Dict[str, Any]:
        """
        生成指定日期的内容
        
        Args:
            target_date: 目标日期，默认为明天
        
        Returns:
            生成结果
        """
        if target_date is None:
            target_date = date.today() + timedelta(days=1)
        
        day_of_week = target_date.isoweekday()  # 1-7 对应周一到周日
        content_config = self.CONTENT_SCHEDULE.get(day_of_week, self.CONTENT_SCHEDULE[1])
        
        logger.info(f"📝 开始生成 {target_date} 的内容: {content_config['name']}")
        
        try:
            async with async_session_maker() as db:
                # 1. 检查是否已有该日期的内容计划
                existing = await db.execute(
                    text("""
                        SELECT id, status FROM content_calendar 
                        WHERE content_date = :date AND content_type = :type
                    """),
                    {"date": target_date, "type": content_config["type"]}
                )
                existing_row = existing.fetchone()
                
                # 如果已存在且状态是 generating 或 generated，则跳过
                if existing_row and existing_row[1] in ('generating', 'generated'):
                    logger.info(f"📝 {target_date} 的内容已存在(状态: {existing_row[1]})，跳过")
                    return {"status": "skipped", "message": "内容已存在或正在生成"}
                
                # 2. 获取数据源
                data_source = await self._get_data_source(content_config["type"], db)
                
                # 3. 创建或更新内容日历记录
                if existing_row:
                    calendar_id = existing_row[0]
                    await db.execute(
                        text("""
                            UPDATE content_calendar 
                            SET status = 'generating', data_source = :data_source
                            WHERE id = :id
                        """),
                        {"id": calendar_id, "data_source": json.dumps(data_source, ensure_ascii=False)}
                    )
                else:
                    calendar_id = str(uuid.uuid4())
                    await db.execute(
                        text("""
                            INSERT INTO content_calendar 
                            (id, content_date, day_of_week, content_type, status, data_source)
                            VALUES (:id, :date, :dow, :type, 'generating', :data_source)
                        """),
                        {
                            "id": calendar_id,
                            "date": target_date,
                            "dow": day_of_week,
                            "type": content_config["type"],
                            "data_source": json.dumps(data_source, ensure_ascii=False)
                        }
                    )
                
                await db.commit()
                
                # 4. 为每个平台生成内容
                generated_items = []
                for platform in self.PLATFORMS:
                    try:
                        content_item = await self._generate_content_for_platform(
                            content_type=content_config["type"],
                            platform=platform,
                            data_source=data_source,
                            db=db
                        )
                        
                        # 保存内容
                        item_id = str(uuid.uuid4())
                        await db.execute(
                            text("""
                                INSERT INTO content_items 
                                (id, calendar_id, platform, title, content, hashtags, 
                                 call_to_action, contact_info, video_script, status)
                                VALUES (:id, :calendar_id, :platform, :title, :content, :hashtags,
                                        :cta, :contact, :video_script, 'draft')
                            """),
                            {
                                "id": item_id,
                                "calendar_id": calendar_id,
                                "platform": platform,
                                "title": content_item.get("title"),
                                "content": content_item.get("content"),
                                "hashtags": content_item.get("hashtags", []),
                                "cta": content_item.get("call_to_action"),
                                "contact": content_item.get("contact_info"),
                                "video_script": content_item.get("video_script")
                            }
                        )
                        
                        generated_items.append({
                            "id": item_id,
                            "platform": platform,
                            "title": content_item.get("title"),
                            "status": "success"
                        })
                        
                        logger.info(f"✅ 生成 {self.PLATFORM_NAMES[platform]} 内容成功")
                        
                    except Exception as e:
                        logger.error(f"❌ 生成 {platform} 内容失败: {e}")
                        generated_items.append({
                            "platform": platform,
                            "status": "failed",
                            "error": str(e)
                        })
                
                # 5. 更新日历状态
                await db.execute(
                    text("""
                        UPDATE content_calendar 
                        SET status = 'generated', generated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": calendar_id}
                )
                
                await db.commit()
                
                logger.info(f"📝 {target_date} 内容生成完成！共 {len(generated_items)} 个平台")
                
                return {
                    "status": "success",
                    "date": str(target_date),
                    "content_type": content_config["type"],
                    "content_name": content_config["name"],
                    "calendar_id": calendar_id,
                    "items": generated_items
                }
                
        except Exception as e:
            logger.error(f"生成每日内容失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "failed", "error": str(e)}
    
    async def _get_data_source(self, content_type: str, db) -> Dict[str, Any]:
        """
        根据内容类型获取数据源
        """
        data = {
            "type": content_type,
            "generated_at": datetime.now().isoformat()
        }
        
        # 获取公司配置（包含聚焦市场等新字段）
        company_result = await db.execute(
            text("""
                SELECT company_name, company_intro, advantages, service_routes,
                       focus_markets, business_scope, brand_slogan, content_tone,
                       content_focus_keywords, forbidden_content, social_media
                FROM company_config LIMIT 1
            """)
        )
        company = company_result.fetchone()
        
        if company:
            data["company"] = {
                "name": company[0],  # company_name
                "intro": company[1],  # company_intro
                "advantages": company[2] or [],  # advantages
                "service_routes": company[3] or [],  # service_routes
                "focus_markets": company[4] or [],  # 聚焦市场
                "business_scope": company[5],  # 业务范围描述
                "brand_slogan": company[6],  # 品牌口号
                "content_tone": company[7] or 'professional',  # 内容风格
                "focus_keywords": company[8] or [],  # 内容关键词
                "forbidden_content": company[9] or [],  # 禁止内容
                "social_media": company[10] or {}  # 社交媒体账号
            }
        
        # 根据内容类型获取特定数据
        if content_type == "pricing":
            # 尝试从ERP缓存获取运价数据
            pricing_result = await db.execute(
                text("""
                    SELECT data_value FROM erp_data_cache 
                    WHERE data_type = 'pricing' 
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY updated_at DESC LIMIT 1
                """)
            )
            pricing = pricing_result.fetchone()
            if pricing:
                data["pricing"] = pricing[0]
            else:
                # 使用模拟数据（实际应该从ERP获取）
                data["pricing"] = await self._get_mock_pricing_data()
        
        elif content_type == "case":
            # 获取成功案例
            data["cases"] = await self._get_mock_case_data()
        
        elif content_type == "policy":
            # 获取政策公告
            data["policy"] = await self._get_mock_policy_data()
        
        elif content_type == "faq":
            # 从客户对话中提取高频问题
            data["faq"] = await self._extract_faq_from_conversations(db)
        
        elif content_type == "weekly":
            # 获取本周数据汇总
            data["weekly_stats"] = await self._get_weekly_stats(db)
        
        return data
    
    async def _generate_content_for_platform(
        self, 
        content_type: str, 
        platform: str, 
        data_source: Dict[str, Any],
        db
    ) -> Dict[str, Any]:
        """
        为指定平台生成内容
        优先使用AI生成，确保内容质量和真实性
        """
        # 构建提示词
        company_name = data_source.get("company", {}).get("name", "专业物流公司")
        
        platform_config = {
            "douyin": {
                "style": "口语化、有节奏感、适合短视频，开头要有钩子吸引注意力",
                "length": "100-200字",
                "extra": "需要生成完整的视频脚本，包含分镜画面描述、旁白、字幕"
            },
            "xiaohongshu": {
                "style": "亲切、种草风格、多用emoji、适合图文，有真实感和体验感",
                "length": "300-500字",
                "extra": "标题要有数字或疑问引发好奇，正文分段清晰，突出痛点和解决方案"
            },
            "wechat_article": {
                "style": "专业、深度、有干货，体现行业专家形象",
                "length": "800-1500字",
                "extra": "需要有小标题、列表、案例、总结，内容有深度有价值"
            },
            "wechat_moments": {
                "style": "简洁精炼、有信息量、适合快速阅读，像朋友分享",
                "length": "50-150字",
                "extra": "不需要标题，直接是文案，要有温度感和真实感"
            }
        }
        
        platform_info = platform_config.get(platform, platform_config["wechat_moments"])
        
        # 始终使用AI生成，确保内容质量和真实性
        # 模板容易导致变量未替换或内容千篇一律
        content = await self._generate_with_ai(
            content_type=content_type,
            platform=platform,
            platform_info=platform_info,
            data_source=data_source,
            company_name=company_name
        )
        
        return content
    
    async def _generate_from_template(
        self, 
        template, 
        data_source: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """从模板生成内容"""
        title_tpl = template[0] or ""
        content_tpl = template[1] or ""
        hashtags_tpl = template[2] or []
        cta_tpl = template[3] or ""
        
        # 替换变量
        variables = self._extract_variables(data_source)
        
        title = self._replace_variables(title_tpl, variables)
        content = self._replace_variables(content_tpl, variables)
        cta = self._replace_variables(cta_tpl, variables)
        
        return {
            "title": title if title else None,
            "content": content,
            "hashtags": hashtags_tpl,
            "call_to_action": cta,
            "contact_info": "添加微信获取详细报价"
        }
    
    async def _generate_with_ai(
        self,
        content_type: str,
        platform: str,
        platform_info: Dict[str, str],
        data_source: Dict[str, Any],
        company_name: str
    ) -> Dict[str, Any]:
        """使用AI生成高质量营销内容"""
        
        content_type_names = {
            "knowledge": "物流知识科普",
            "pricing": "运价播报",
            "case": "成功案例分享",
            "policy": "政策解读",
            "faq": "常见问题解答",
            "story": "公司故事",
            "weekly": "周报总结"
        }
        
        # 获取内容主题（基于内容类型生成具体话题）
        topic = await self._get_content_topic(content_type, data_source)
        
        # 构建数据摘要
        data_summary = self._build_data_summary(content_type, data_source)
        
        # 从数据源获取公司配置
        company_info = data_source.get("company", {})
        focus_markets = company_info.get("focus_markets", [])
        business_scope = company_info.get("business_scope", "")
        brand_slogan = company_info.get("brand_slogan", "")
        content_tone = company_info.get("content_tone", "professional")
        focus_keywords = company_info.get("focus_keywords", [])
        forbidden_content = company_info.get("forbidden_content", [])
        advantages = company_info.get("advantages", [])
        service_routes = company_info.get("service_routes", [])
        social_media = company_info.get("social_media", {})
        
        # 构建服务航线描述
        routes_text = ""
        if service_routes:
            routes_list = []
            for route in service_routes[:5]:
                from_loc = route.get("from_location", "中国")
                to_loc = route.get("to_location", "")
                transport = route.get("transport", "")
                time = route.get("time", "")
                if to_loc:
                    routes_list.append(f"{from_loc}→{to_loc}({transport}, {time})")
            routes_text = "；".join(routes_list)
        
        # 构建服务区域描述
        focus_region = "欧洲全境（德国、荷兰、英国、法国、意大利等）"
        if focus_markets:
            focus_region = "、".join(focus_markets) + "等地区"
        
        # 构建风格描述
        tone_map = {
            "professional": "专业可信，数据支撑，体现行业经验",
            "friendly": "亲切友好，贴近客户，像朋友聊天",
            "creative": "创意活泼，有趣吸睛，适合传播"
        }
        tone_desc = tone_map.get(content_tone, tone_map["professional"])
        
        # 构建禁止内容提醒
        forbidden_text = ""
        if forbidden_content:
            forbidden_text = f"\n⚠️ **禁止提及：{', '.join(forbidden_content)}**"
        
        # 构建社交媒体引流信息
        social_cta = "私信/评论咨询"
        if social_media:
            cta_parts = []
            if social_media.get("wechat"):
                cta_parts.append(f"微信「{social_media['wechat']}」")
            if social_media.get("wechat_official"):
                cta_parts.append(f"公众号「{social_media['wechat_official']}」")
            if cta_parts:
                social_cta = "或".join(cta_parts)
        
        # 针对不同内容类型的特殊指导
        type_specific_guide = self._get_type_specific_guide(content_type, data_source)
        
        # 针对不同平台的详细要求
        platform_specific_guide = self._get_platform_specific_guide(platform, content_type)
        
        prompt = f"""你是一位资深的物流行业内容营销专家，请为「{company_name}」创作一篇真实、专业、有吸引力的{content_type_names.get(content_type, '营销')}内容。

## 今日内容主题
{topic}

## 公司背景
- 公司名称：{company_name}
- 公司简介：{company_info.get('intro', '专注欧洲物流的专业服务商')}
- 核心优势：{', '.join(advantages) if advantages else '15年欧洲专线经验、德国/荷兰海外仓、全境DDU/DDP服务、一对一专属客服'}
- 服务航线：{routes_text if routes_text else '中国到欧洲全境海运/空运/铁路'}
- 服务区域：{focus_region}
{f'- 品牌口号：{brand_slogan}' if brand_slogan else ''}

## 发布平台：{self.PLATFORM_NAMES.get(platform, platform)}

## 平台内容要求
- 风格基调：{platform_info['style']}
- 内容长度：{platform_info['length']}
- 特殊要求：{platform_info['extra']}
- 整体调性：{tone_desc}
{f'- 关键词融入：{", ".join(focus_keywords)}' if focus_keywords else ''}{forbidden_text}

## 内容类型专项指导
{type_specific_guide}

## 平台专项指导
{platform_specific_guide}

## 可用的真实数据（请基于此创作）
{data_summary}

## 引流转化要求
1. 结尾必须有清晰的行动号召（CTA）
2. 强调"免费咨询"、"专属报价"、"一对一服务"等钩子
3. 引流方式：{social_cta}
4. 营造紧迫感或稀缺感（如"限时"、"名额有限"）

## 内容质量要求
1. 内容必须真实可信，不夸大不虚假
2. 用具体数据和案例支撑观点
3. 语言自然流畅，避免机械感
4. 针对目标客户（外贸商家、跨境卖家）的痛点
5. 体现专业性但不要过于晦涩

## 输出格式（严格按JSON格式）
{{
    "title": "吸引人的标题（朋友圈可为空字符串）",
    "content": "完整的正文内容",
    "hashtags": ["话题1", "话题2", "话题3", "话题4", "话题5"],
    "call_to_action": "有力的行动号召语",
    "video_script": "{self._get_video_script_requirement(platform)}"
}}
"""
        
        try:
            response = await copywriter_agent.think([{"role": "user", "content": prompt}])
            
            # 解析JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                
                # 验证内容不为空
                if result.get("content") and len(result["content"]) > 20:
                    logger.info(f"✅ AI成功生成 {platform} 内容: {result.get('title', '')[:30]}...")
                return result
                    
        except json.JSONDecodeError as e:
            logger.error(f"AI生成内容JSON解析失败: {e}")
        except Exception as e:
            logger.error(f"AI生成内容失败: {e}")
        
        # 如果AI生成失败，返回高质量默认内容
        return self._get_fallback_content(content_type, platform, company_name, data_source)
    
    async def _get_content_topic(self, content_type: str, data_source: Dict[str, Any]) -> str:
        """根据内容类型生成具体话题"""
        topics = {
            "knowledge": [
                "国际物流DDP与DDU的区别及选择建议",
                "欧洲清关避坑指南：这些文件一定要准备齐",
                "海运、空运、铁路怎么选？一张表帮你搞定",
                "欧洲VAT递延是什么？能帮你省多少钱？",
                "FBA头程物流全流程解析",
                "货物保险怎么买？理赔流程是什么？"
            ],
            "pricing": [
                "本周欧洲航线运价速报",
                "1月欧洲物流运价分析与发货建议",
                "德国/荷兰/英国最新运费对比"
            ],
            "case": [
                "客户案例：如何帮助电子产品卖家节省30%运费",
                "真实案例：处理清关延误的紧急应对方案",
                "成功案例：FBA头程+海外仓中转一站式服务"
            ],
            "policy": [
                "欧盟CBAM碳关税新规解读",
                "德国包装法最新要求",
                "英国脱欧后清关新变化"
            ],
            "faq": [
                "客户最常问的5个物流问题解答",
                "新手外贸必看：国际物流Q&A",
                "关于清关和税费，你想知道的都在这里"
            ],
            "story": [
                "我们为什么专注欧洲物流15年",
                "一个包裹从深圳到德国的全程记录",
                "客户好评背后的故事"
            ],
            "weekly": [
                "本周物流动态回顾与下周展望",
                "一周行业资讯精选"
            ]
        }
        
        import random
        type_topics = topics.get(content_type, ["物流行业干货分享"])
        return random.choice(type_topics)
    
    def _get_type_specific_guide(self, content_type: str, data_source: Dict[str, Any]) -> str:
        """获取内容类型专项指导"""
        guides = {
            "knowledge": """
- 选择1个具体知识点深入讲解
- 用"问题→解答→实操建议"的结构
- 加入真实案例或数据佐证
- 最后总结1-3个关键要点""",
            "pricing": """
- 列出主要航线的最新运价
- 对比海运/空运/铁路的价格和时效
- 分析近期市场趋势（涨/跌/稳）
- 给出发货时机建议""",
            "case": """
- 描述客户背景和痛点
- 说明提供的解决方案
- 展示具体成果（数据化）
- 引用客户评价（可适当虚构但要真实感）""",
            "policy": """
- 简述政策核心内容
- 分析对物流/外贸的影响
- 给出应对建议
- 说明我们能提供的帮助""",
            "faq": """
- 选择3-5个高频问题
- 用简洁专业的语言回答
- 每个回答要有实用价值
- 可以引出更多问题激发咨询""",
            "story": """
- 讲述真实感人的服务故事
- 体现团队专业和用心
- 展示公司文化和价值观
- 让读者产生情感共鸣""",
            "weekly": """
- 回顾本周行业动态
- 分享有价值的信息
- 展望下周市场趋势
- 感谢客户支持"""
        }
        return guides.get(content_type, "- 内容要有价值、有干货")
    
    def _get_platform_specific_guide(self, platform: str, content_type: str) -> str:
        """获取平台专项指导"""
        guides = {
            "douyin": """
📱 抖音短视频文案要求：
- 开头5秒必须有钩子：疑问句、数字、痛点
- 全文口语化，像在和朋友聊天
- 分点清晰，每点一句话
- 结尾要有强互动："评论区扣1"、"关注不迷路"
- 同时生成完整视频脚本：包含[时间]、【画面】、【旁白】、【字幕】""",
            "xiaohongshu": """
📕 小红书图文要求：
- 标题要有数字、疑问、emoji（如"3个技巧"、"你知道吗？"）
- 正文分段清晰，每段2-3句话
- 多用emoji增加阅读感（每段1-2个）
- 语气亲切像闺蜜分享
- 结尾要有引导收藏和关注的话术""",
            "wechat_article": """
📝 公众号文章要求：
- 有清晰的标题层级（##标题 ###小标题）
- 开头提出问题或痛点吸引阅读
- 正文有数据、案例、对比表格
- 可以用引用框突出重点
- 结尾有总结和明确的行动指引
- 内容专业但不晦涩，有深度有价值""",
            "wechat_moments": """
💬 朋友圈文案要求：
- 不需要标题，直接是精炼文案
- 3-5行为宜，太长没人看
- 要有温度感，像朋友分享
- 可以适当用emoji但不要过多
- 信息密度高，每句话都有价值
- 结尾简单引导私信咨询"""
        }
        return guides.get(platform, "- 内容要符合平台调性")
    
    def _get_video_script_requirement(self, platform: str) -> str:
        """获取视频脚本要求说明"""
        if platform == "douyin":
            return "必须生成完整视频脚本，格式：[时间段] 【画面】xxx 【旁白】xxx 【字幕】xxx"
        return "仅抖音需要，其他平台留空字符串"
    
    def _get_fallback_content(self, content_type: str, platform: str, company_name: str, data_source: Dict[str, Any]) -> Dict[str, Any]:
        """AI生成失败时的备用高质量内容"""
        company_info = data_source.get("company", {})
        advantages = company_info.get("advantages", ["15年欧洲专线经验", "德国/荷兰海外仓", "全境DDU/DDP服务"])
        
        fallback_contents = {
            "douyin": {
                "title": "发货欧洲，这3个坑千万别踩！",
                "content": f"""做外贸的老板注意了！发货欧洲最容易踩的3个坑：

1️⃣ 贪便宜选没资质的货代，货物被扣海关
2️⃣ 不了解清关政策，DDP变DDU还得加钱
3️⃣ 没有海外仓支持，退换货只能销毁

{company_name}，专注欧洲物流15年✅
{chr(10).join(['✔️ ' + adv for adv in advantages[:3]])}

需要欧洲物流报价？评论区扣1，私信发你！""",
                "hashtags": ["欧洲物流", "跨境电商", "外贸干货", "德国专线", "物流避坑"],
                "call_to_action": "评论区扣1，私信发你专属报价！",
                "video_script": """[00:00-00:05] 开场
【画面】快递包裹被海关扣押的场景
【旁白】发货欧洲，这3个坑踩了血亏！
【字幕】欧洲物流避坑指南

[00:05-00:20] 坑1
【画面】价格对比图+海关查验场景
【旁白】第一坑：贪便宜选没资质的货代，结果货物被扣海关，损失惨重
【字幕】坑1：贪便宜=高风险

[00:20-00:35] 坑2
【画面】DDP和DDU对比动画
【旁白】第二坑：不了解清关政策，说好的DDP，到了变DDU，还得额外加钱
【字幕】坑2：搞不懂DDP/DDU

[00:35-00:50] 坑3
【画面】货物销毁场景
【旁白】第三坑：没有海外仓支持，客户退货只能销毁，白白损失
【字幕】坑3：无海外仓支撑

[00:50-01:00] 解决方案+CTA
【画面】公司logo+服务优势展示
【旁白】15年欧洲专线，德国荷兰自有仓，专业清关，让你发货无忧！评论扣1，私信发报价！
【字幕】{company_name} | 欧洲物流专家"""
            },
            "xiaohongshu": {
                "title": "发货欧洲踩过的坑，希望你别再踩了😭",
                "content": f"""做跨境3年，在物流上吃过的亏太多了，今天分享给姐妹们避避雷💡

❌ 坑1：贪便宜选小货代
之前为了省200块选了个没听过的货代，结果货在海关躺了2周，客户直接取消订单，亏大了😱

❌ 坑2：DDP≠真包税
有些所谓"DDP服务"其实是半包，尾程关税还得自己掏，套路满满⚠️

❌ 坑3：没有海外仓
退货只能销毁或者高价退回国，一单亏几千块💸

后来找到了{company_name}，真的靠谱👇
✅ {advantages[0] if len(advantages) > 0 else '15年欧洲专线经验'}
✅ {advantages[1] if len(advantages) > 1 else '德国/荷兰自有海外仓'}
✅ {advantages[2] if len(advantages) > 2 else '全境DDU/DDP服务'}
✅ 一对一客服，有问题秒回

现在发货欧洲再也不焦虑了✨

📩 需要报价的姐妹私信我，备注"小红书"优先回复～""",
                "hashtags": ["跨境物流", "欧洲专线", "外贸干货", "物流避坑", "亚马逊FBA"],
                "call_to_action": "私信我领取专属报价方案，备注"小红书"优先回复～",
                "video_script": ""
            },
            "wechat_article": {
                "title": f"【干货】欧洲物流避坑指南：选对合作伙伴省心省钱",
                "content": f"""在跨境电商蓬勃发展的今天，欧洲市场以其高消费力和稳定需求成为众多卖家的必争之地。然而，物流环节的复杂性常常让人头疼——清关延误、税费不透明、退货处理困难等问题层出不穷。

作为深耕欧洲物流15年的{company_name}，我们见证了太多卖家在物流选择上的困惑与教训。今天，我们将这些经验总结成文，希望能帮助您少走弯路。

## 一、选择物流服务商的3大核心考量

### 1. 资质与经验
专业的物流服务商应具备完善的清关资质和丰富的欧洲市场经验。{company_name}拥有{advantages[0] if len(advantages) > 0 else '15年欧洲专线运营经验'}，熟悉德国、荷兰、英国、法国等国的海关政策和操作流程。

### 2. 服务模式透明度
DDP（完税后交货）和DDU（未完税交货）是两种常见的贸易术语，务必在合作前明确服务范围。我们提供的{advantages[2] if len(advantages) > 2 else '全境DDU/DDP服务'}，报价即包含所有费用，无隐形收费。

### 3. 海外仓储能力
{advantages[1] if len(advantages) > 1 else '德国/荷兰自有海外仓'}能有效解决退换货难题，同时支持本地化分拨，提升配送时效。

## 二、我们的服务优势

{chr(10).join(['- ' + adv for adv in advantages])}
- 一对一专属客服，全程可视化追踪

## 三、合作流程

1. **需求沟通**：了解您的货物类型、目的地、时效要求
2. **方案定制**：提供海运/空运/铁路多种方案对比
3. **报价确认**：透明报价，无隐形费用
4. **执行交付**：全程跟踪，及时反馈

---

**如果您正在寻找可靠的欧洲物流合作伙伴，欢迎联系我们获取专属报价方案。**

首次合作客户可享受运费优惠，名额有限，先到先得。""",
                "hashtags": ["国际物流", "欧洲专线", "跨境电商物流", "DDP清关", "海外仓"],
                "call_to_action": "点击阅读原文或添加客服微信，获取您的专属物流解决方案！",
                "video_script": ""
            },
            "wechat_moments": {
                "title": "",
                "content": f"""📦 发货欧洲的老板看过来

{company_name}，专注欧洲物流15年
✅ {advantages[0] if len(advantages) > 0 else '德国/荷兰/英国/法国全境覆盖'}
✅ {advantages[1] if len(advantages) > 1 else 'DDU/DDP双模式，报价透明'}
✅ {advantages[2] if len(advantages) > 2 else '海外仓支持，退换无忧'}

最近欧洲航线舱位紧张，建议提前预订
需要报价的老板私信我 👇""",
                "hashtags": ["欧洲物流", "跨境电商"],
                "call_to_action": "需要报价私信我",
                "video_script": ""
            }
        }
        
        return fallback_contents.get(platform, fallback_contents["wechat_moments"])
    
    def _extract_variables(self, data_source: Dict[str, Any]) -> Dict[str, str]:
        """从数据源提取变量"""
        variables = {
            "month": str(datetime.now().month),
            "year": str(datetime.now().year),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        
        # 公司信息
        if "company" in data_source:
            variables["company_name"] = data_source["company"].get("name", "物流公司")
        
        # 运价信息
        if "pricing" in data_source:
            pricing = data_source["pricing"]
            if isinstance(pricing, dict):
                sea = pricing.get("sea_freight", [])
                if sea and len(sea) > 0:
                    variables["destination"] = sea[0].get("route", "欧洲").split("→")[-1].strip()
                    variables["price"] = str(sea[0].get("price", 2500))
                    variables["transit_time"] = sea[0].get("transit_time", "25-30天")
        
        return variables
    
    def _replace_variables(self, template: str, variables: Dict[str, str]) -> str:
        """替换模板中的变量"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    def _build_data_summary(self, content_type: str, data_source: Dict[str, Any]) -> str:
        """构建详细的数据摘要供AI使用"""
        lines = []
        
        # 公司基本信息
        if "company" in data_source:
            company = data_source["company"]
            if company.get("name"):
                lines.append(f"### 公司信息")
                lines.append(f"- 公司名称：{company['name']}")
                if company.get("intro"):
                    lines.append(f"- 公司简介：{company['intro']}")
                if company.get("advantages"):
                    lines.append(f"- 核心优势：{', '.join(company['advantages'])}")
        
        # 根据内容类型添加专项数据
        if content_type == "pricing" and "pricing" in data_source:
            pricing = data_source["pricing"]
            if isinstance(pricing, dict):
                lines.append("\n### 最新运价数据（可直接引用）")
                
                # 海运运价
                sea_freight = pricing.get("sea_freight", [])
                if sea_freight:
                    lines.append("\n**海运整柜运价：**")
                    for item in sea_freight[:5]:
                        route = item.get('route', '')
                        price = item.get('price', 0)
                        container = item.get('container_type', '40GP')
                        time = item.get('transit_time', '')
                        remarks = item.get('remarks', '')
                        lines.append(f"- {route}: ${price}/{container}, 时效{time}")
                        if remarks:
                            lines.append(f"  备注：{remarks}")
                
                # 空运运价
                air_freight = pricing.get("air_freight", [])
                if air_freight:
                    lines.append("\n**空运运价：**")
                    for item in air_freight[:3]:
                        route = item.get('route', '')
                        price = item.get('price_per_kg', 0)
                        time = item.get('transit_time', '')
                        lines.append(f"- {route}: ¥{price}/kg, 时效{time}")
                
                # 铁路运价
                rail_freight = pricing.get("rail_freight", [])
                if rail_freight:
                    lines.append("\n**中欧班列运价：**")
                    for item in rail_freight[:2]:
                        route = item.get('route', '')
                        price = item.get('price', 0)
                        time = item.get('transit_time', '')
                        lines.append(f"- {route}: ${price}/柜, 时效{time}")
                
                # 市场动态
                if pricing.get("highlight"):
                    lines.append(f"\n**市场动态：**{pricing['highlight']}")
                if pricing.get("service_area"):
                    lines.append(f"**服务区域：**{pricing['service_area']}")
        
        elif content_type == "case" and "cases" in data_source:
            cases = data_source["cases"]
            if cases:
                lines.append("\n### 真实客户案例（可引用或改编）")
                for i, case in enumerate(cases[:3], 1):
                    lines.append(f"\n**案例{i}：**")
                    lines.append(f"- 客户类型：{case.get('customer_type', '跨境卖家')}")
                    lines.append(f"- 货物类型：{case.get('cargo_type', '一般贸易货物')}")
                    lines.append(f"- 运输路线：{case.get('route', '中国到欧洲')}")
                    lines.append(f"- 服务方案：{case.get('service', '海运+清关+派送')}")
                    lines.append(f"- 亮点成果：{case.get('highlight', '准时送达')}")
                    if case.get('feedback'):
                        lines.append(f"- 客户反馈："{case['feedback']}"")
        
        elif content_type == "policy" and "policy" in data_source:
            policy = data_source["policy"]
            if policy:
                lines.append("\n### 政策信息（用于解读）")
                lines.append(f"- 政策主题：{policy.get('title', '')}")
                lines.append(f"- 政策摘要：{policy.get('summary', '')}")
                if policy.get("key_points"):
                    lines.append("- 关键要点：")
                    for point in policy.get("key_points", [])[:5]:
                        lines.append(f"  • {point}")
                if policy.get("impact"):
                    lines.append(f"- 影响分析：{policy['impact']}")
                if policy.get("recommendation"):
                    lines.append(f"- 应对建议：{policy['recommendation']}")
        
        elif content_type == "faq" and "faq" in data_source:
            faq = data_source["faq"]
            if faq:
                lines.append("\n### 客户高频问题（用于解答）")
                for i, q in enumerate(faq[:6], 1):
                    lines.append(f"{i}. {q}")
        
        elif content_type == "weekly" and "weekly_stats" in data_source:
            stats = data_source["weekly_stats"]
            if stats:
                lines.append("\n### 本周业务数据")
                lines.append(f"- 新增客户：{stats.get('new_customers', 0)}家")
                lines.append(f"- 新增线索：{stats.get('new_leads', 0)}条")
                if stats.get("highlight"):
                    lines.append(f"- 周报亮点：{stats['highlight']}")
        
        elif content_type == "story":
            lines.append("\n### 公司故事素材")
            lines.append("- 创业历程：15年前从欧洲专线起步，专注做好一件事")
            lines.append("- 团队理念：客户的货就是我们的责任")
            lines.append("- 服务承诺：全程可视、问题必达、售后无忧")
            lines.append("- 里程碑：累计服务客户3000+家，0重大清关事故")
        
        elif content_type == "knowledge":
            lines.append("\n### 物流知识要点（供参考）")
            lines.append("- DDP（完税后交货）：卖方承担全部费用和风险，买方只需收货")
            lines.append("- DDU（未完税交货）：卖方送货到目的地，但买方负责清关和税费")
            lines.append("- 欧洲主要港口：汉堡(德国)、鹿特丹(荷兰)、费利克斯托(英国)、勒阿弗尔(法国)")
            lines.append("- 时效参考：海运28-35天，空运5-7天，中欧班列18-22天")
            lines.append("- 清关要点：发票、装箱单、提单、原产地证、CE认证等")
        
        # 添加通用的营销钩子建议
        lines.append("\n### 营销钩子建议")
        lines.append("- 免费咨询、专属报价、一对一服务")
        lines.append("- 15年经验、3000+客户、0重大事故")
        lines.append("- 限时优惠、名额有限、先到先得")
        
        return "\n".join(lines) if lines else "请基于物流行业专业知识生成内容，突出欧洲专线服务优势"
    
    # ==================== 模拟数据（等ERP对接后替换） ====================
    
    async def _get_mock_pricing_data(self) -> Dict[str, Any]:
        """模拟运价数据 - 仅欧洲航线"""
        return {
            "sea_freight": [
                {
                    "route": "深圳 → 汉堡(德国)",
                    "container_type": "40GP",
                    "price": 2500,
                    "currency": "USD",
                    "transit_time": "28-32天",
                    "remarks": "本周舱位充足，德国全境派送"
                },
                {
                    "route": "宁波 → 鹿特丹(荷兰)",
                    "container_type": "40HQ",
                    "price": 2800,
                    "currency": "USD",
                    "transit_time": "25-30天",
                    "remarks": "荷兰仓储+欧洲全境分拨"
                },
                {
                    "route": "上海 → 费利克斯托(英国)",
                    "container_type": "40GP",
                    "price": 2600,
                    "currency": "USD",
                    "transit_time": "30-35天",
                    "remarks": "含清关，DDP到门"
                },
                {
                    "route": "深圳 → 勒阿弗尔(法国)",
                    "container_type": "40GP",
                    "price": 2700,
                    "currency": "USD",
                    "transit_time": "30-35天",
                    "remarks": "法国全境派送"
                },
                {
                    "route": "宁波 → 热那亚(意大利)",
                    "container_type": "40GP",
                    "price": 2900,
                    "currency": "USD",
                    "transit_time": "32-38天",
                    "remarks": "意大利清关一条龙"
                }
            ],
            "air_freight": [
                {
                    "route": "深圳 → 法兰克福(德国)",
                    "price_per_kg": 28,
                    "currency": "CNY",
                    "transit_time": "5-7天",
                    "min_weight": 45,
                    "remarks": "紧急件首选"
                },
                {
                    "route": "上海 → 阿姆斯特丹(荷兰)",
                    "price_per_kg": 30,
                    "currency": "CNY",
                    "transit_time": "4-6天",
                    "min_weight": 45
                }
            ],
            "rail_freight": [
                {
                    "route": "义乌 → 杜伊斯堡(德国)",
                    "container_type": "40GP",
                    "price": 8500,
                    "currency": "USD",
                    "transit_time": "18-22天",
                    "remarks": "中欧班列，性价比之选"
                },
                {
                    "route": "成都 → 波兰华沙",
                    "container_type": "40GP",
                    "price": 7800,
                    "currency": "USD",
                    "transit_time": "15-18天"
                }
            ],
            "highlight": "本周欧洲航线运价平稳，德国/荷兰线舱位充足，建议提前预订",
            "service_area": "专注欧洲：德国、荷兰、英国、法国、意大利、西班牙、波兰等"
        }
    
    async def _get_mock_case_data(self) -> List[Dict[str, Any]]:
        """模拟案例数据 - 仅欧洲客户"""
        return [
            {
                "customer_type": "跨境电商卖家",
                "cargo_type": "电子产品",
                "route": "深圳 → 德国FBA仓",
                "service": "海运+德国清关+亚马逊仓派送",
                "highlight": "28天到仓，含清关和VAT递延",
                "feedback": "德国线做了3年了，每次都很稳"
            },
            {
                "customer_type": "外贸工厂",
                "cargo_type": "机械配件",
                "route": "宁波 → 英国伯明翰",
                "service": "整柜海运DDP到门",
                "highlight": "帮客户节省了30%运费，含英国清关",
                "feedback": "英国脱欧后清关麻烦，他们搞定了"
            },
            {
                "customer_type": "家具出口商",
                "cargo_type": "实木家具",
                "route": "佛山 → 荷兰鹿特丹",
                "service": "海运+荷兰仓储+欧洲分拨",
                "highlight": "荷兰仓中转，覆盖欧洲5国客户",
                "feedback": "仓储费用比其他低，服务也专业"
            },
            {
                "customer_type": "服装品牌商",
                "cargo_type": "服装鞋帽",
                "route": "义乌 → 波兰华沙",
                "service": "中欧班列+波兰清关",
                "highlight": "铁路比海运快10天，比空运省一半",
                "feedback": "东欧市场就靠这条线支撑"
            }
        ]
    
    async def _get_mock_policy_data(self) -> Dict[str, Any]:
        """模拟政策数据 - 欧洲政策"""
        return {
            "title": "欧盟CBAM碳关税新规解读",
            "summary": "自2026年起，进口欧盟的钢铁、铝等产品需申报碳排放",
            "key_points": [
                "适用产品范围：钢铁、铝、水泥、化肥、电力",
                "需要提供碳排放数据证明",
                "过渡期报告义务已开始",
                "2026年正式征收碳关税"
            ],
            "impact": "对电子产品影响较小，钢铁铝材出口欧洲需重点关注",
            "recommendation": "建议与供应商确认碳排放数据，我们可协助准备申报材料",
            "related_policies": [
                "德国包装法VerpackG注册要求",
                "欧盟WEEE电子废弃物回收法规",
                "英国脱欧后清关新规",
                "欧盟CE认证更新要求"
            ],
            "service_area": "欧洲"
        }
    
    async def _extract_faq_from_conversations(self, db) -> List[str]:
        """从客户对话中提取高频问题"""
        # 简单实现：从对话中提取包含问号的内容
        try:
            result = await db.execute(
                text("""
                    SELECT content FROM conversations 
                    WHERE message_type = 'inbound' 
                    AND content LIKE '%？%'
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
            )
            rows = result.fetchall()
            
            questions = []
            for row in rows:
                content = row[0]
                if '？' in content or '?' in content:
                    # 简单清理
                    q = content.strip()
                    if len(q) > 10 and len(q) < 100:
                        questions.append(q)
            
            return questions[:5] if questions else [
                "海运到德国要多久？",
                "欧洲清关需要什么资料？",
                "德国FBA仓派送怎么收费？",
                "中欧班列和海运怎么选？",
                "英国脱欧后清关有什么变化？"
            ]
        except:
            return [
                "海运到德国要多久？",
                "欧洲DDU和DDP有什么区别？",
                "荷兰仓可以分拨到哪些国家？"
            ]
    
    async def _get_weekly_stats(self, db) -> Dict[str, Any]:
        """获取本周统计数据"""
        try:
            # 本周新客户
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM customers 
                    WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
                """)
            )
            new_customers = result.scalar() or 0
            
            # 本周线索
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM leads 
                    WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)
                """)
            )
            new_leads = result.scalar() or 0
            
            return {
                "new_customers": new_customers,
                "new_leads": new_leads,
                "highlight": "本周业务稳步增长"
            }
        except:
            return {
                "new_customers": 0,
                "new_leads": 0,
                "highlight": "感谢大家的支持"
            }
    
    # ==================== 查询方法 ====================
    
    async def get_content_calendar(
        self, 
        start_date: date = None, 
        end_date: date = None,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """获取内容日历"""
        if start_date is None:
            start_date = date.today() - timedelta(days=7)
        if end_date is None:
            end_date = date.today() + timedelta(days=7)
        
        try:
            async with async_session_maker() as db:
                query = """
                    SELECT c.id, c.content_date, c.day_of_week, c.content_type, 
                           c.status, c.topic, c.generated_at, c.published_at,
                           COUNT(i.id) as item_count
                    FROM content_calendar c
                    LEFT JOIN content_items i ON c.id = i.calendar_id
                    WHERE c.content_date BETWEEN :start AND :end
                """
                params = {"start": start_date, "end": end_date}
                
                if status:
                    query += " AND c.status = :status"
                    params["status"] = status
                
                query += " GROUP BY c.id ORDER BY c.content_date DESC"
                
                result = await db.execute(text(query), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "content_date": str(row[1]),
                        "day_of_week": row[2],
                        "content_type": row[3],
                        "content_name": self.CONTENT_SCHEDULE.get(row[2], {}).get("name", "未知"),
                        "emoji": self.CONTENT_SCHEDULE.get(row[2], {}).get("emoji", "📝"),
                        "status": row[4],
                        "topic": row[5],
                        "generated_at": row[6].isoformat() if row[6] else None,
                        "published_at": row[7].isoformat() if row[7] else None,
                        "item_count": row[8]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取内容日历失败: {e}")
            return []
    
    async def get_content_items(self, calendar_id: str) -> List[Dict[str, Any]]:
        """获取指定日期的内容条目"""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT id, platform, title, content, hashtags, 
                               call_to_action, video_script, status,
                               views, likes, comments, shares, leads_generated,
                               created_at
                        FROM content_items
                        WHERE calendar_id = :calendar_id
                        ORDER BY platform
                    """),
                    {"calendar_id": calendar_id}
                )
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "platform": row[1],
                        "platform_name": self.PLATFORM_NAMES.get(row[1], row[1]),
                        "title": row[2],
                        "content": row[3],
                        "hashtags": row[4] or [],
                        "call_to_action": row[5],
                        "video_script": row[6],
                        "status": row[7],
                        "stats": {
                            "views": row[8] or 0,
                            "likes": row[9] or 0,
                            "comments": row[10] or 0,
                            "shares": row[11] or 0,
                            "leads": row[12] or 0
                        },
                        "created_at": row[13].isoformat() if row[13] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取内容条目失败: {e}")
            return []
    
    async def update_content_item(
        self, 
        item_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """更新内容条目"""
        try:
            async with async_session_maker() as db:
                set_parts = []
                params = {"id": item_id}
                
                for key, value in updates.items():
                    if key in ["title", "content", "call_to_action", "video_script", "status"]:
                        set_parts.append(f"{key} = :{key}")
                        params[key] = value
                    elif key == "hashtags":
                        set_parts.append("hashtags = :hashtags")
                        params["hashtags"] = value
                
                if set_parts:
                    set_parts.append("updated_at = NOW()")
                    query = f"UPDATE content_items SET {', '.join(set_parts)} WHERE id = :id"
                    await db.execute(text(query), params)
                    await db.commit()
                
                return True
        except Exception as e:
            logger.error(f"更新内容条目失败: {e}")
            return False


# 创建服务单例
content_marketing_service = ContentMarketingService()
