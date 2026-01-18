-- 037_add_assistant_agent.sql
-- 小助 - 个人助理AI员工相关表结构
-- 功能：日程管理、会议纪要、待办事项、多邮箱管理

-- =====================================================
-- 1. 添加新的AI员工类型
-- =====================================================

-- 先检查并添加 assistant 类型到枚举
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'assistant' AND enumtypid = 'agent_type'::regtype) THEN
        ALTER TYPE agent_type ADD VALUE 'assistant';
    END IF;
END$$;

-- 插入小助AI员工记录
INSERT INTO ai_agents (name, agent_type, description, status) VALUES
    ('小助', 'assistant', '个人助理 - 日程管理、会议纪要、邮件管理、ERP数据跟踪', 'online')
ON CONFLICT (agent_type) DO NOTHING;

-- =====================================================
-- 2. 日程管理表
-- =====================================================

CREATE TABLE IF NOT EXISTS assistant_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    location VARCHAR(200),                   -- 地点
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    all_day BOOLEAN DEFAULT FALSE,           -- 是否全天事件
    
    -- 提醒设置
    reminder_day_before BOOLEAN DEFAULT TRUE,  -- 是否提前一天提醒
    reminder_minutes INTEGER DEFAULT 15,       -- 提前多少分钟提醒（0=不提醒）
    reminder_sent_day_before BOOLEAN DEFAULT FALSE,  -- 是否已发送提前一天提醒
    reminder_sent BOOLEAN DEFAULT FALSE,       -- 是否已发送当天提醒
    
    -- 重复设置（可选）
    repeat_type VARCHAR(20),                 -- none/daily/weekly/monthly
    repeat_until TIMESTAMP WITH TIME ZONE,
    
    -- 状态
    priority VARCHAR(20) DEFAULT 'normal',   -- low/normal/high/urgent
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 日程表索引
CREATE INDEX IF NOT EXISTS idx_assistant_schedules_start_time ON assistant_schedules(start_time);
CREATE INDEX IF NOT EXISTS idx_assistant_schedules_is_completed ON assistant_schedules(is_completed);
CREATE INDEX IF NOT EXISTS idx_assistant_schedules_reminder ON assistant_schedules(reminder_sent, reminder_sent_day_before);

COMMENT ON TABLE assistant_schedules IS '小助日程管理表';
COMMENT ON COLUMN assistant_schedules.reminder_day_before IS '是否提前一天晚上8点提醒';
COMMENT ON COLUMN assistant_schedules.reminder_minutes IS '提前多少分钟提醒，0表示不提醒';

-- =====================================================
-- 3. 待办事项表
-- =====================================================

CREATE TABLE IF NOT EXISTS assistant_todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content VARCHAR(500) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',   -- low/normal/high/urgent
    due_date TIMESTAMP WITH TIME ZONE,
    
    -- 来源（可能来自会议纪要）
    source_type VARCHAR(50),                 -- manual/meeting
    source_id UUID,                          -- 关联的会议纪要ID
    
    -- 状态
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 待办表索引
CREATE INDEX IF NOT EXISTS idx_assistant_todos_is_completed ON assistant_todos(is_completed);
CREATE INDEX IF NOT EXISTS idx_assistant_todos_due_date ON assistant_todos(due_date);
CREATE INDEX IF NOT EXISTS idx_assistant_todos_priority ON assistant_todos(priority);

COMMENT ON TABLE assistant_todos IS '小助待办事项表';

-- =====================================================
-- 4. 会议纪要表
-- =====================================================

CREATE TABLE IF NOT EXISTS meeting_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES assistant_schedules(id) ON DELETE SET NULL,
    
    -- 会议信息
    title VARCHAR(200),
    meeting_time TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    participants TEXT,                       -- 参会人员
    location VARCHAR(200),
    
    -- 录音信息
    audio_file_url VARCHAR(500),             -- 录音文件URL
    audio_duration_seconds INTEGER,          -- 录音时长（秒）
    transcription_status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/failed
    
    -- 内容
    raw_transcription TEXT,                  -- 原始语音转写文本
    summary TEXT,                            -- 会议摘要（AI生成）
    content_structured JSONB,                -- 结构化会议内容
    action_items JSONB,                      -- 待办任务列表 [{assignee, task, deadline}]
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 会议纪要索引
CREATE INDEX IF NOT EXISTS idx_meeting_records_schedule_id ON meeting_records(schedule_id);
CREATE INDEX IF NOT EXISTS idx_meeting_records_meeting_time ON meeting_records(meeting_time);
CREATE INDEX IF NOT EXISTS idx_meeting_records_status ON meeting_records(transcription_status);

