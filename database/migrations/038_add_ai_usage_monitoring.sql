-- AI用量监控模块
-- 记录大模型API调用用量和费用告警

-- =====================================================
-- 1. AI用量日志表 - 记录每次API调用
-- =====================================================
CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id SERIAL PRIMARY KEY,
    
    -- 调用信息
    agent_name VARCHAR(50),                    -- AI员工名称（小猎、小销、小析等）
    agent_id INTEGER REFERENCES ai_agents(id), -- AI员工ID（可选）
    model_name VARCHAR(100) NOT NULL,          -- 模型名称（qwen-plus, gpt-4等）
    provider VARCHAR(50) NOT NULL,             -- 提供商（dashscope, openai, anthropic）
    
    -- Token统计
    input_tokens INTEGER NOT NULL DEFAULT 0,   -- 输入token数
    output_tokens INTEGER NOT NULL DEFAULT 0,  -- 输出token数
    total_tokens INTEGER NOT NULL DEFAULT 0,   -- 总token数
    
    -- 费用估算（单位：元）
    cost_estimate DECIMAL(10, 6) NOT NULL DEFAULT 0, -- 估算费用
    
    -- 请求信息
    task_type VARCHAR(100),                    -- 任务类型（chat, analysis, content_generation等）
    request_id VARCHAR(100),                   -- 请求ID（用于追踪）
    
    -- 性能指标
    response_time_ms INTEGER,                  -- 响应时间（毫秒）
    is_success BOOLEAN DEFAULT TRUE,           -- 是否成功
    error_message TEXT,                        -- 错误信息（如果失败）
    
    -- 元数据
    extra_data JSONB DEFAULT '{}',             -- 额外数据
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化查询
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created_at ON ai_usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_agent_name ON ai_usage_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_model_name ON ai_usage_logs(model_name);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_provider ON ai_usage_logs(provider);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_task_type ON ai_usage_logs(task_type);

