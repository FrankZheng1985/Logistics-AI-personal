-- ================================================
-- 迁移008: 初始化AI员工工作标准数据
-- ================================================

-- 小影 - 视频创作员 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('video_creator', 'quality', '视频质量标准', 
'{
    "video_duration": {"min_seconds": 90, "max_seconds": 300, "default_seconds": 120},
    "resolution": "1080p/4K",
    "frame_rate": 24,
    "requirements": [
        "无水印",
        "无AI生成痕迹", 
        "画面稳定流畅",
        "色彩专业统一",
        "字幕清晰可读",
        "配音清晰自然",
        "背景音乐匹配"
    ],
    "style_requirements": [
        "电影级镜头语言",
        "专业转场效果",
        "情感共鸣设计",
        "品牌调性一致"
    ]
}',
'{"min_duration_seconds": 90, "max_duration_seconds": 300, "resolution": "1080p"}',
TRUE),

('video_creator', 'efficiency', '视频效率标准',
'{
    "short_video_generation_time_minutes": 15,
    "long_video_generation_time_minutes": 30,
    "max_retry_attempts": 3
}',
'{"short_video_time_minutes": 15, "long_video_time_minutes": 30}',
TRUE),

('video_creator', 'professional', '视频专业标准',
'{
    "supported_languages": ["zh-CN", "en-US", "de-DE", "fr-FR", "es-ES", "ja-JP", "ko-KR", "ar-SA", "pt-BR", "ru-RU"],
    "video_types": ["ad", "intro", "route", "case_study", "tutorial"]
}',
'{"language_count": 10, "video_type_count": 5}',
TRUE);

-- 小文 - 文案策划(天下第一笔) 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('copywriter', 'quality', '文案质量标准',
'{
    "originality_rate": 0.95,
    "grammar_error_rate": 0,
    "requirements": [
        "原创度高，无抄袭",
        "无语法错误",
        "符合物流行业专业性",
        "情感共鸣强",
        "行动号召明确",
        "品牌调性一致"
    ],
    "style_requirements": [
        "标题吸睛有力",
        "内容简洁精炼",
        "卖点突出清晰",
        "情感触动人心",
        "节奏感强"
    ]
}',
'{"originality_rate": 0.95, "grammar_error_rate": 0}',
TRUE),

('copywriter', 'efficiency', '文案效率标准',
'{
    "short_copy_time_minutes": 5,
    "long_copy_time_minutes": 15,
    "video_script_time_minutes": 20
}',
'{"short_copy_time": 5, "long_copy_time": 15, "script_time": 20}',
TRUE),

('copywriter', 'professional', '文案专业标准',
'{
    "writing_models": ["AIDA", "PAS", "BAB", "4P", "QUEST"],
    "copy_types": ["video_script", "ad_copy", "moments", "email", "landing_page"],
    "supported_languages": ["中文", "英文", "西班牙语", "德语", "法语", "日语", "韩语", "阿拉伯语"]
}',
'{"model_count": 5, "language_count": 8}',
TRUE);

-- 小调 - AI调度主管 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('coordinator', 'quality', '调度质量标准',
'{
    "report_accuracy_rate": 0.99,
    "requirements": [
        "数据准确无误",
        "分析深入专业",
        "建议可执行",
        "格式规范统一",
        "重点突出"
    ],
    "analysis_depth": [
        "MBA级战略分析",
        "数据驱动决策",
        "趋势预测能力",
        "风险识别预警"
    ]
}',
'{"report_accuracy_rate": 0.99}',
TRUE),

('coordinator', 'efficiency', '调度效率标准',
'{
    "daily_report_time_minutes": 5,
    "weekly_report_time_minutes": 15,
    "monthly_report_time_minutes": 30,
    "task_dispatch_time_seconds": 3
}',
'{"daily_report_time": 5, "dispatch_time_seconds": 3}',
TRUE),

('coordinator', 'professional', '调度专业标准',
'{
    "report_types": ["daily", "weekly", "monthly"],
    "monitoring_scope": [
        "API可用性(可灵AI/通义千问/Serper等)",
        "接口响应时间",
        "错误率统计",
        "SSL证书有效期",
        "数据库连接状态"
    ]
}',
'{"report_type_count": 3, "monitoring_scope_count": 5}',
TRUE);

-- 小销 - 销售客服 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('sales', 'quality', '销售质量标准',
'{
    "customer_satisfaction_rate": 0.90,
    "requirements": [
        "专业友好",
        "回复准确",
        "耐心细致",
        "善于引导",
        "有效收集信息"
    ],
    "communication_style": [
        "热情但不过分",
        "专业但不生硬",
        "主动但不强迫",
        "细心但不啰嗦"
    ]
}',
'{"satisfaction_rate": 0.90}',
TRUE),

