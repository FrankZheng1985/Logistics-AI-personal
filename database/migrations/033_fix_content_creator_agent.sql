-- ================================================
-- 迁移033: 修复小媒（content_creator）AI员工定义
-- 问题：原迁移023中使用了不存在的列名
-- ================================================

-- 1. 添加 content_creator 到 agent_type 枚举
DO $$ BEGIN
    ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'content_creator';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. 插入小媒员工记录（使用正确的列名）
INSERT INTO ai_agents (name, agent_type, description, status, config)
VALUES (
    '小媒', 
    'content_creator', 
    '内容运营专员 - 负责每日内容生成、多平台发布、效果追踪',
    'online',
    '{"capabilities": ["content_generation", "multi_platform", "analytics"]}'::jsonb
)
ON CONFLICT (agent_type) DO UPDATE SET
    name = '小媒',
    description = '内容运营专员 - 负责每日内容生成、多平台发布、效果追踪';

-- 3. 添加小媒的工作标准
INSERT INTO agent_standards (agent_type, standard_category, standard_name, standard_content, quality_metrics, version, is_active)
VALUES 
(
    'content_creator', 
    'professional', 
    '内容运营专业标准',
    '{
        "platforms": ["抖音", "小红书", "微信公众号", "微信朋友圈", "视频号"],
        "content_types": ["运价播报", "知识科普", "成功案例", "政策解读", "FAQ问答"],
        "daily_quota": {
            "posts_per_day": 3,
            "platforms_per_content": 2
        }
    }'::jsonb,
    '{"daily_content_count": 3, "platform_coverage": 5}'::jsonb,
    1,
    true
),
(
    'content_creator', 
    'efficiency', 
    '内容运营效率标准',
    '{
        "generation_time_limit": 300,
        "batch_size": 7,
        "auto_schedule": true
    }'::jsonb,
    '{"avg_generation_time": 60, "batch_completion_rate": 0.95}'::jsonb,
    1,
    true
),
(
    'content_creator', 
    'quality', 
    '内容运营质量标准',
    '{
        "engagement_target": {
            "avg_views": 1000,
            "avg_likes": 50,
            "avg_comments": 10
        },
        "lead_conversion_rate": 0.02
    }'::jsonb,
    '{"content_approval_rate": 0.9, "lead_generation_rate": 0.02}'::jsonb,
    1,
    true
)
ON CONFLICT DO NOTHING;

COMMENT ON COLUMN ai_agents.config IS 'Agent配置参数，包含capabilities等';
