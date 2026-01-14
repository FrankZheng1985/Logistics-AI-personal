-- 物流获客AI系统 - 数据库初始化脚本
-- PostgreSQL 15+

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- =====================================================
-- 枚举类型定义
-- =====================================================

-- 客户意向等级
CREATE TYPE intent_level AS ENUM ('S', 'A', 'B', 'C');

-- 客户来源渠道
CREATE TYPE customer_source AS ENUM ('wechat', 'website', 'referral', 'ad', 'other');

-- AI员工类型
CREATE TYPE agent_type AS ENUM ('coordinator', 'video_creator', 'copywriter', 'sales', 'follow', 'analyst', 'lead_hunter');

-- AI员工状态
CREATE TYPE agent_status AS ENUM ('online', 'busy', 'offline');

-- 任务状态
CREATE TYPE task_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');

-- 消息类型
CREATE TYPE message_type AS ENUM ('inbound', 'outbound');

-- 视频状态
CREATE TYPE video_status AS ENUM ('draft', 'generating', 'completed', 'failed');

-- =====================================================
-- 核心表结构
-- =====================================================

-- 系统用户表（管理员）
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI员工表
CREATE TABLE ai_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(20) NOT NULL UNIQUE,    -- 小调、小视、小文等（唯一）
    agent_type agent_type NOT NULL UNIQUE, -- 员工类型（唯一，防止重复）
    description TEXT,
    avatar_url VARCHAR(500),
    status agent_status DEFAULT 'online',
    current_task_id UUID,                -- 当前正在处理的任务
    tasks_completed_today INTEGER DEFAULT 0,
    total_tasks_completed INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}',           -- Agent配置参数
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 客户表
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 基本信息
    name VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    wechat_id VARCHAR(100),              -- 微信号
    wechat_open_id VARCHAR(100),         -- 微信OpenID
    company VARCHAR(200),                 -- 公司名称
    
    -- 来源追踪
    source customer_source DEFAULT 'other',
    source_detail VARCHAR(200),          -- 来源详情（如广告ID）
    
    -- 意向评估
    intent_score INTEGER DEFAULT 0,      -- 意向分数 0-100+
    intent_level intent_level DEFAULT 'C',
    tags VARCHAR(50)[] DEFAULT '{}',     -- 客户标签
    
    -- 业务信息
    cargo_types VARCHAR(100)[],          -- 货物类型
    routes VARCHAR(100)[],               -- 关注航线
    estimated_volume VARCHAR(50),        -- 预估货量
    
    -- 跟进状态
    assigned_to UUID REFERENCES users(id),  -- 分配给哪个销售
    last_contact_at TIMESTAMP WITH TIME ZONE,
    next_follow_at TIMESTAMP WITH TIME ZONE,
    follow_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引优化字段
    is_active BOOLEAN DEFAULT true
);

-- 对话记录表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- 对话信息
    session_id VARCHAR(100),             -- 会话ID，用于追踪多轮对话
    agent_type agent_type NOT NULL,      -- 哪个AI员工处理的
    message_type message_type NOT NULL,  -- 收到/发出
    content TEXT NOT NULL,               -- 消息内容
    
    -- 意向分析
    intent_delta INTEGER DEFAULT 0,      -- 本轮意向变化
    intent_signals JSONB DEFAULT '{}',   -- 识别到的意向信号
    
    -- 元数据
    metadata JSONB DEFAULT '{}',         -- 其他元数据
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI任务表
CREATE TABLE ai_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 任务信息
    task_type VARCHAR(50) NOT NULL,      -- video, copy, chat, analysis, follow
    agent_type agent_type NOT NULL,
    status task_status DEFAULT 'pending',
    priority INTEGER DEFAULT 5,          -- 1-10，数字越小优先级越高
    
    -- 关联
    customer_id UUID REFERENCES customers(id),
    parent_task_id UUID REFERENCES ai_tasks(id),  -- 父任务（用于任务分解）
    
    -- 输入输出
    input_data JSONB NOT NULL DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_message TEXT,
    
    -- 执行信息
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 视频表
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 基本信息
    title VARCHAR(200) NOT NULL,
    description TEXT,
    video_type VARCHAR(50),              -- ad, intro, route, warehouse等
    
    -- 内容
    script TEXT,                         -- 视频脚本
    keywords VARCHAR(50)[],              -- 关键词
    
    -- 文件信息
    video_url VARCHAR(500),              -- 视频URL（腾讯云COS）
    thumbnail_url VARCHAR(500),          -- 缩略图URL
    duration INTEGER,                    -- 视频时长（秒）
    file_size BIGINT,                    -- 文件大小（字节）
    
    -- 状态
    status video_status DEFAULT 'draft',
    
    -- 关联
    task_id UUID REFERENCES ai_tasks(id),
    created_by UUID REFERENCES users(id),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 文案表
