-- 线索管理表迁移脚本
-- 添加leads表用于存储自动搜索到的潜在客户线索

-- 创建线索来源枚举
DO $$ BEGIN
    CREATE TYPE lead_source AS ENUM (
        'weibo', 'zhihu', 'tieba', 'google', 
        'youtube', 'facebook', 'linkedin',
        'alibaba', '1688', 'manual', 'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 创建线索状态枚举
DO $$ BEGIN
    CREATE TYPE lead_status AS ENUM (
        'new', 'contacted', 'following', 
        'converted', 'invalid', 'archived'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 创建线索意向等级枚举
DO $$ BEGIN
    CREATE TYPE lead_intent_level AS ENUM (
        'high', 'medium', 'low', 'unknown'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 创建线索表
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基本信息
    name VARCHAR(100),
    company VARCHAR(200),
    phone VARCHAR(50),
    email VARCHAR(200),
    wechat VARCHAR(100),
    
    -- 线索来源
    source lead_source DEFAULT 'other',
    source_url TEXT,
    source_content TEXT,
    content JSONB,                        -- 线索详细内容（JSON格式）
    
    -- 状态和意向
    status lead_status DEFAULT 'new',
    intent_level lead_intent_level DEFAULT 'unknown',
    intent_score INTEGER DEFAULT 0,
    
    -- AI分析结果
    ai_confidence FLOAT DEFAULT 0.0,
    ai_summary TEXT,
    ai_suggestion TEXT,
    
    -- 需求标签
    needs TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- 额外数据
    extra_data JSONB DEFAULT '{}',
    
    -- 跟进记录
    last_contact_at TIMESTAMPTZ,
    contact_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_intent_level ON leads(intent_level);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email) WHERE email IS NOT NULL;

-- 添加source_url唯一约束（用于避免重复线索）
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_source_url_unique ON leads(source_url) WHERE source_url IS NOT NULL;

-- 更新agent_type枚举，添加lead_hunter
DO $$ BEGIN
    ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'lead_hunter';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 添加更新时间触发器
CREATE OR REPLACE FUNCTION update_leads_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_leads_updated_at ON leads;
CREATE TRIGGER trigger_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_leads_updated_at();

-- 插入示例线索数据（可选）
-- INSERT INTO leads (name, company, source, source_content, intent_level, ai_summary, needs)
-- VALUES 
--     ('张先生', '深圳贸易公司', 'manual', '从展会获取的名片', 'high', '有大量FBA物流需求', ARRAY['FBA物流', '海运']),
--     ('李经理', '广州电子厂', 'google', '搜索货代服务找到', 'medium', '询问空运报价', ARRAY['空运', '清关']);

COMMENT ON TABLE leads IS '线索表 - 存储自动搜索或手动录入的潜在客户线索';
