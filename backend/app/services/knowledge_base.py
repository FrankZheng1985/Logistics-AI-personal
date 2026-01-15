"""
知识库服务
AI员工共享知识库系统
支持知识的存储、检索、更新
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.core.config import settings


# 知识类型定义
KNOWLEDGE_TYPES = {
    "clearance_exp": {
        "name": "清关经验",
        "description": "欧洲各国清关流程、注意事项、常见问题"
    },
    "price_ref": {
        "name": "运价参考",
        "description": "欧洲各线路运价、清关费用、派送费率"
    },
    "policy": {
        "name": "政策法规",
        "description": "欧盟/各国海关政策、VAT规定、合规要求"
    },
    "faq": {
        "name": "常见问题",
        "description": "客户常问问题及标准回答"
    },
    "pain_point": {
        "name": "客户痛点",
        "description": "客户关注的痛点和解决方案"
    },
    "market_intel": {
        "name": "市场情报",
        "description": "行业动态、竞品信息、市场趋势"
    },
    "case_study": {
        "name": "成功案例",
        "description": "客户成功案例和解决方案"
    },
    "sales_skill": {
        "name": "销售技巧",
        "description": "话术模板、异议处理、成交技巧"
    }
}


class KnowledgeBaseService:
    """知识库服务"""
    
    def __init__(self):
        pass
    
    async def add_knowledge(
        self,
        content: str,
        knowledge_type: str,
        source: str = "manual",
        source_id: Optional[str] = None,
        tags: List[str] = None,
        is_verified: bool = False
    ) -> Optional[str]:
        """
        添加知识
        
        Args:
            content: 知识内容
            knowledge_type: 知识类型
            source: 来源 (wechat_group/market_intel/manual)
            source_id: 来源记录ID
            tags: 标签列表
            is_verified: 是否已验证
        
        Returns:
            知识ID
        """
        if knowledge_type not in KNOWLEDGE_TYPES:
            logger.warning(f"未知的知识类型: {knowledge_type}")
            knowledge_type = "faq"
        
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO knowledge_base 
                        (content, knowledge_type, source, source_id, tags, is_verified, created_at, updated_at)
                        VALUES (:content, :type, :source, :source_id, :tags, :verified, NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        "content": content,
                        "type": knowledge_type,
                        "source": source,
                        "source_id": source_id,
                        "tags": tags or [],
                        "verified": is_verified
                    }
                )
                knowledge_id = result.fetchone()[0]
                await db.commit()
                
                logger.info(f"📚 添加知识: [{knowledge_type}] {content[:50]}...")
                return str(knowledge_id)
                
        except Exception as e:
            logger.error(f"添加知识失败: {e}")
            return None
    
    async def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        tags: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索知识
        
        Args:
            query: 搜索关键词
            knowledge_type: 限定知识类型
            tags: 限定标签
            limit: 返回数量
        
        Returns:
            匹配的知识列表
        """
        try:
            async with async_session_maker() as db:
                # 构建查询
                sql = """
                    SELECT id, content, knowledge_type, source, tags, 
                           is_verified, usage_count, created_at
                    FROM knowledge_base
                    WHERE content ILIKE :query
                """
                params = {"query": f"%{query}%", "limit": limit}
                
                if knowledge_type:
                    sql += " AND knowledge_type = :type"
                    params["type"] = knowledge_type
                
                if tags:
                    sql += " AND tags && :tags"
                    params["tags"] = tags
                
                sql += " ORDER BY is_verified DESC, usage_count DESC LIMIT :limit"
                
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "content": row[1],
                        "knowledge_type": row[2],
                        "type_name": KNOWLEDGE_TYPES.get(row[2], {}).get("name", row[2]),
                        "source": row[3],
                        "tags": row[4],
                        "is_verified": row[5],
                        "usage_count": row[6],
                        "created_at": row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"搜索知识失败: {e}")
            return []
    
    async def get_knowledge_for_agent(
        self,
        agent_type: str,
        context: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        为AI员工获取相关知识
        
        Args:
            agent_type: AI员工类型
            context: 上下文（对话内容、任务描述等）
            limit: 返回数量
        
        Returns:
            相关知识列表
        """
        # 根据员工类型确定优先知识类型
        type_priority = {
            "sales": ["faq", "sales_skill", "price_ref", "case_study"],
            "follow": ["faq", "sales_skill", "pain_point"],
            "copywriter": ["case_study", "pain_point", "policy"],
            "analyst": ["market_intel", "price_ref", "policy"],
            "analyst2": ["market_intel", "policy", "clearance_exp"]
        }
        
        preferred_types = type_priority.get(agent_type, list(KNOWLEDGE_TYPES.keys()))
        
        try:
            async with async_session_maker() as db:
                # 先按类型优先级搜索
                all_results = []
                
                for knowledge_type in preferred_types:
                    results = await self.search_knowledge(
                        query=context[:100],  # 使用上下文的前100字符作为搜索词
                        knowledge_type=knowledge_type,
                        limit=2
                    )
                    all_results.extend(results)
                    
                    if len(all_results) >= limit:
                        break
                
                # 记录使用
                for item in all_results[:limit]:
                    await db.execute(
                        text("""
                            UPDATE knowledge_base
                            SET usage_count = usage_count + 1
                            WHERE id = :id
                        """),
                        {"id": item["id"]}
                    )
                await db.commit()
                
                return all_results[:limit]
                
        except Exception as e:
            logger.error(f"获取员工知识失败: {e}")
            return []
    
    async def get_answer_for_question(
        self,
        question: str
    ) -> Optional[Dict[str, Any]]:
        """
        为问题查找答案（用于小销回答客户）
        
        Args:
            question: 客户问题
        
        Returns:
            最匹配的知识/答案
        """
        # 关键词匹配
        keywords = self._extract_keywords(question)
        
        results = []
        for kw in keywords:
            matched = await self.search_knowledge(
                query=kw,
                knowledge_type="faq",
                limit=3
            )
            results.extend(matched)
        
        # 去重并按使用次数排序
        seen_ids = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)
        
        unique_results.sort(key=lambda x: x["usage_count"], reverse=True)
        
        return unique_results[0] if unique_results else None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（可以后续用更复杂的NLP）
        stop_words = {"的", "是", "在", "有", "和", "了", "吗", "呢", "啊", "什么", "怎么", "如何"}
        
        # 按标点分割
        import re
        words = re.split(r'[，。？！、\s]+', text)
        
        # 过滤停用词和太短的词
        keywords = [w for w in words if w and len(w) > 1 and w not in stop_words]
        
        return keywords[:5]  # 最多5个关键词
    
    async def update_knowledge(
        self,
        knowledge_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_verified: Optional[bool] = None
    ) -> bool:
        """更新知识"""
        try:
            async with async_session_maker() as db:
                updates = ["updated_at = NOW()"]
                params = {"id": knowledge_id}
                
                if content is not None:
                    updates.append("content = :content")
                    params["content"] = content
                
                if tags is not None:
                    updates.append("tags = :tags")
                    params["tags"] = tags
                
                if is_verified is not None:
                    updates.append("is_verified = :verified")
                    params["verified"] = is_verified
                
                sql = f"UPDATE knowledge_base SET {', '.join(updates)} WHERE id = :id"
                await db.execute(text(sql), params)
                await db.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"更新知识失败: {e}")
            return False
    
    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("DELETE FROM knowledge_base WHERE id = :id"),
                    {"id": knowledge_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"删除知识失败: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计"""
        try:
            async with async_session_maker() as db:
                # 总量统计
                result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE is_verified = true) as verified,
                            SUM(usage_count) as total_usage
                        FROM knowledge_base
                    """)
                )
                total_stats = result.fetchone()
                
                # 按类型统计
                result = await db.execute(
                    text("""
                        SELECT knowledge_type, COUNT(*) as count
                        FROM knowledge_base
                        GROUP BY knowledge_type
                        ORDER BY count DESC
                    """)
                )
                type_stats = result.fetchall()
                
                # 按来源统计
                result = await db.execute(
                    text("""
                        SELECT source, COUNT(*) as count
                        FROM knowledge_base
                        GROUP BY source
                        ORDER BY count DESC
                    """)
                )
                source_stats = result.fetchall()
                
                # 热门知识
                result = await db.execute(
                    text("""
                        SELECT id, content, knowledge_type, usage_count
                        FROM knowledge_base
                        ORDER BY usage_count DESC
                        LIMIT 10
                    """)
                )
                hot_knowledge = result.fetchall()
                
                return {
                    "total": {
                        "count": total_stats[0] if total_stats else 0,
                        "verified": total_stats[1] if total_stats else 0,
                        "total_usage": total_stats[2] if total_stats else 0
                    },
                    "by_type": [
                        {
                            "type": row[0],
                            "type_name": KNOWLEDGE_TYPES.get(row[0], {}).get("name", row[0]),
                            "count": row[1]
                        }
                        for row in type_stats
                    ],
                    "by_source": [
                        {"source": row[0], "count": row[1]}
                        for row in source_stats
                    ],
                    "hot_knowledge": [
                        {
                            "id": str(row[0]),
                            "content": row[1][:100],
                            "type": row[2],
                            "usage_count": row[3]
                        }
                        for row in hot_knowledge
                    ]
                }
                
        except Exception as e:
            logger.error(f"获取知识库统计失败: {e}")
            return {}
    
    async def init_default_knowledge(self):
        """初始化默认知识 - 欧洲物流专业知识库"""
        default_knowledge = [
            # ============================================================
            # 清关经验 (clearance_exp) - 15条
            # ============================================================
            # 德国清关
            {
                "content": "德国清关要点：1）必须有有效EORI号；2）商业发票需包含HS编码、货值、原产国；3）德国海关对低申报查验严格，建议如实申报；4）清关时效通常1-2个工作日，查验需额外2-3天。",
                "type": "clearance_exp",
                "tags": ["德国", "清关", "EORI", "要点"]
            },
            {
                "content": "德国双清包税服务：适合没有德国VAT税号的客户，我们使用自有税号完成清关和VAT缴纳，客户只需支付含税运费，无需担心税务问题。适合小批量、试水市场的客户。",
                "type": "clearance_exp",
                "tags": ["德国", "双清包税", "VAT"]
            },
            # 法国清关
            {
                "content": "法国海关特点：1）对产品描述要求严格，HS编码必须准确；2）对纺织品、电子产品查验率较高；3）法国EPR注册是必须的，未注册可能被扣货；4）建议提前准备CE认证文件。",
                "type": "clearance_exp",
                "tags": ["法国", "清关", "EPR", "CE认证"]
            },
            {
                "content": "法国特殊品清关：葡萄酒、化妆品、食品类需要额外资质。葡萄酒需要进口许可证，化妆品需要CPNP注册，食品需要符合欧盟食品安全标准并提供成分表。",
                "type": "clearance_exp",
                "tags": ["法国", "特殊品", "葡萄酒", "化妆品"]
            },
            # 英国清关
            {
                "content": "英国脱欧后清关变化：1）需要单独的UK EORI号；2）从欧盟进入英国需要清关；3）UKCA认证逐步取代CE认证；4）135英镑以下货物可使用简化申报流程。",
                "type": "clearance_exp",
                "tags": ["英国", "脱欧", "UKCA", "清关"]
            },
            {
                "content": "英国低价值货物（≤135英镑）清关：可使用IOSS类似机制，在销售时收取VAT，清关时无需再缴税。适合跨境电商B2C小包业务，大幅简化清关流程。",
                "type": "clearance_exp",
                "tags": ["英国", "低价值", "小包", "VAT"]
            },
            # 意大利清关
            {
                "content": "意大利清关注意事项：1）米兰海关效率高于罗马；2）时尚品类（服装、鞋包）查验率高，需准备品牌授权；3）意大利海关对货值核实严格；4）清关时效2-3个工作日。",
                "type": "clearance_exp",
                "tags": ["意大利", "清关", "米兰", "时尚品"]
            },
            # 荷兰清关
            {
                "content": "荷兰鹿特丹港优势：1）欧洲最大港口，清关效率高；2）AEO认证企业可享受快速通道；3）适合作为欧盟中转枢纽，货物可免税转运至其他欧盟国家；4）有完善的保税仓体系。",
                "type": "clearance_exp",
                "tags": ["荷兰", "鹿特丹", "AEO", "中转"]
            },
            {
                "content": "荷兰VAT递延政策：货物在荷兰清关后转运至其他欧盟国家，可以申请VAT递延，在最终销售国缴纳VAT，避免双重征税，有效降低资金占用。",
                "type": "clearance_exp",
                "tags": ["荷兰", "VAT递延", "税务筹划"]
            },
            # 西班牙清关
            {
                "content": "西班牙清关特点：1）马德里和巴塞罗那为主要清关口岸；2）食品类需要AESAN注册；3）西班牙海关对中国商品查验较多；4）建议使用正规渠道，避免灰清风险。",
                "type": "clearance_exp",
                "tags": ["西班牙", "清关", "食品", "AESAN"]
            },
            # VAT递延
            {
                "content": "欧盟VAT递延操作指南：1）在荷兰/比利时清关；2）使用Fiscal Representative代理；3）货物转运至目的国仓库；4）在目的国销售时缴纳VAT。可节省20%左右的前期资金占用。",
                "type": "clearance_exp",
                "tags": ["VAT递延", "税务", "荷兰", "比利时"]
            },
            {
                "content": "VAT税号申请流程：1）准备公司营业执照、法人护照等资料；2）通过税务代理提交申请；3）德国约4-8周，英国约2-4周，法国约6-10周；4）获得税号后即可使用自己税号清关。",
                "type": "clearance_exp",
                "tags": ["VAT", "税号申请", "流程"]
            },
            # 特殊品清关
            {
                "content": "带电产品欧洲清关要求：1）必须有CE认证和MSDS报告；2）电池需要UN38.3认证；3）锂电池需要标注Wh值；4）建议走正规带电渠道，避免被查扣。内置电池和配套电池清关相对容易，纯电池风险较高。",
                "type": "clearance_exp",
                "tags": ["带电产品", "电池", "CE", "MSDS"]
            },
            {
                "content": "化妆品欧盟清关要点：1）必须完成CPNP（化妆品产品通知门户）注册；2）需要产品安全评估报告；3）标签必须符合欧盟要求（成分、生产日期、责任人等）；4）建议找有经验的代理处理。",
                "type": "clearance_exp",
                "tags": ["化妆品", "CPNP", "欧盟", "合规"]
            },
            {
                "content": "食品类欧盟清关：1）需要符合欧盟食品安全标准；2）提供成分表、营养标签；3）某些食品需要进口许可；4）需要指定欧盟境内食品经营者（FBO）；5）肉类、乳制品等动物源性产品限制严格。",
                "type": "clearance_exp",
                "tags": ["食品", "欧盟", "安全标准", "FBO"]
            },
            
            # ============================================================
            # 运价参考 (price_ref) - 12条
            # ============================================================
            {
                "content": "欧洲海运拼箱运价参考（中国-欧洲主要港口）：普货约$80-120/CBM，旺季（9-12月）可能上涨30-50%。含起运港杂费，不含目的港清关和派送。具体价格需根据实际货量和目的港报价。",
                "type": "price_ref",
                "tags": ["海运", "拼箱", "运价", "欧洲"]
            },
            {
                "content": "欧洲空运运价参考：普货约￥30-45/KG，敏感货约￥40-55/KG，带电产品约￥45-65/KG。淡旺季价格波动较大，大货量可议价。以上为参考价，实际以报价单为准。",
                "type": "price_ref",
                "tags": ["空运", "运价", "普货", "敏感货"]
            },
            {
                "content": "中欧班列运价参考：约$3000-5000/柜（40HQ），时效15-20天。相比海运快10-15天，价格比空运低60-70%。适合对时效有要求但预算有限的大货量客户。",
                "type": "price_ref",
                "tags": ["中欧班列", "铁路", "运价", "整柜"]
            },
            {
                "content": "德国清关费用参考：清关代理费€50-100/票，海关查验费€100-300/次，仓储费€1-3/CBM/天。VAT为货值的19%，关税根据HS编码0-15%不等。",
                "type": "price_ref",
                "tags": ["德国", "清关费", "VAT", "关税"]
            },
            {
                "content": "英国清关费用参考：清关代理费£40-80/票，查验费£80-200/次。VAT 20%，关税根据商品类型0-12%。脱欧后清关手续增加，费用略有上涨。",
                "type": "price_ref",
                "tags": ["英国", "清关费", "VAT", "关税"]
            },
            {
                "content": "法国清关费用参考：清关代理费€60-120/票，查验费€120-350/次。VAT 20%，部分商品优惠税率5.5%或10%。EPR合规费用另计。",
                "type": "price_ref",
                "tags": ["法国", "清关费", "VAT", "EPR"]
            },
            {
                "content": "欧洲境内派送费率参考：德国DPD/DHL约€5-15/件（30KG内），偏远地区附加€5-10。大件货（>30KG）走专线派送，约€0.1-0.2/KG，最低消费€20-30。",
                "type": "price_ref",
                "tags": ["派送", "德国", "最后一公里", "费率"]
            },
            {
                "content": "欧洲偏远地区附加费说明：主要快递公司对偏远地区收取附加费，通常€5-15/件。偏远地区定义：离主要城市>50KM的乡村、岛屿、山区等。可通过快递官网查询邮编是否偏远。",
                "type": "price_ref",
                "tags": ["偏远地区", "附加费", "派送"]
            },
            {
                "content": "德国海外仓费用参考：仓储费€3-8/CBM/月，入库操作费€0.5-1/件，出库操作费€1-3/单，退货处理费€2-5/件。具体费用因仓库位置和服务内容而异。",
                "type": "price_ref",
                "tags": ["海外仓", "德国", "仓储费", "操作费"]
            },
            {
                "content": "英国海外仓费用参考：仓储费£2-6/CBM/月，入库£0.3-0.8/件，出库£0.8-2/单。脱欧后英国仓与欧盟仓需分开备货，增加了仓储成本。",
                "type": "price_ref",
                "tags": ["海外仓", "英国", "仓储费"]
            },
            {
                "content": "欧洲境内卡车运输费率：德国境内约€1.5-2.5/KM（整车），拼车按体积或重量计费。跨国运输德国-法国约€800-1200/车，德国-意大利约€1000-1500/车。",
                "type": "price_ref",
                "tags": ["卡车", "境内运输", "欧洲", "跨国"]
            },
            {
                "content": "FBA头程费用参考（中国-德国FBA）：海运约￥15-25/KG，空运约￥35-50/KG，铁路约￥20-30/KG。含清关派送，不含亚马逊入仓费。旺季价格上浮20-40%。",
                "type": "price_ref",
                "tags": ["FBA", "头程", "亚马逊", "德国"]
            },
            
            # ============================================================
            # 政策法规 (policy) - 10条
            # ============================================================
            {
                "content": "欧盟IOSS政策（进口一站式服务）：适用于货值≤150欧元的B2C货物。卖家在IOSS系统注册后，在销售时收取VAT，货物入境时凭IOSS号免缴进口VAT，简化清关流程，提升妥投效率。",
                "type": "policy",
                "tags": ["IOSS", "欧盟", "B2C", "VAT"]
            },
            {
                "content": "欧盟EPR（生产者责任延伸）制度：要求在欧盟销售包装产品、电子电器、电池、纺织品的企业必须注册EPR，承担产品回收处理责任。德国LUCID、法国SYDEREP等各国有独立系统，未注册可能被平台下架或海关扣货。",
                "type": "policy",
                "tags": ["EPR", "欧盟", "合规", "包装"]
            },
            {
                "content": "CE认证要求：在欧盟销售的产品必须符合CE标准，包括电子电器、玩具、机械、医疗器械等。CE标志表明产品符合欧盟安全、健康、环保要求。无CE认证的产品将被拒绝入境。",
                "type": "policy",
                "tags": ["CE认证", "欧盟", "合规", "安全"]
            },
            {
                "content": "英国UKCA认证：2021年1月1日起，部分产品进入英国市场需要UKCA标志（UK Conformity Assessed），取代CE标志。目前仍有过渡期，建议新产品同时准备CE和UKCA。",
                "type": "policy",
                "tags": ["UKCA", "英国", "认证", "脱欧"]
            },
            {
                "content": "欧盟新电池法规（2023年生效）：要求电池产品必须有碳足迹声明、再生材料含量标签、电池护照等。2027年起锂电池必须达到最低回收效率。跨境电商卖家需提前准备合规方案。",
                "type": "policy",
                "tags": ["电池法规", "欧盟", "合规", "环保"]
            },
            {
                "content": "欧盟碳边境调节机制（CBAM）：2026年全面实施，进口商需为特定产品（钢铁、铝、水泥、化肥、电力、氢）购买CBAM证书，缴纳碳关税。目前处于过渡期，需报告碳排放数据。",
                "type": "policy",
                "tags": ["CBAM", "碳关税", "欧盟", "环保"]
            },
            {
                "content": "欧盟各国VAT税率汇总：德国19%，法国20%，英国20%，意大利22%，西班牙21%，荷兰21%，波兰23%，比利时21%。部分商品（食品、书籍、儿童用品）享受优惠税率。",
                "type": "policy",
                "tags": ["VAT", "税率", "欧盟", "各国"]
            },
            {
                "content": "欧盟禁止进口商品：象牙制品、濒危动植物制品、仿冒品、部分农产品、未经授权的药品等。限制进口：武器、烟草、酒精（需许可证）。违规进口将被扣押销毁并可能面临罚款。",
                "type": "policy",
                "tags": ["禁限品", "欧盟", "进口限制"]
            },
            {
                "content": "欧盟产品安全法规（通用产品安全条例GPSR）：2024年12月起实施，要求所有消费品必须安全，并在产品或包装上标注制造商/进口商信息、可追溯标识。跨境电商需确保产品合规。",
                "type": "policy",
                "tags": ["GPSR", "产品安全", "欧盟", "合规"]
            },
            {
                "content": "德国包装法（VerpackG）：在德国销售带包装商品的企业必须注册LUCID系统，并与双元系统签约，缴纳包装回收费。未注册将面临高额罚款，亚马逊等平台会强制下架违规商品。",
                "type": "policy",
                "tags": ["包装法", "德国", "LUCID", "EPR"]
            },
            
            # ============================================================
            # 常见问题 (faq) - 20条
            # ============================================================
            # 时效类
            {
                "content": "Q：海运到欧洲要多久？A：中国到欧洲主要港口海运时效约25-35天（港到港），加上清关和派送，门到门约30-45天。旺季可能延长5-10天。",
                "type": "faq",
                "tags": ["海运", "时效", "欧洲"]
            },
            {
                "content": "Q：空运到欧洲要多久？A：正常情况下5-8天可到达（门到门），含清关时间。旺季或航班紧张时可能延长至10-12天。敏感货或带电产品可能多1-2天。",
                "type": "faq",
                "tags": ["空运", "时效", "欧洲"]
            },
            {
                "content": "Q：中欧班列时效多长？A：从中国发运到欧洲主要城市约15-20天，比海运快10-15天，比空运慢7-10天。性价比高，适合对时效有一定要求的大货量。",
                "type": "faq",
                "tags": ["中欧班列", "时效", "铁路"]
            },
            # 价格类
            {
                "content": "Q：报价需要提供什么信息？A：1）货物名称和品类；2）重量和体积（或件数和单件尺寸）；3）起运地和目的地；4）是否需要清关和派送；5）是否有VAT税号；6）特殊要求（时效、保险等）。",
                "type": "faq",
                "tags": ["报价", "信息", "询价"]
            },
            {
                "content": "Q：为什么海运报价差异大？A：影响因素包括：1）起运港和目的港；2）货物类型（普货/危险品）；3）体积和重量比；4）淡旺季；5）是否含清关派送；6）附加服务（保险、仓储）。建议提供详细信息获取准确报价。",
                "type": "faq",
                "tags": ["报价", "海运", "价格因素"]
            },
            {
                "content": "Q：空运按什么计费？A：空运按实重和体积重取大者计费。体积重=长×宽×高(cm)÷6000。例如：实重10KG，尺寸50×40×30cm，体积重=10KG，按10KG计费。",
                "type": "faq",
                "tags": ["空运", "计费", "体积重"]
            },
            # 清关类
            {
                "content": "Q：清关需要什么资料？A：基本资料：1）商业发票（含品名、数量、单价、总价、HS编码）；2）装箱单；3）提单/运单。特殊品可能需要：CE证书、MSDS、品牌授权、原产地证等。",
                "type": "faq",
                "tags": ["清关", "资料", "单证"]
            },
            {
                "content": "Q：清关要多久？A：正常情况下1-3个工作日。如遇海关查验，可能延长2-5天。节假日前后、旺季查验率较高。我们有专业清关团队，尽量确保时效。",
                "type": "faq",
                "tags": ["清关", "时效", "查验"]
            },
            {
                "content": "Q：会不会被海关查验？A：海关查验有一定随机性，但以下情况查验率较高：1）新客户首次进口；2）货值异常（过高或过低）；3）敏感品类（电子、纺织）；4）申报信息不完整。如实申报可降低风险。",
                "type": "faq",
                "tags": ["清关", "查验", "风险"]
            },
            # VAT类
            {
                "content": "Q：什么是VAT？A：VAT是增值税（Value Added Tax），在欧盟国家进口和销售时都需要缴纳。进口VAT=（货值+运费+关税）×税率。德国19%，法国20%，英国20%。",
                "type": "faq",
                "tags": ["VAT", "增值税", "税率"]
            },
            {
                "content": "Q：没有VAT税号怎么办？A：有两个选择：1）双清包税服务：使用我们的税号清关，含税价一口价，适合小批量；2）申请自己的VAT税号：适合长期稳定出货，可抵扣进口VAT。",
                "type": "faq",
                "tags": ["VAT", "税号", "双清包税"]
            },
            {
                "content": "Q：什么是双清包税？A：双清包税是指物流公司使用自有税号完成起运地和目的地清关，并代缴VAT和关税，客户只需支付一个含税总价。优点是省心，缺点是无法抵扣VAT。",
                "type": "faq",
                "tags": ["双清包税", "VAT", "清关"]
            },
            # 海外仓类
            {
                "content": "Q：海外仓入仓流程是什么？A：1）提前发送入仓预报（SKU、数量、箱规）；2）货物到港清关；3）派送至仓库；4）仓库验收上架；5）系统确认库存。整个流程3-5个工作日。",
                "type": "faq",
                "tags": ["海外仓", "入仓", "流程"]
            },
            {
                "content": "Q：海外仓仓储费怎么算？A：按占用体积×天数计算，通常€3-8/CBM/月。首月免仓储费，超过90天的滞销库存可能加收长期仓储费。建议合理控制库存周转。",
                "type": "faq",
                "tags": ["海外仓", "仓储费", "计算"]
            },
            {
                "content": "Q：退货怎么处理？A：海外仓支持退货处理：1）退回仓库质检；2）合格品重新上架；3）不合格品可选择销毁或退回国内。退货处理费€2-5/件，具体根据操作复杂度。",
                "type": "faq",
                "tags": ["海外仓", "退货", "处理"]
            },
            # 境内派送类
            {
                "content": "Q：欧洲境内运输时效多久？A：德国境内1-2天，德国到周边国家（法、荷、比）2-3天，到南欧（意、西）3-5天，到东欧3-4天。偏远地区可能多1-2天。",
                "type": "faq",
                "tags": ["境内运输", "时效", "欧洲"]
            },
            {
                "content": "Q：什么是偏远地区？A：距离主要城市较远的乡村、山区、岛屿等。各快递公司定义不同，可通过邮编查询。偏远地区派送需加收€5-15/件附加费，时效也会延长1-2天。",
                "type": "faq",
                "tags": ["偏远地区", "派送", "附加费"]
            },
            # 特殊货物类
            {
                "content": "Q：带电产品能发吗？A：可以。内置电池和配套电池都可以走带电渠道。需要提供：1）电池信息（型号、容量、Wh值）；2）MSDS报告；3）UN38.3认证。纯电池限制较多，建议咨询。",
                "type": "faq",
                "tags": ["带电产品", "电池", "限制"]
            },
            {
                "content": "Q：食品能清关吗？A：可以，但要求较高：1）需符合欧盟食品安全标准；2）提供成分表和营养标签（目的国语言）；3）指定欧盟境内食品经营者；4）部分食品需要进口许可。建议提前咨询具体品类要求。",
                "type": "faq",
                "tags": ["食品", "清关", "欧盟"]
            },
            {
                "content": "Q：液体、粉末能发吗？A：可以走特定渠道。液体需要密封包装，提供成分说明；粉末需要提供检测报告证明非违禁品。化妆品类液体需要CPNP注册。具体可咨询确认。",
                "type": "faq",
                "tags": ["液体", "粉末", "敏感货"]
            },
            
            # ============================================================
            # 客户痛点 (pain_point) - 8条
            # ============================================================
            {
                "content": "痛点：清关被扣货怎么办？解决方案：1）我们有专业清关团队，熟悉各国海关政策；2）提前审核资料，确保合规；3）遇到问题第一时间沟通处理；4）必要时可协助申诉或转关。多年经验，清关通过率99%+。",
                "type": "pain_point",
                "tags": ["扣货", "清关", "解决方案"]
            },
            {
                "content": "痛点：VAT成本太高怎么办？解决方案：1）VAT递延方案：在荷兰/比利时清关后转运，延迟缴税；2）合理税务筹划：利用欧盟成员国间的税务优惠；3）正规申报：避免补税罚款风险。帮您合法降低税务成本。",
                "type": "pain_point",
                "tags": ["VAT", "成本", "税务筹划"]
            },
            {
                "content": "痛点：物流时效不稳定？解决方案：1）多渠道保障：海运、空运、铁路多种选择；2）实时追踪系统：货物全程可视；3）异常预警：及时发现和处理问题；4）备选方案：遇到延误有应急措施。确保您的供应链稳定。",
                "type": "pain_point",
                "tags": ["时效", "稳定性", "供应链"]
            },
            {
                "content": "痛点：退货处理困难？解决方案：1）欧洲海外仓支持退货接收；2）专业质检团队；3）合格品可重新上架销售；4）残次品可选择销毁或退回；5）退货数据分析帮助改进产品。让退货不再是负担。",
                "type": "pain_point",
                "tags": ["退货", "海外仓", "处理"]
            },
            {
                "content": "痛点：沟通时差问题？解决方案：1）欧洲本地团队支持当地时间服务；2）中国团队早晚班轮值；3）紧急问题7×24小时响应；4）微信、邮件、电话多渠道沟通。确保您的问题随时得到响应。",
                "type": "pain_point",
                "tags": ["时差", "沟通", "服务"]
            },
            {
                "content": "痛点：小批量发货成本高？解决方案：1）拼箱服务：与其他货主拼柜降低成本；2）周发货计划：固定航线稳定价格；3）海外仓小批量补货方案；4）阶梯价格：累计货量享受优惠。小客户也能享受大客户待遇。",
                "type": "pain_point",
                "tags": ["小批量", "成本", "拼箱"]
            },
            {
                "content": "痛点：不懂欧洲市场合规要求？解决方案：1）免费合规咨询：EPR、CE、VAT等；2）协助办理各类认证和注册；3）定期分享政策法规更新；4）一站式合规解决方案。让您专注业务，合规交给我们。",
                "type": "pain_point",
                "tags": ["合规", "咨询", "EPR"]
            },
            {
                "content": "痛点：找不到靠谱的物流商？解决方案：1）10年+欧洲物流经验；2）完善的服务网络覆盖欧洲主要国家；3）透明报价无隐藏费用；4）专属客服一对一服务；5）众多客户案例可查证。选择我们，选择放心。",
                "type": "pain_point",
                "tags": ["信任", "服务", "经验"]
            },
            
            # ============================================================
            # 市场情报 (market_intel) - 6条
            # ============================================================
            {
                "content": "欧洲电商市场概况：德国是欧洲最大电商市场，2023年规模约1000亿欧元；英国第二，约1200亿英镑；法国第三，约600亿欧元。亚马逊在德英法占主导，本土平台如Otto、Cdiscount也有一定份额。",
                "type": "market_intel",
                "tags": ["欧洲", "电商", "市场规模"]
            },
            {
                "content": "物流旺季提醒：欧洲主要旺季：1）Prime Day（7月）提前30天备货；2）黑五/网一（11月）提前45-60天备货；3）圣诞季（12月）提前60天备货；4）新年促销（1月）。旺季运价上涨、舱位紧张，务必提前规划。",
                "type": "market_intel",
                "tags": ["旺季", "备货", "规划"]
            },
            {
                "content": "2024年海运运价走势：受红海危机影响，欧线运价大幅上涨，从$1500/TEU涨至$4000-5000/TEU。预计2024年下半年逐步回落，但仍高于2023年水平。建议关注航线动态，灵活调整发货计划。",
                "type": "market_intel",
                "tags": ["运价", "海运", "走势"]
            },
            {
                "content": "欧盟最新贸易政策动态：1）CBAM碳关税2026年实施；2）EPR制度扩展到更多品类；3）数字服务税影响大型电商平台；4）产品安全新规GPSR 2024年12月生效。建议密切关注政策变化，提前合规。",
                "type": "market_intel",
                "tags": ["政策", "欧盟", "动态"]
            },
            {
                "content": "跨境电商物流趋势：1）海外仓模式成为主流，提升时效和客户体验；2）多渠道物流（海运+空运+铁路）降低风险；3）智能化仓储提高效率；4）绿色物流成为竞争力。建议布局海外仓，优化供应链。",
                "type": "market_intel",
                "tags": ["趋势", "跨境电商", "物流"]
            },
            {
                "content": "竞品分析参考：欧洲物流市场主要玩家：1）传统货代（德迅、DSV等）覆盖广但价格较高；2）平台物流（亚马逊FBA）便捷但灵活性差；3）专线物流公司（如我们）性价比高、服务专业。差异化竞争，专注欧洲市场深耕细作。",
                "type": "market_intel",
                "tags": ["竞品", "分析", "差异化"]
            },
            
            # ============================================================
            # 成功案例 (case_study) - 5条
            # ============================================================
            {
                "content": "案例：跨境电商大卖月发货量提升3倍。客户背景：深圳3C电子卖家，主做德国亚马逊。痛点：原物流商时效不稳定，旺季经常断货。方案：海运+空运组合，德国海外仓备货。效果：库存周转提升50%，物流成本降低20%，销售额增长200%。",
                "type": "case_study",
                "tags": ["电商", "3C", "德国", "成功案例"]
            },
            {
                "content": "案例：传统外贸工厂转型DDP服务。客户背景：浙江家具工厂，原做FOB出口。痛点：客户要求送货上门，但不懂欧洲清关。方案：提供DDP一站式服务，从工厂到欧洲客户仓库。效果：订单转化率提升40%，客户满意度大幅提高，开拓了新的大客户。",
                "type": "case_study",
                "tags": ["外贸", "DDP", "家具", "成功案例"]
            },
            {
                "content": "案例：旺季紧急清关48小时解决。客户背景：服装卖家，黑五前货物在德国被扣。痛点：眼看大促开始，货物清关遥遥无期。方案：紧急介入，补充资料，协调海关，优先处理。效果：48小时内完成清关，货物及时入仓，客户黑五销售未受影响。",
                "type": "case_study",
                "tags": ["紧急", "清关", "旺季", "成功案例"]
            },
            {
                "content": "案例：海外仓助力48小时妥投。客户背景：德国本土电商平台卖家，主营家居用品。痛点：原从国内直发，时效15-20天，退货率高。方案：德国海外仓备货+本地派送。效果：妥投时效缩短至1-2天，退货率下降60%，店铺评分提升至4.8星。",
                "type": "case_study",
                "tags": ["海外仓", "时效", "退货", "成功案例"]
            },
            {
                "content": "案例：带电产品合规清关。客户背景：移动电源品牌，拓展欧洲市场。痛点：多次被海关扣货，不清楚合规要求。方案：协助准备CE认证、MSDS、UN38.3等文件，选择正规带电渠道。效果：清关一次通过，后续发货顺畅，成功进入欧洲多个国家市场。",
                "type": "case_study",
                "tags": ["带电", "合规", "清关", "成功案例"]
            },
            
            # ============================================================
            # 销售技巧 (sales_skill) - 10条
            # ============================================================
            {
                "content": "首次询价话术：客户来询价时，先专业引导收集信息：'好的，为了给您准确的报价，我需要了解几个信息：1）货物是什么品类？2）大概多重多大？3）发到哪个国家/城市？4）有没有VAT税号？您方便说一下吗？'",
                "type": "sales_skill",
                "tags": ["话术", "询价", "信息收集"]
            },
            {
                "content": "处理'价格太贵'异议：1）先认同感受：'理解您对成本的关注'；2）说明价值：'我们的报价包含清关、派送、全程追踪，是门到门一口价'；3）对比算账：'如果算上隐藏费用和售后保障，其实综合成本更低'；4）提供方案：'我们也有经济型方案，时效稍长但价格更优惠，您看需要吗？'",
                "type": "sales_skill",
                "tags": ["异议处理", "价格", "话术"]
            },
            {
                "content": "竞品对比技巧：1）不主动贬低竞争对手；2）突出自身差异化优势：'我们专注欧洲市场10年，在清关方面特别有经验'；3）用案例说话：'很多客户之前用过XX，后来选择我们是因为...'；4）让客户自己比较：'您可以先小批量试一下，对比看看'。",
                "type": "sales_skill",
                "tags": ["竞品", "对比", "差异化"]
            },
            {
                "content": "促成成交技巧：1）制造紧迫感：'旺季快到了，舱位紧张，建议尽早确认'；2）首单优惠：'首次合作我们可以给个优惠价，让您体验一下服务'；3）降低门槛：'可以先发一批试试，满意再长期合作'；4）明确下一步：'那我现在帮您预订舱位，您把货物信息发我？'",
                "type": "sales_skill",
                "tags": ["成交", "促成", "技巧"]
            },
            {
                "content": "老客户维护技巧：1）定期关怀：节日问候、生日祝福；2）主动分享：行业资讯、政策变化、运价走势；3）专属服务：优先排舱、专属报价；4）问题预防：发现潜在问题主动沟通；5）邀请反馈：定期询问满意度，持续改进。",
                "type": "sales_skill",
                "tags": ["维护", "老客户", "关系"]
            },
            {
                "content": "处理'考虑一下'话术：1）表示理解：'好的，多比较是应该的'；2）探询顾虑：'方便说一下主要考虑哪方面吗？价格还是时效？'；3）解决问题：针对性解答；4）留下钩子：'我把详细方案发您，有问题随时问我'；5）设定跟进：'那我明天再联系您？'",
                "type": "sales_skill",
                "tags": ["异议处理", "跟进", "话术"]
            },
            {
                "content": "挖掘需求技巧：不只是问'发什么货到哪里'，要深挖：1）'您现在的物流痛点是什么？'；2）'对时效有什么要求？'；3）'预算大概是多少？'；4）'后续发货量大概怎样？'；5）'之前用过哪些物流商？有什么不满意的？'了解越多，方案越精准。",
                "type": "sales_skill",
                "tags": ["需求", "挖掘", "沟通"]
            },
            {
                "content": "报价技巧：1）不要只报价格，要报方案；2）说明报价包含什么、不包含什么；3）多给选择：快的vs便宜的；4）强调价值而非价格；5）留有谈判空间；6）报价后主动跟进，不要等客户来问。",
                "type": "sales_skill",
                "tags": ["报价", "技巧", "方案"]
            },
            {
                "content": "处理客户投诉：1）先道歉：'非常抱歉给您带来不便'；2）倾听：让客户说完，不要打断；3）记录：确认问题细节；4）行动：'我马上帮您查一下处理'；5）反馈：及时告知处理进展；6）补救：必要时给予补偿；7）总结：分析原因，避免再发生。",
                "type": "sales_skill",
                "tags": ["投诉", "处理", "售后"]
            },
            {
                "content": "微信朋友圈营销技巧：1）内容多样：行业资讯+案例分享+日常动态；2）频率适中：每天1-2条，不要刷屏；3）时间选择：早9点、中午12点、晚8点发布效果好；4）互动回复：点赞评论客户朋友圈；5）专业形象：展示专业知识，建立信任感。",
                "type": "sales_skill",
                "tags": ["朋友圈", "营销", "微信"]
            }
        ]
        
        for item in default_knowledge:
            await self.add_knowledge(
                content=item["content"],
                knowledge_type=item["type"],
                source="system",
                tags=item["tags"],
                is_verified=True
            )
        
        logger.info(f"📚 初始化 {len(default_knowledge)} 条欧洲物流专业知识")


# 创建单例
knowledge_base = KnowledgeBaseService()