-- =====================================================
-- 2. AI费用告警配置表
-- =====================================================
CREATE TABLE IF NOT EXISTS ai_usage_alerts (
    id SERIAL PRIMARY KEY,
    
    -- 告警配置
    alert_name VARCHAR(100) NOT NULL,          -- 告警名称
    alert_type VARCHAR(20) NOT NULL,           -- 告警类型: daily, weekly, monthly, total
    threshold_amount DECIMAL(10, 2) NOT NULL,  -- 阈值金额（元）
    threshold_tokens INTEGER,                  -- 阈值token数（可选）
    
    -- 通知配置
    notify_wechat BOOLEAN DEFAULT TRUE,        -- 是否企业微信通知
    notify_email BOOLEAN DEFAULT FALSE,        -- 是否邮件通知
    notify_users TEXT,                         -- 通知用户列表（逗号分隔）
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,            -- 是否启用
    last_triggered_at TIMESTAMP WITH TIME ZONE, -- 上次触发时间
    trigger_count INTEGER DEFAULT 0,           -- 触发次数
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 3. AI用量统计汇总表（按天汇总，提高查询性能）
-- =====================================================
CREATE TABLE IF NOT EXISTS ai_usage_daily_stats (
    id SERIAL PRIMARY KEY,
    
    -- 统计维度
    stat_date DATE NOT NULL,                   -- 统计日期
    agent_name VARCHAR(50),                    -- AI员工名称
    model_name VARCHAR(100),                   -- 模型名称
    provider VARCHAR(50),                      -- 提供商
    
    -- 汇总数据
    request_count INTEGER DEFAULT 0,           -- 请求次数
    success_count INTEGER DEFAULT 0,           -- 成功次数
    error_count INTEGER DEFAULT 0,             -- 失败次数
    
    -- Token统计
    total_input_tokens BIGINT DEFAULT 0,       -- 总输入token
    total_output_tokens BIGINT DEFAULT 0,      -- 总输出token
    total_tokens BIGINT DEFAULT 0,             -- 总token
    
    -- 费用统计
    total_cost DECIMAL(12, 4) DEFAULT 0,       -- 总费用
    
    -- 性能统计
    avg_response_time_ms INTEGER,              -- 平均响应时间
    max_response_time_ms INTEGER,              -- 最大响应时间
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束：每天每个维度只有一条记录
    UNIQUE(stat_date, agent_name, model_name, provider)
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_stats_date ON ai_usage_daily_stats(stat_date);
CREATE INDEX IF NOT EXISTS idx_ai_usage_daily_stats_agent ON ai_usage_daily_stats(agent_name);

-- =====================================================
-- 4. 模型价格配置表
-- =====================================================
CREATE TABLE IF NOT EXISTS ai_model_pricing (
    id SERIAL PRIMARY KEY,
    
    -- 模型信息
    provider VARCHAR(50) NOT NULL,             -- 提供商
    model_name VARCHAR(100) NOT NULL,          -- 模型名称
    display_name VARCHAR(100),                 -- 显示名称
    
    -- 价格配置（单位：元/1000 tokens）
    input_price_per_1k DECIMAL(10, 6) NOT NULL,  -- 输入价格
    output_price_per_1k DECIMAL(10, 6) NOT NULL, -- 输出价格
    
    -- 描述
    description TEXT,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(provider, model_name)
);

-- 插入默认模型价格（阿里云通义千问）
INSERT INTO ai_model_pricing (provider, model_name, display_name, input_price_per_1k, output_price_per_1k, description)
VALUES 
    -- 通义千问系列（价格参考阿里云官网 2024年）
    ('dashscope', 'qwen-turbo', '通义千问-Turbo', 0.002, 0.006, '高性价比，适合简单任务'),
    ('dashscope', 'qwen-plus', '通义千问-Plus', 0.004, 0.012, '均衡型，推荐日常使用'),
    ('dashscope', 'qwen-max', '通义千问-Max', 0.02, 0.06, '最强性能，复杂任务'),
    ('dashscope', 'qwen-long', '通义千问-Long', 0.0005, 0.002, '长文本处理'),
    
    -- OpenAI系列（价格参考OpenAI官网 2024年，单位已转换为人民币，汇率约7.2）
    ('openai', 'gpt-4-turbo-preview', 'GPT-4 Turbo', 0.072, 0.216, '最强GPT-4模型'),
    ('openai', 'gpt-4', 'GPT-4', 0.216, 0.432, 'GPT-4标准版'),
    ('openai', 'gpt-3.5-turbo', 'GPT-3.5 Turbo', 0.0036, 0.0108, '高性价比'),
    
    -- Anthropic Claude系列（价格参考Anthropic官网 2024年，单位已转换为人民币）
    ('anthropic', 'claude-3-opus-20240229', 'Claude 3 Opus', 0.108, 0.54, '最强Claude模型'),
    ('anthropic', 'claude-3-sonnet-20240229', 'Claude 3 Sonnet', 0.0216, 0.108, '均衡型Claude'),
    ('anthropic', 'claude-3-haiku-20240307', 'Claude 3 Haiku', 0.0018, 0.009, '轻量级Claude'),
    
    -- DeepSeek系列
    ('deepseek', 'deepseek-chat', 'DeepSeek Chat', 0.001, 0.002, '高性价比国产模型'),
    ('deepseek', 'deepseek-coder', 'DeepSeek Coder', 0.001, 0.002, '代码专用模型')
ON CONFLICT (provider, model_name) DO NOTHING;

-- 插入默认告警配置
INSERT INTO ai_usage_alerts (alert_name, alert_type, threshold_amount, notify_wechat, notify_email, is_active)
VALUES 
    ('每日费用告警', 'daily', 50.00, TRUE, FALSE, TRUE),
    ('每周费用告警', 'weekly', 200.00, TRUE, FALSE, TRUE),
    ('每月费用告警', 'monthly', 500.00, TRUE, TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- 添加注释
COMMENT ON TABLE ai_usage_logs IS 'AI大模型API调用用量日志';
COMMENT ON TABLE ai_usage_alerts IS 'AI用量费用告警配置';
COMMENT ON TABLE ai_usage_daily_stats IS 'AI用量每日统计汇总';
COMMENT ON TABLE ai_model_pricing IS 'AI模型价格配置';
