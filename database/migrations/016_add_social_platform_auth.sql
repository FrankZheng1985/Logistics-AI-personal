-- 016_add_social_platform_auth.sql
-- 社交媒体平台登录状态管理

-- 创建平台类型枚举
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'social_platform') THEN
        CREATE TYPE social_platform AS ENUM ('xiaohongshu', 'douyin', 'bilibili', 'weixin_video');
    END IF;
END $$;

-- 创建平台登录状态表
CREATE TABLE IF NOT EXISTS social_platform_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform social_platform NOT NULL UNIQUE,
    platform_name VARCHAR(50) NOT NULL,
    -- 登录状态
    is_logged_in BOOLEAN DEFAULT FALSE,
    login_username VARCHAR(100),
    login_avatar_url TEXT,
    -- Cookie存储（加密）
    cookies_data TEXT,  -- JSON格式的cookie数据
    cookies_expire_at TIMESTAMP WITH TIME ZONE,
    -- 浏览器状态存储路径
    browser_state_path VARCHAR(255),
    -- 最后活动时间
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_collect_at TIMESTAMP WITH TIME ZONE,
    -- 采集统计
    total_collected INT DEFAULT 0,
    today_collected INT DEFAULT 0,
    -- 状态
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_social_platform_auth_platform ON social_platform_auth(platform);

-- 插入默认平台配置
INSERT INTO social_platform_auth (platform, platform_name) VALUES
('xiaohongshu', '小红书'),
('douyin', '抖音'),
('bilibili', 'B站'),
('weixin_video', '微信视频号')
ON CONFLICT (platform) DO NOTHING;

-- 添加注释
COMMENT ON TABLE social_platform_auth IS '社交媒体平台登录状态管理';
COMMENT ON COLUMN social_platform_auth.cookies_data IS 'JSON格式的Cookie数据，用于维持登录状态';
COMMENT ON COLUMN social_platform_auth.browser_state_path IS 'Playwright浏览器状态文件路径';
