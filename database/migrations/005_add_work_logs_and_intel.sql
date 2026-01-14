-- ================================================
-- 迁移005: 添加工作日志、市场情报、知识库相关表
-- 用于支持AI员工24小时自动化工作系统
-- ================================================

-- 1. AI员工工作日志表
CREATE TABLE IF NOT EXISTS agent_work_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,               -- 员工类型: lead_hunter, analyst, etc.
    agent_name VARCHAR(50) NOT NULL,               -- 员工名称: 小猎, 小析, etc.
    task_type VARCHAR(100) NOT NULL,               -- 任务类型
    task_description TEXT,                          -- 任务描述
    status VARCHAR(20) DEFAULT 'pending',          -- 状态: pending, running, success, failed
    input_data JSONB,                              -- 输入数据
    output_data JSONB,                             -- 输出数据
    error_message TEXT,                            -- 错误信息
    started_at TIMESTAMP WITH TIME ZONE,           -- 开始时间
    completed_at TIMESTAMP WITH TIME ZONE,         -- 完成时间
    duration_ms INTEGER,                           -- 执行时长(毫秒)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agent_work_logs_agent ON agent_work_logs(agent_type);
CREATE INDEX idx_agent_work_logs_created ON agent_work_logs(created_at);
CREATE INDEX idx_agent_work_logs_status ON agent_work_logs(status);

-- 2. 市场情报表
CREATE TABLE IF NOT EXISTS market_intel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,                   -- 情报标题
    content TEXT,                                  -- 情报内容
    source VARCHAR(100),                           -- 来源: google_search, google_news, etc.
    url VARCHAR(1000) UNIQUE,                      -- 原始链接
    intel_type VARCHAR(50) DEFAULT 'news',         -- 类型: news, price, policy, competitor, urgent
    is_urgent BOOLEAN DEFAULT FALSE,               -- 是否紧急
    relevance_score INTEGER DEFAULT 50,            -- 相关性评分(0-100)
    knowledge_extracted BOOLEAN DEFAULT FALSE,     -- 是否已提取到知识库
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_market_intel_type ON market_intel(intel_type);
CREATE INDEX idx_market_intel_created ON market_intel(created_at);
CREATE INDEX idx_market_intel_urgent ON market_intel(is_urgent) WHERE is_urgent = TRUE;

-- 3. 知识库表
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,                         -- 知识内容
    knowledge_type VARCHAR(50) NOT NULL,           -- 类型: clearance_exp, price_ref, policy, faq, pain_point, market_intel
    source VARCHAR(100),                           -- 来源: wechat_group, market_intel, manual
    source_id VARCHAR(100),                        -- 来源记录ID
    tags TEXT[],                                   -- 标签
    usage_count INTEGER DEFAULT 0,                 -- 使用次数
    is_verified BOOLEAN DEFAULT FALSE,             -- 是否经过验证
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_knowledge_type ON knowledge_base(knowledge_type);
CREATE INDEX idx_knowledge_tags ON knowledge_base USING GIN(tags);

-- 4. 微信群配置表
CREATE TABLE IF NOT EXISTS wechat_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id VARCHAR(100) UNIQUE NOT NULL,         -- 微信群ID
    group_name VARCHAR(200),                       -- 群名称
    group_type VARCHAR(50),                        -- 群类型: logistics, freight, trade, ecommerce, clearance
    is_monitored BOOLEAN DEFAULT TRUE,             -- 是否监控
    keywords TEXT[],                               -- 关注关键词
    last_message_at TIMESTAMP WITH TIME ZONE,      -- 最后消息时间
    message_count INTEGER DEFAULT 0,               -- 消息计数
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. 微信群消息表
CREATE TABLE IF NOT EXISTS wechat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id VARCHAR(100) NOT NULL,                -- 微信群ID
    sender_id VARCHAR(100),                        -- 发送者ID
    sender_name VARCHAR(200),                      -- 发送者名称
    content TEXT,                                  -- 消息内容
    message_type VARCHAR(20) DEFAULT 'text',       -- 消息类型: text, image, file
    is_valuable BOOLEAN DEFAULT FALSE,             -- 是否有价值
    analysis_result JSONB,                         -- AI分析结果
    knowledge_extracted BOOLEAN DEFAULT FALSE,     -- 是否已提取到知识库
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_wechat_messages_group ON wechat_messages(group_id);
CREATE INDEX idx_wechat_messages_created ON wechat_messages(created_at);
CREATE INDEX idx_wechat_messages_valuable ON wechat_messages(is_valuable) WHERE is_valuable = TRUE;

