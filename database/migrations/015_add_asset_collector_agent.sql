-- 015_add_asset_collector_agent.sql
-- 添加素材采集员（小采）AI员工

-- 添加新的agent_type枚举值
DO $$ BEGIN
    ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'asset_collector';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 插入小采员工记录
INSERT INTO ai_agents (name, agent_type, description, status)
VALUES (
    '小采', 
    'asset_collector', 
    '素材采集员，负责从社交媒体和素材网站自动收集物流相关视频、图片和音频素材',
    'online'
)
ON CONFLICT (agent_type) DO UPDATE SET
    name = '小采',
    description = '素材采集员，负责从社交媒体和素材网站自动收集物流相关视频、图片和音频素材';

-- 添加小采的工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, version, is_active)
VALUES 
(
    'asset_collector', 
    'professional', 
    '采集专业标准',
    '{
        "platforms": ["小红书", "抖音", "B站", "Pexels", "Pixabay"],
        "content_types": ["物流仓库", "港口场景", "运输车辆", "快递分拣"],
        "quality_requirements": {
            "min_resolution": "720p",
            "min_duration": 5,
            "max_duration": 300
        }
    }'::jsonb,
    '{"platform_count": 5, "content_type_count": 4}'::jsonb,
    1,
    true
),
(
    'asset_collector', 
    'efficiency', 
    '采集效率标准',
    '{
        "daily_search_count": 10,
        "batch_size": 20,
        "dedup_enabled": true
    }'::jsonb,
    '{"target_per_day": 50, "dedup_rate": 0.3}'::jsonb,
    1,
    true
),
(
    'asset_collector', 
    'quality', 
    '采集质量标准',
    '{
        "copyright_check": true,
        "content_relevance": "物流相关",
        "format_requirements": ["mp4", "webm", "mp3", "jpg", "png"]
    }'::jsonb,
    '{"relevance_score": 80, "format_compliance": 100}'::jsonb,
    1,
    true
)
ON CONFLICT DO NOTHING;

-- 给assets表添加来源字段（如果不存在）
ALTER TABLE assets ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS collected_by VARCHAR(50) DEFAULT 'manual';
