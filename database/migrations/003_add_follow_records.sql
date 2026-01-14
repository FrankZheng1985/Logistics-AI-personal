-- 跟进记录表迁移脚本
-- 版本: 003
-- 描述: 添加跟进记录表，用于CRM跟进管理

-- =====================================================
-- 创建枚举类型
-- =====================================================

-- 跟进类型
DO $$ BEGIN
    CREATE TYPE follow_type AS ENUM (
        'first_contact',    -- 首次联系
        'daily_follow',     -- 日常跟进
        'intent_track',     -- 意向跟踪
        'reactivate',       -- 激活沉默客户
        'promotion',        -- 促销推送
        'after_sale',       -- 售后跟进
        'other'             -- 其他
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 跟进结果
DO $$ BEGIN
    CREATE TYPE follow_result AS ENUM (
        'replied',          -- 客户已回复
        'no_reply',         -- 未回复
        'interested',       -- 表达兴趣
        'not_interested',   -- 无兴趣
        'deal_progress',    -- 成交进展
        'deal_closed',      -- 已成交
        'lost'              -- 已流失
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 跟进渠道
DO $$ BEGIN
    CREATE TYPE follow_channel AS ENUM (
        'wechat',           -- 企业微信
        'phone',            -- 电话
        'email',            -- 邮件
        'website',          -- 网站客服
        'douyin',           -- 抖音私信
        'xiaohongshu',      -- 小红书
        'system',           -- 系统自动
        'other'             -- 其他
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =====================================================
-- 创建跟进记录表
-- =====================================================

CREATE TABLE IF NOT EXISTS follow_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 关联客户
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- 跟进信息
    follow_type follow_type DEFAULT 'daily_follow',
    channel follow_channel DEFAULT 'wechat',
    
    -- 执行者
    executor_type VARCHAR(50) DEFAULT 'sales',    -- sales/follow/manual
    executor_name VARCHAR(100),                    -- 小销/小跟/张三
    
    -- 跟进内容
    content TEXT NOT NULL,                         -- 发送的消息内容
    customer_reply TEXT,                           -- 客户回复内容
    
    -- 跟进结果
    result follow_result,
    result_note TEXT,                              -- 结果备注
    
    -- 意向变化
    intent_before INTEGER DEFAULT 0,               -- 跟进前意向分
    intent_after INTEGER DEFAULT 0,                -- 跟进后意向分
    intent_level_before VARCHAR(1),                -- 跟进前等级
    intent_level_after VARCHAR(1),                 -- 跟进后等级
    
    -- 下次跟进计划
    next_follow_at TIMESTAMP WITH TIME ZONE,
    next_follow_note VARCHAR(500),
    
    -- 关联对话
    conversation_id UUID,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 创建索引
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_follow_records_customer_id ON follow_records(customer_id);
CREATE INDEX IF NOT EXISTS idx_follow_records_follow_type ON follow_records(follow_type);
CREATE INDEX IF NOT EXISTS idx_follow_records_result ON follow_records(result);
CREATE INDEX IF NOT EXISTS idx_follow_records_created_at ON follow_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_follow_records_next_follow_at ON follow_records(next_follow_at);
CREATE INDEX IF NOT EXISTS idx_follow_records_executor ON follow_records(executor_type, executor_name);

-- =====================================================
-- 创建视图：客户跟进汇总
-- =====================================================

CREATE OR REPLACE VIEW customer_follow_summary AS
SELECT 
    c.id as customer_id,
    c.name as customer_name,
    c.company,
    c.intent_level,
    c.intent_score,
    c.last_contact_at,
    COUNT(fr.id) as total_follows,
    COUNT(CASE WHEN fr.result = 'replied' THEN 1 END) as replied_count,
    COUNT(CASE WHEN fr.result = 'no_reply' THEN 1 END) as no_reply_count,
    MAX(fr.created_at) as last_follow_at,
    (
        SELECT next_follow_at 
        FROM follow_records 
        WHERE customer_id = c.id 
        AND next_follow_at > NOW()
        ORDER BY next_follow_at 
        LIMIT 1
    ) as next_scheduled_follow
FROM customers c
LEFT JOIN follow_records fr ON c.id = fr.customer_id
WHERE c.is_active = true
GROUP BY c.id, c.name, c.company, c.intent_level, c.intent_score, c.last_contact_at;

-- =====================================================
-- 创建视图：今日跟进任务
-- =====================================================

CREATE OR REPLACE VIEW today_follow_tasks AS
SELECT 
    c.id as customer_id,
    c.name as customer_name,
    c.company,
    c.phone,
    c.wechat_id,
    c.intent_level,
    c.intent_score,
    c.last_contact_at,
    c.next_follow_at,
    CASE 
        WHEN c.intent_level = 'S' THEN 1
        WHEN c.intent_level = 'A' THEN 2
        WHEN c.intent_level = 'B' THEN 3
        ELSE 4
    END as priority,
    (
        SELECT content 
        FROM conversations 
        WHERE customer_id = c.id 
        ORDER BY created_at DESC 
        LIMIT 1
    ) as last_message
FROM customers c
WHERE c.is_active = true
AND (
    -- 明确设置了今天需要跟进的
    (c.next_follow_at IS NOT NULL AND DATE(c.next_follow_at) <= CURRENT_DATE)
    OR
    -- 根据意向等级自动判断需要跟进的
    (
        c.next_follow_at IS NULL 
        AND c.last_contact_at IS NOT NULL
        AND (
            (c.intent_level = 'S' AND c.last_contact_at < NOW() - INTERVAL '1 day')
            OR (c.intent_level = 'A' AND c.last_contact_at < NOW() - INTERVAL '2 days')
            OR (c.intent_level = 'B' AND c.last_contact_at < NOW() - INTERVAL '5 days')
            OR (c.intent_level = 'C' AND c.last_contact_at < NOW() - INTERVAL '15 days')
        )
    )
)
ORDER BY priority, c.last_contact_at ASC;

-- =====================================================
-- 添加注释
-- =====================================================

COMMENT ON TABLE follow_records IS '客户跟进记录表';
COMMENT ON COLUMN follow_records.follow_type IS '跟进类型';
COMMENT ON COLUMN follow_records.channel IS '跟进渠道';
COMMENT ON COLUMN follow_records.executor_type IS '执行者类型: sales/follow/manual';
COMMENT ON COLUMN follow_records.content IS '跟进发送的内容';
COMMENT ON COLUMN follow_records.customer_reply IS '客户回复内容';
COMMENT ON COLUMN follow_records.result IS '跟进结果';
COMMENT ON COLUMN follow_records.intent_before IS '跟进前意向分数';
COMMENT ON COLUMN follow_records.intent_after IS '跟进后意向分数';

COMMENT ON VIEW customer_follow_summary IS '客户跟进汇总视图';
COMMENT ON VIEW today_follow_tasks IS '今日跟进任务视图';
