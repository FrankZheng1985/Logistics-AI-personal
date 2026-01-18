-- 034_fix_notifications_table.sql
-- 修复 notifications 表缺失的字段

-- 添加 customer_name 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'notifications' AND column_name = 'customer_name'
    ) THEN
        ALTER TABLE notifications ADD COLUMN customer_name VARCHAR(100);
        RAISE NOTICE 'Added customer_name column to notifications table';
    END IF;
END $$;

-- 添加 priority 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'notifications' AND column_name = 'priority'
    ) THEN
        ALTER TABLE notifications ADD COLUMN priority VARCHAR(20) DEFAULT 'normal';
        RAISE NOTICE 'Added priority column to notifications table';
    END IF;
END $$;

-- 添加 action_url 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'notifications' AND column_name = 'action_url'
    ) THEN
        ALTER TABLE notifications ADD COLUMN action_url TEXT;
        RAISE NOTICE 'Added action_url column to notifications table';
    END IF;
END $$;

-- 添加索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notifications(priority);

-- 添加表注释
COMMENT ON TABLE notifications IS '通知表 - 已修复字段 (034_fix_notifications_table.sql)';
COMMENT ON COLUMN notifications.customer_name IS '客户名称（冗余存储，方便显示）';
COMMENT ON COLUMN notifications.priority IS '通知优先级: urgent/high/normal/low';
COMMENT ON COLUMN notifications.action_url IS '点击通知后跳转的URL';