CREATE TABLE copies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 基本信息
    title VARCHAR(200),
    copy_type VARCHAR(50) NOT NULL,      -- ad, moments, script, email等
    content TEXT NOT NULL,
    
    -- 关联
    task_id UUID REFERENCES ai_tasks(id),
    video_id UUID REFERENCES videos(id),
    
    -- 元数据
    keywords VARCHAR(50)[],
    target_audience VARCHAR(100),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 通知表
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 通知信息
    user_id UUID REFERENCES users(id),
    type VARCHAR(50) NOT NULL,           -- high_intent, task_complete, system等
    title VARCHAR(200) NOT NULL,
    content TEXT,
    
    -- 关联
    customer_id UUID REFERENCES customers(id),
    task_id UUID REFERENCES ai_tasks(id),
    
    -- 状态
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 系统配置表
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 公司配置表
CREATE TABLE company_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 公司基本信息
    company_name VARCHAR(200) DEFAULT '',
    company_intro TEXT,
    contact_phone VARCHAR(50),
    contact_email VARCHAR(100),
    contact_wechat VARCHAR(100),
    address VARCHAR(500),
    
    -- 产品与服务 (JSON格式存储)
    -- 格式: [{"name": "海运整柜", "description": "...", "features": ["..."]}]
    products JSONB DEFAULT '[]',
    
    -- 服务区域/航线
    -- 格式: [{"from_location": "中国", "to_location": "美国", "time": "25-30天", "price_ref": "...", "transport": "海运"}]
    service_routes JSONB DEFAULT '[]',
    
    -- 公司优势
    -- 格式: ["价格优惠", "时效快", "服务好"]
    advantages TEXT[] DEFAULT '{}',
    
    -- 常见FAQ
    -- 格式: [{"question": "...", "answer": "..."}]
    faq JSONB DEFAULT '[]',
    
    -- 价格参考说明
    price_policy TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 索引创建
-- =====================================================

-- 客户表索引
CREATE INDEX idx_customers_intent_level ON customers(intent_level);
CREATE INDEX idx_customers_intent_score ON customers(intent_score DESC);
CREATE INDEX idx_customers_source ON customers(source);
CREATE INDEX idx_customers_created_at ON customers(created_at DESC);
CREATE INDEX idx_customers_wechat_id ON customers(wechat_id);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_name_trgm ON customers USING gin(name gin_trgm_ops);

-- 对话记录索引
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_agent_type ON conversations(agent_type);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);

-- AI任务索引
CREATE INDEX idx_ai_tasks_status ON ai_tasks(status);
CREATE INDEX idx_ai_tasks_agent_type ON ai_tasks(agent_type);
CREATE INDEX idx_ai_tasks_priority ON ai_tasks(priority, created_at);
CREATE INDEX idx_ai_tasks_customer_id ON ai_tasks(customer_id);

-- 视频索引
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);

-- 通知索引
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- =====================================================
-- 触发器函数
-- =====================================================

-- 自动更新 updated_at 时间戳
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_tasks_updated_at BEFORE UPDATE ON ai_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_agents_updated_at BEFORE UPDATE ON ai_agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON system_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_company_config_updated_at BEFORE UPDATE ON company_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 客户意向等级自动计算
CREATE OR REPLACE FUNCTION calculate_intent_level()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.intent_score >= 80 THEN
        NEW.intent_level = 'S';
    ELSIF NEW.intent_score >= 60 THEN
        NEW.intent_level = 'A';
    ELSIF NEW.intent_score >= 30 THEN
        NEW.intent_level = 'B';
    ELSE
        NEW.intent_level = 'C';
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER calculate_customer_intent_level 
    BEFORE INSERT OR UPDATE OF intent_score ON customers
    FOR EACH ROW EXECUTE FUNCTION calculate_intent_level();

