-- 012: 添加营销序列表
-- 创建日期: 2026-01-15
-- 说明: 用于存储自动化邮件营销序列

-- 营销序列表
CREATE TABLE IF NOT EXISTS marketing_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(100) NOT NULL,  -- 触发类型: first_inquiry, no_reply_3d, inactive_30d, manual
    trigger_condition JSONB DEFAULT '{}',  -- 触发条件详情
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, paused
    email_count INTEGER DEFAULT 0,  -- 邮件数量
    enrolled_count INTEGER DEFAULT 0,  -- 已触达人数
    converted_count INTEGER DEFAULT 0,  -- 已转化人数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 序列邮件表
CREATE TABLE IF NOT EXISTS sequence_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID REFERENCES marketing_sequences(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,  -- 邮件顺序
    subject VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    delay_days INTEGER DEFAULT 0,  -- 延迟天数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 序列执行记录表
CREATE TABLE IF NOT EXISTS sequence_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID REFERENCES marketing_sequences(id) ON DELETE CASCADE,
    customer_id UUID,  -- 关联客户
    email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, unsubscribed
    current_step INTEGER DEFAULT 0,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    converted BOOLEAN DEFAULT FALSE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sequences_status ON marketing_sequences(status);
CREATE INDEX IF NOT EXISTS idx_sequence_emails_sequence ON sequence_emails(sequence_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_sequence ON sequence_enrollments(sequence_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_status ON sequence_enrollments(status);

-- 添加注释
COMMENT ON TABLE marketing_sequences IS '营销序列配置表';
COMMENT ON TABLE sequence_emails IS '序列邮件内容表';
COMMENT ON TABLE sequence_enrollments IS '序列执行记录表';
