-- 添加内容发布相关字段
-- 用于支持文案的审核和自动发布功能

-- 添加发布时间字段
ALTER TABLE content_posts 
ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- 添加发布渠道字段
ALTER TABLE content_posts 
ADD COLUMN IF NOT EXISTS published_channels TEXT[];

-- 添加更新时间字段
ALTER TABLE content_posts 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- 更新状态枚举，添加 approved 和 rejected 状态
-- 注意：PostgreSQL 枚举类型需要特殊处理
DO $$
BEGIN
    -- 检查是否存在 content_status 枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_status') THEN
        CREATE TYPE content_status AS ENUM ('draft', 'approved', 'rejected', 'published');
    ELSE
        -- 添加新的枚举值（如果不存在）
        BEGIN
            ALTER TYPE content_status ADD VALUE IF NOT EXISTS 'approved';
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END;
        BEGIN
            ALTER TYPE content_status ADD VALUE IF NOT EXISTS 'rejected';
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END;
    END IF;
END$$;

-- 如果 status 列是 varchar 类型，先修改为支持新状态
-- 这里假设 status 已经是 varchar 类型，不需要修改类型

-- 添加索引优化查询
CREATE INDEX IF NOT EXISTS idx_content_posts_status ON content_posts(status);
CREATE INDEX IF NOT EXISTS idx_content_posts_published_at ON content_posts(published_at);

-- 添加注释
COMMENT ON COLUMN content_posts.published_at IS '发布时间';
COMMENT ON COLUMN content_posts.published_channels IS '发布渠道列表';
COMMENT ON COLUMN content_posts.updated_at IS '更新时间';
