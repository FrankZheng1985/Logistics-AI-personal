-- 014_add_notifications_and_wechat_groups.sql
-- 添加通知和微信群监控表

-- 创建通知表
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL, -- high_intent, task_complete, system_alert, lead_found, video_ready
    title VARCHAR(255) NOT NULL,
    content TEXT,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    customer_name VARCHAR(100),
    is_read BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'normal', -- urgent, high, normal, low
    action_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 通知索引
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- 创建微信群表
CREATE TABLE IF NOT EXISTS wechat_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    wechat_group_id VARCHAR(100),
    member_count INTEGER DEFAULT 0,
    is_monitoring BOOLEAN DEFAULT TRUE,
    messages_today INTEGER DEFAULT 0,
    leads_found INTEGER DEFAULT 0,
    intel_count INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 微信群索引
CREATE INDEX IF NOT EXISTS idx_wechat_groups_is_monitoring ON wechat_groups(is_monitoring);

-- 创建群消息表
CREATE TABLE IF NOT EXISTS group_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES wechat_groups(id) ON DELETE CASCADE,
    sender_name VARCHAR(100),
    sender_wechat_id VARCHAR(100),
    content TEXT,
    category VARCHAR(50) DEFAULT 'irrelevant', -- lead, intel, knowledge, irrelevant
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 群消息索引
CREATE INDEX IF NOT EXISTS idx_group_messages_group_id ON group_messages(group_id);
CREATE INDEX IF NOT EXISTS idx_group_messages_category ON group_messages(category);
CREATE INDEX IF NOT EXISTS idx_group_messages_created_at ON group_messages(created_at DESC);