COMMENT ON TABLE meeting_records IS '会议纪要表';
COMMENT ON COLUMN meeting_records.action_items IS 'JSON数组格式：[{"assignee": "张总", "task": "提交报告", "deadline": "本周五"}]';

-- =====================================================
-- 5. 多邮箱账户表
-- =====================================================

CREATE TABLE IF NOT EXISTS email_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,              -- 邮箱别名（如"工作邮箱"）
    email_address VARCHAR(200) NOT NULL,     -- 邮箱地址
    provider VARCHAR(50),                    -- 邮箱服务商（qq_enterprise/aliyun/163/gmail/outlook/other）
    
    -- IMAP配置（收件）
    imap_host VARCHAR(200),
    imap_port INTEGER DEFAULT 993,
    imap_user VARCHAR(200),
    imap_password TEXT,                      -- 加密存储
    imap_ssl BOOLEAN DEFAULT TRUE,
    
    -- SMTP配置（发件）
    smtp_host VARCHAR(200),
    smtp_port INTEGER DEFAULT 465,
    smtp_user VARCHAR(200),
    smtp_password TEXT,                      -- 加密存储
    smtp_ssl BOOLEAN DEFAULT TRUE,
    
    -- 同步设置
    sync_interval_minutes INTEGER DEFAULT 5, -- 同步频率（分钟）
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_sync_error TEXT,
    sync_enabled BOOLEAN DEFAULT TRUE,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,        -- 是否为默认发件邮箱
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 邮箱账户索引
CREATE INDEX IF NOT EXISTS idx_email_accounts_is_active ON email_accounts(is_active);
CREATE INDEX IF NOT EXISTS idx_email_accounts_sync_enabled ON email_accounts(sync_enabled);
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_accounts_email ON email_accounts(email_address);

COMMENT ON TABLE email_accounts IS '多邮箱账户配置表';
COMMENT ON COLUMN email_accounts.provider IS '邮箱服务商：qq_enterprise/aliyun/163/gmail/outlook/qq/other';

-- =====================================================
-- 6. 邮件缓存表
-- =====================================================

CREATE TABLE IF NOT EXISTS email_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES email_accounts(id) ON DELETE CASCADE,
    message_id VARCHAR(500) NOT NULL,        -- 邮件唯一标识（来自邮件头）
    
    -- 邮件信息
    subject VARCHAR(500),
    from_address VARCHAR(200),
    from_name VARCHAR(200),
    to_addresses TEXT,
    cc_addresses TEXT,
    reply_to VARCHAR(200),
    
    -- 内容
    body_text TEXT,
    body_html TEXT,
    has_attachments BOOLEAN DEFAULT FALSE,
    attachment_names TEXT[],
    attachment_count INTEGER DEFAULT 0,
    
    -- 状态
    is_read BOOLEAN DEFAULT FALSE,
    is_important BOOLEAN DEFAULT FALSE,
    is_starred BOOLEAN DEFAULT FALSE,
    is_replied BOOLEAN DEFAULT FALSE,
    is_forwarded BOOLEAN DEFAULT FALSE,
    
    -- AI分类
    category VARCHAR(50),                    -- customer/internal/subscription/spam/other
    category_confidence FLOAT,               -- AI分类置信度
    ai_summary TEXT,                         -- AI生成的邮件摘要
    
    -- 时间
    received_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 邮件缓存索引
