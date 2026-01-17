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
                
                if existing_row and existing_row[1] == 'generated':
                    logger.info(f"📝 {target_date} 的内容已生成，跳过")
                    return {"status": "skipped", "message": "内容已存在"}
                
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
        
        # 获取公司配置
        company_result = await db.execute(
            text("SELECT * FROM company_config LIMIT 1")
        )
        company = company_result.fetchone()
        
        if company:
            data["company"] = {
                "name": company[1] if len(company) > 1 else None,  # company_name
                "intro": company[2] if len(company) > 2 else None,  # company_intro
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
        """
        # 获取模板
        template_result = await db.execute(
            text("""
                SELECT title_template, content_template, hashtags_template, cta_template
                FROM content_templates
                WHERE content_type = :type AND platform = :platform AND is_active = true
                LIMIT 1
            """),
            {"type": content_type, "platform": platform}
        )
        template = template_result.fetchone()
        
        # 构建提示词
        company_name = data_source.get("company", {}).get("name", "专业物流公司")
        
        platform_config = {
            "douyin": {
                "style": "口语化、有节奏感、适合短视频，开头要有钩子",
                "length": "100-200字",
                "extra": "需要生成视频脚本，包含画面描述"
            },
            "xiaohongshu": {
                "style": "亲切、种草风格、多用emoji、适合图文",
                "length": "300-500字",
                "extra": "标题要有数字或疑问，正文分段清晰"
            },
            "wechat_article": {
                "style": "专业、深度、有干货",
                "length": "800-1500字",
                "extra": "需要有小标题、列表、总结"
            },
            "wechat_moments": {
                "style": "简洁、有信息量、适合快速阅读",
                "length": "50-150字",
                "extra": "不需要标题，直接是文案"
            }
        }
        
        platform_info = platform_config.get(platform, platform_config["wechat_moments"])
        
        # 使用模板或AI生成
        if template:
            # 使用模板生成
            content = await self._generate_from_template(template, data_source, platform)
        else:
            # AI自动生成
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
        """使用AI生成内容"""
        
        content_type_names = {
            "knowledge": "物流知识科普",
            "pricing": "运价播报",
            "case": "成功案例分享",
            "policy": "政策解读",
            "faq": "常见问题解答",
            "story": "公司故事",
            "weekly": "周报总结"
        }
        
        # 构建数据摘要
        data_summary = self._build_data_summary(content_type, data_source)
        
        prompt = f"""请为{company_name}生成一篇{content_type_names.get(content_type, '营销')}内容。

## 发布平台
{self.PLATFORM_NAMES.get(platform, platform)}

## 内容风格要求
- 风格：{platform_info['style']}
- 长度：{platform_info['length']}
- 特殊要求：{platform_info['extra']}

## 可用数据
{data_summary}

## 引流要求
- 结尾必须有明确的行动号召（CTA）
- 引导用户添加微信/私信咨询
- 强调"免费咨询"、"专属报价"等钩子

## 输出格式
请按以下JSON格式输出：
{{
    "title": "标题（朋友圈可为空）",
    "content": "正文内容",
    "hashtags": ["话题标签1", "话题标签2"],
    "call_to_action": "行动号召语",
    "video_script": "视频脚本（仅抖音需要，包含画面描述）"
}}
"""
        
        try:
            response = await copywriter_agent.think([{"role": "user", "content": prompt}])
            
            # 解析JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
        except Exception as e:
            logger.error(f"AI生成内容解析失败: {e}")
        
        # 如果AI生成失败，返回默认内容
        return {
            "title": f"{content_type_names.get(content_type, '物流')}分享",
            "content": f"感谢关注{company_name}！我们提供专业的国际物流服务，欢迎咨询！",
            "hashtags": ["物流", "跨境电商", "外贸"],
            "call_to_action": "私信咨询获取专属报价！",
            "contact_info": "添加微信免费咨询"
        }
    
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
        """构建数据摘要供AI使用"""
        lines = []
        
        if "company" in data_source:
            company = data_source["company"]
            if company.get("name"):
                lines.append(f"公司名称：{company['name']}")
        
        if content_type == "pricing" and "pricing" in data_source:
            pricing = data_source["pricing"]
            if isinstance(pricing, dict):
                lines.append("\n### 海运运价")
                for item in pricing.get("sea_freight", [])[:3]:
                    lines.append(f"- {item.get('route')}: ${item.get('price')}/柜, {item.get('transit_time')}")
                
                lines.append("\n### 空运运价")
                for item in pricing.get("air_freight", [])[:2]:
                    lines.append(f"- {item.get('route')}: ¥{item.get('price_per_kg')}/kg")
        
        elif content_type == "case" and "cases" in data_source:
            lines.append("\n### 成功案例")
            for case in data_source["cases"][:2]:
                lines.append(f"- 客户类型：{case.get('customer_type')}")
                lines.append(f"  货物：{case.get('cargo_type')}")
                lines.append(f"  亮点：{case.get('highlight')}")
        
        elif content_type == "faq" and "faq" in data_source:
            lines.append("\n### 高频问题")
            for q in data_source["faq"][:5]:
                lines.append(f"- {q}")
        
        return "\n".join(lines) if lines else "请基于物流行业通用知识生成内容"
    
    # ==================== 模拟数据（等ERP对接后替换） ====================
    
    async def _get_mock_pricing_data(self) -> Dict[str, Any]:
        """模拟运价数据"""
        return {
            "sea_freight": [
                {
                    "route": "深圳 → 汉堡",
                    "container_type": "40GP",
                    "price": 2500,
                    "currency": "USD",
                    "transit_time": "28-32天",
                    "remarks": "本周舱位充足"
                },
                {
                    "route": "宁波 → 鹿特丹",
                    "container_type": "40HQ",
                    "price": 2800,
                    "currency": "USD",
                    "transit_time": "25-30天"
                },
                {
                    "route": "上海 → 费利克斯托",
                    "container_type": "40GP",
                    "price": 2600,
                    "currency": "USD",
                    "transit_time": "30-35天"
                }
            ],
            "air_freight": [
                {
                    "route": "深圳 → 法兰克福",
                    "price_per_kg": 28,
                    "currency": "CNY",
                    "transit_time": "5-7天",
                    "min_weight": 45
                }
            ],
            "rail_freight": [
                {
                    "route": "义乌 → 杜伊斯堡",
                    "container_type": "40GP",
                    "price": 8500,
                    "currency": "USD",
                    "transit_time": "18-22天"
                }
            ],
            "highlight": "本周欧洲航线运价平稳，建议提前预订舱位"
        }
    
    async def _get_mock_case_data(self) -> List[Dict[str, Any]]:
        """模拟案例数据"""
        return [
            {
                "customer_type": "跨境电商卖家",
                "cargo_type": "电子产品",
                "route": "深圳 → 德国FBA",
                "service": "海运+清关+派送",
                "highlight": "15天到门，比客户预期快5天",
                "feedback": "非常满意，已推荐给朋友"
            },
            {
                "customer_type": "外贸工厂",
                "cargo_type": "机械配件",
                "route": "宁波 → 英国",
                "service": "整柜海运",
                "highlight": "帮客户节省了30%运费",
                "feedback": "价格很有竞争力"
            }
        ]
    
    async def _get_mock_policy_data(self) -> Dict[str, Any]:
        """模拟政策数据"""
        return {
            "title": "欧盟CBAM碳关税新规解读",
            "summary": "自2026年起，进口欧盟的钢铁、铝等产品需申报碳排放",
            "key_points": [
                "适用产品范围扩大",
                "需要提供碳排放数据",
                "建议提前做好准备"
            ],
            "impact": "对电子产品影响较小，钢铁铝材需关注",
            "recommendation": "建议与供应商确认碳排放数据"
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
                "海运到欧洲要多久？",
                "空运和海运怎么选？",
                "清关需要什么资料？",
                "可以做FBA派送吗？",
                "运费怎么计算？"
            ]
        except:
            return [
                "海运到欧洲要多久？",
                "空运和海运怎么选？",
                "清关需要什么资料？"
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