-- 6. 内容发布记录表
CREATE TABLE IF NOT EXISTS content_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,                         -- 发布内容
    topic VARCHAR(200),                            -- 主题
    platform VARCHAR(50) NOT NULL,                 -- 平台: wechat_moments, weibo, xiaohongshu, etc.
    status VARCHAR(20) DEFAULT 'draft',            -- 状态: draft, published, scheduled
    scheduled_at TIMESTAMP WITH TIME ZONE,         -- 计划发布时间
    published_at TIMESTAMP WITH TIME ZONE,         -- 实际发布时间
    engagement_data JSONB,                         -- 互动数据(点赞、评论等)
    created_by VARCHAR(50),                        -- 创建者(AI员工)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_posts_platform ON content_posts(platform);
CREATE INDEX idx_content_posts_status ON content_posts(status);

-- 7. 任务队列表
CREATE TABLE IF NOT EXISTS task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL,               -- 任务类型
    task_data JSONB,                               -- 任务数据
    priority INTEGER DEFAULT 5,                    -- 优先级(1-10, 10最高)
    status VARCHAR(20) DEFAULT 'pending',          -- 状态: pending, processing, completed, failed
    retry_count INTEGER DEFAULT 0,                 -- 重试次数
    max_retries INTEGER DEFAULT 3,                 -- 最大重试次数
    assigned_to VARCHAR(50),                       -- 分配给哪个AI员工
    error_message TEXT,                            -- 错误信息
    scheduled_at TIMESTAMP WITH TIME ZONE,         -- 计划执行时间
    started_at TIMESTAMP WITH TIME ZONE,           -- 开始执行时间
    completed_at TIMESTAMP WITH TIME ZONE,         -- 完成时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_task_queue_status ON task_queue(status);
CREATE INDEX idx_task_queue_priority ON task_queue(priority DESC);
CREATE INDEX idx_task_queue_scheduled ON task_queue(scheduled_at) WHERE status = 'pending';

-- 8. 营销序列配置表
CREATE TABLE IF NOT EXISTS marketing_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,                    -- 序列名称
    description TEXT,                              -- 描述
    trigger_event VARCHAR(100) NOT NULL,           -- 触发事件: new_lead, no_reply, quote_sent, etc.
    sequence_steps JSONB NOT NULL,                 -- 序列步骤(JSON数组)
    is_active BOOLEAN DEFAULT TRUE,                -- 是否激活
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. 营销序列执行记录表
CREATE TABLE IF NOT EXISTS marketing_sequence_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID REFERENCES marketing_sequences(id),
    customer_id UUID,                              -- 客户ID
    lead_id UUID,                                  -- 线索ID
    current_step INTEGER DEFAULT 0,                -- 当前步骤
    status VARCHAR(20) DEFAULT 'active',           -- 状态: active, paused, completed, cancelled
    next_action_at TIMESTAMP WITH TIME ZONE,       -- 下次动作时间
    executed_steps JSONB,                          -- 已执行步骤记录
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_marketing_logs_customer ON marketing_sequence_logs(customer_id);
CREATE INDEX idx_marketing_logs_status ON marketing_sequence_logs(status);
CREATE INDEX idx_marketing_logs_next ON marketing_sequence_logs(next_action_at) WHERE status = 'active';

-- 10. 修改customers表，添加时区和免打扰字段
ALTER TABLE customers ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Asia/Shanghai';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS dnd_start TIME DEFAULT '22:00';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS dnd_end TIME DEFAULT '08:00';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS dnd_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS source_channel VARCHAR(50);

-- 11. 修改leads表，添加时区和质量评分字段
ALTER TABLE leads ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS timezone VARCHAR(50);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS quality_score INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_channel VARCHAR(50);

-- 12. 添加通知表的优先级字段
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';

-- 13. 添加videos表的created_by字段
ALTER TABLE videos ADD COLUMN IF NOT EXISTS created_by VARCHAR(50);

-- 14. 更新ai_agents表，添加更多统计字段
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS tasks_completed_today INTEGER DEFAULT 0;
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS tasks_completed_total INTEGER DEFAULT 0;
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS success_rate DECIMAL(5,2) DEFAULT 0;
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS avg_task_duration_ms INTEGER DEFAULT 0;

-- 添加注释
COMMENT ON TABLE agent_work_logs IS 'AI员工工作日志';
COMMENT ON TABLE market_intel IS '市场情报存储';
COMMENT ON TABLE knowledge_base IS 'AI员工共享知识库';
COMMENT ON TABLE wechat_groups IS '微信群配置(小析2监控)';
COMMENT ON TABLE wechat_messages IS '微信群消息记录';
COMMENT ON TABLE content_posts IS '内容发布记录';
COMMENT ON TABLE task_queue IS '任务队列';
COMMENT ON TABLE marketing_sequences IS '营销序列配置';
COMMENT ON TABLE marketing_sequence_logs IS '营销序列执行记录';
