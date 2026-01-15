-- 013_add_assets_and_settings.sql
-- 添加素材库和系统设置表

-- 创建素材表
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- video, audio, image
    category VARCHAR(100) DEFAULT 'general',
    duration INTEGER, -- 时长（秒）
    file_size BIGINT DEFAULT 0,
    file_url TEXT,
    thumbnail_url TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);

-- 创建系统设置表
CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认设置
INSERT INTO system_settings (key, value, description) VALUES
('company', '{}', '公司信息配置'),
('notification', '{"high_intent_threshold": 60, "enable_wechat_notify": true, "enable_email_notify": false, "quiet_hours_start": "22:00", "quiet_hours_end": "08:00"}', '通知设置'),
('ai', '{"model_name": "qwen-max", "temperature": 0.7}', 'AI模型设置')
ON CONFLICT (key) DO NOTHING;

-- 插入一些示例素材数据
INSERT INTO assets (name, type, category, duration, file_size, usage_count) VALUES
('港口航拍01', 'video', 'port', 15, 52428800, 45),
('仓库内景01', 'video', 'warehouse', 12, 41943040, 38),
('商务专业BGM', 'audio', 'bgm_corporate', 180, 5242880, 124),
('活力动感BGM', 'audio', 'bgm_upbeat', 150, 4718592, 89),
('货车运输01', 'video', 'truck', 10, 31457280, 56),
('飞机装货01', 'video', 'airplane', 8, 25165824, 34)
ON CONFLICT DO NOTHING;