-- =====================================================
-- 初始化数据
-- =====================================================

-- 插入AI员工（使用ON CONFLICT防止重复插入）
INSERT INTO ai_agents (name, agent_type, description, status) VALUES
    ('小调', 'coordinator', 'AI调度主管 - 负责任务分配、流程协调、异常处理', 'online'),
    ('小视', 'video_creator', '视频创作员 - 生成物流广告视频、产品展示视频', 'online'),
    ('小文', 'copywriter', '文案策划 - 广告文案、朋友圈文案、视频脚本', 'online'),
    ('小销', 'sales', '销售客服 - 首次接待、解答咨询、收集需求', 'online'),
    ('小跟', 'follow', '跟进专员 - 老客户维护、意向客户跟进、促成转化', 'online'),
    ('小析', 'analyst', '客户分析师 - 意向评分、客户画像、数据报表', 'online'),
    ('小猎', 'lead_hunter', '线索猎手 - 自动搜索互联网上的潜在客户线索，发现物流需求商机', 'online')
ON CONFLICT (agent_type) DO NOTHING;

-- 插入默认系统配置
INSERT INTO system_configs (config_key, config_value, description) VALUES
    ('intent_scoring', '{
        "ask_price": 25,
        "provide_cargo_info": 20,
        "ask_transit_time": 15,
        "multiple_interactions": 30,
        "leave_contact": 50,
        "express_interest": 40,
        "just_asking": -10
    }', '客户意向评分规则'),
    ('ai_model_config', '{
        "primary_model": "claude-3-opus",
        "fallback_model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000
    }', 'AI模型配置'),
    ('notification_settings', '{
        "high_intent_threshold": 60,
        "notify_methods": ["wechat", "system"],
        "quiet_hours": {"start": "22:00", "end": "08:00"}
    }', '通知设置');

-- 创建默认管理员用户（密码需要在应用中hash）
INSERT INTO users (username, email, password_hash, full_name, is_admin) VALUES
    ('admin', 'admin@logistics-ai.com', '$2b$12$placeholder_hash_replace_me', '系统管理员', true);

-- =====================================================
-- 视图创建
-- =====================================================

-- 今日统计视图
CREATE VIEW daily_stats AS
SELECT 
    DATE(CURRENT_TIMESTAMP) as stat_date,
    (SELECT COUNT(*) FROM customers WHERE DATE(created_at) = DATE(CURRENT_TIMESTAMP)) as new_customers_today,
    (SELECT COUNT(*) FROM customers WHERE intent_level IN ('S', 'A') AND DATE(updated_at) = DATE(CURRENT_TIMESTAMP)) as high_intent_today,
    (SELECT COUNT(*) FROM conversations WHERE DATE(created_at) = DATE(CURRENT_TIMESTAMP)) as conversations_today,
    (SELECT COUNT(*) FROM videos WHERE DATE(created_at) = DATE(CURRENT_TIMESTAMP)) as videos_today,
    (SELECT COUNT(*) FROM ai_tasks WHERE status = 'completed' AND DATE(completed_at) = DATE(CURRENT_TIMESTAMP)) as tasks_completed_today;

-- 客户详情视图（包含最近对话）
CREATE VIEW customer_details AS
SELECT 
    c.*,
    (SELECT COUNT(*) FROM conversations WHERE customer_id = c.id) as total_conversations,
    (SELECT content FROM conversations WHERE customer_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message,
    (SELECT created_at FROM conversations WHERE customer_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message_at
FROM customers c;

COMMENT ON TABLE customers IS '客户信息表';
COMMENT ON TABLE conversations IS '对话记录表';
COMMENT ON TABLE ai_tasks IS 'AI任务表';
COMMENT ON TABLE videos IS '视频表';
COMMENT ON TABLE ai_agents IS 'AI员工表';