CREATE INDEX IF NOT EXISTS idx_email_cache_account_id ON email_cache(account_id);
CREATE INDEX IF NOT EXISTS idx_email_cache_received_at ON email_cache(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_cache_is_read ON email_cache(is_read);
CREATE INDEX IF NOT EXISTS idx_email_cache_category ON email_cache(category);
CREATE INDEX IF NOT EXISTS idx_email_cache_is_important ON email_cache(is_important);
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_cache_unique ON email_cache(account_id, message_id);

COMMENT ON TABLE email_cache IS '邮件缓存表 - 存储同步的邮件';
COMMENT ON COLUMN email_cache.category IS 'AI分类：customer(客户)/internal(内部)/subscription(订阅)/spam(垃圾)/other(其他)';

-- =====================================================
-- 7. 邮件操作日志表
-- =====================================================

CREATE TABLE IF NOT EXISTS email_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id UUID REFERENCES email_cache(id) ON DELETE CASCADE,
    account_id UUID REFERENCES email_accounts(id) ON DELETE CASCADE,
    
    action_type VARCHAR(50) NOT NULL,        -- read/reply/forward/delete/archive/star/mark_important
    action_data JSONB,                       -- 操作相关数据
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 邮件操作日志索引
CREATE INDEX IF NOT EXISTS idx_email_actions_email_id ON email_actions(email_id);
CREATE INDEX IF NOT EXISTS idx_email_actions_account_id ON email_actions(account_id);
CREATE INDEX IF NOT EXISTS idx_email_actions_created_at ON email_actions(created_at DESC);

COMMENT ON TABLE email_actions IS '邮件操作日志';

-- =====================================================
-- 8. 小助交互记录表
-- =====================================================

CREATE TABLE IF NOT EXISTS assistant_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,           -- 企业微信用户ID
    
    -- 消息内容
    message_type VARCHAR(50) NOT NULL,       -- text/voice/file
    content TEXT NOT NULL,                   -- 用户发送的内容
    
    -- 处理信息
    interaction_type VARCHAR(50) NOT NULL,   -- schedule/todo/meeting/email/erp/report/help/unknown
    intent_parsed JSONB,                     -- 解析出的意图
    
    -- 响应
    response TEXT,
    response_sent BOOLEAN DEFAULT FALSE,
    
    -- 关联
    related_schedule_id UUID REFERENCES assistant_schedules(id),
    related_todo_id UUID REFERENCES assistant_todos(id),
    related_meeting_id UUID REFERENCES meeting_records(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 交互记录索引
CREATE INDEX IF NOT EXISTS idx_assistant_interactions_user_id ON assistant_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_assistant_interactions_type ON assistant_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_assistant_interactions_created_at ON assistant_interactions(created_at DESC);

COMMENT ON TABLE assistant_interactions IS '小助企业微信交互记录';

-- =====================================================
-- 9. 语音转写任务表
-- =====================================================

CREATE TABLE IF NOT EXISTS speech_transcription_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 关联
    meeting_id UUID REFERENCES meeting_records(id) ON DELETE CASCADE,
    
    -- 文件信息
    audio_url VARCHAR(500) NOT NULL,         -- 音频文件URL（腾讯云COS或本地）
    audio_format VARCHAR(20),                -- mp3/m4a/wav/amr
    audio_duration_seconds INTEGER,
    
    -- 腾讯云任务信息
    tencent_task_id VARCHAR(100),            -- 腾讯云任务ID
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',    -- pending/uploading/processing/completed/failed
    progress INTEGER DEFAULT 0,              -- 处理进度 0-100
    
    -- 结果
    result_text TEXT,                        -- 转写结果
    error_message TEXT,
    
    -- 时间
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 语音转写任务索引
CREATE INDEX IF NOT EXISTS idx_speech_tasks_meeting_id ON speech_transcription_tasks(meeting_id);
CREATE INDEX IF NOT EXISTS idx_speech_tasks_status ON speech_transcription_tasks(status);

COMMENT ON TABLE speech_transcription_tasks IS '语音转写任务表';

-- =====================================================
-- 10. 触发器：自动更新 updated_at
-- =====================================================

-- 日程表触发器
DROP TRIGGER IF EXISTS update_assistant_schedules_updated_at ON assistant_schedules;
CREATE TRIGGER update_assistant_schedules_updated_at 
    BEFORE UPDATE ON assistant_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 待办表触发器
DROP TRIGGER IF EXISTS update_assistant_todos_updated_at ON assistant_todos;
CREATE TRIGGER update_assistant_todos_updated_at 
    BEFORE UPDATE ON assistant_todos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 会议纪要触发器
DROP TRIGGER IF EXISTS update_meeting_records_updated_at ON meeting_records;
CREATE TRIGGER update_meeting_records_updated_at 
    BEFORE UPDATE ON meeting_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 邮箱账户触发器
DROP TRIGGER IF EXISTS update_email_accounts_updated_at ON email_accounts;
CREATE TRIGGER update_email_accounts_updated_at 
    BEFORE UPDATE ON email_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 完成
-- =====================================================

SELECT '小助相关表结构创建完成' AS message;