('sales', 'efficiency', '销售效率标准',
'{
    "first_response_time_seconds": 3,
    "avg_response_time_seconds": 10,
    "conversation_resolution_rate": 0.85
}',
'{"first_response_seconds": 3, "resolution_rate": 0.85}',
TRUE),

('sales', 'professional', '销售专业标准',
'{
    "knowledge_areas": [
        "海运(整柜/拼箱/散货)",
        "空运(普货/敏感货/危险品)",
        "铁路(中欧班列/中亚班列)",
        "快递(国际快递/跨境电商)",
        "仓储(海外仓/保税仓)",
        "清关(各国政策/流程)"
    ],
    "info_collection_targets": [
        "货物品类和属性",
        "起运地和目的地",
        "货量(重量/体积)",
        "时效要求",
        "预算范围",
        "联系方式"
    ]
}',
'{"knowledge_area_count": 6, "collection_target_count": 6}',
TRUE);

-- 小跟 - 跟进专员 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('follow', 'quality', '跟进质量标准',
'{
    "follow_up_timeliness_rate": 0.95,
    "conversion_rate": 0.15,
    "requirements": [
        "及时跟进不遗漏",
        "个性化沟通",
        "有价值的内容",
        "适度不骚扰",
        "持续建立信任"
    ]
}',
'{"timeliness_rate": 0.95, "conversion_rate": 0.15}',
TRUE),

('follow', 'efficiency', '跟进效率标准',
'{
    "follow_intervals": {
        "S_level_days": 1,
        "A_level_days": 2,
        "B_level_days": 5,
        "C_level_days": 15
    },
    "no_response_strategy": {
        "after_3_no_response": "降低跟进频率",
        "after_5_no_response": "转入冷藏池",
        "reactivate_after_days": 90
    }
}',
'{"s_level_days": 1, "reactivate_days": 90}',
TRUE);

-- 小析 - 客户分析师 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('analyst', 'quality', '分析质量标准',
'{
    "intent_accuracy_rate": 0.85,
    "requirements": [
        "评分准确客观",
        "画像全面深入",
        "洞察有价值",
        "建议可落地"
    ]
}',
'{"intent_accuracy_rate": 0.85}',
TRUE),

('analyst', 'professional', '分析专业标准',
'{
    "scoring_rules": {
        "ask_price": 25,
        "provide_cargo_info": 20,
        "ask_transit_time": 15,
        "multiple_interactions": 30,
        "leave_contact": 50,
        "express_interest": 40,
        "just_asking": -10
    },
    "intent_levels": {
        "S": {"min_score": 80, "action": "重点跟进"},
        "A": {"min_score": 60, "action": "安排小跟重点跟进"},
        "B": {"min_score": 30, "action": "定期跟进"},
        "C": {"min_score": 0, "action": "存档备用"}
    },
    "profile_dimensions": [
        "客户类型",
        "业务规模",
        "主要需求",
        "决策特征",
        "行为特征"
    ]
}',
'{"level_count": 4, "dimension_count": 5}',
TRUE);

-- 小猎 - 线索猎手 工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, is_active)
VALUES 
('lead_hunter', 'quality', '线索质量标准',
'{
    "lead_quality_score_min": 60,
    "requirements": [
        "真实有效的需求",
        "非广告/竞争对手",
        "可追踪联系",
        "需求明确"
    ]
}',
'{"min_quality_score": 60}',
TRUE),

('lead_hunter', 'efficiency', '线索效率标准',
'{
    "daily_analysis_min": 50,
    "response_time_seconds": 5
}',
'{"daily_analysis_min": 50, "response_time_seconds": 5}',
TRUE),

('lead_hunter', 'professional', '线索专业标准',
'{
    "search_sources": ["weibo", "zhihu", "tieba", "google"],
    "search_keywords_cn": ["找货代", "货代推荐", "物流报价", "跨境物流", "FBA物流"],
    "search_keywords_en": ["freight forwarder needed", "shipping quote", "FBA shipping"],
    "high_intent_signals": ["急", "马上", "尽快", "报价", "价格", "urgent", "asap", "quote"]
}',
'{"source_count": 4, "signal_count": 8}',
TRUE);

-- 表注释
COMMENT ON TABLE agent_standards IS 'AI员工工作标准配置表 - 定义各员工的质量、效率、专业标准';
