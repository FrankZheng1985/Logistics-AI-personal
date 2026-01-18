-- 迁移035: 添加小欧间谍（欧洲海关监控员）AI员工
-- 2026-01-18

-- =====================================================
-- 步骤1：添加 eu_customs_monitor 到 agent_type 枚举
-- =====================================================

DO $$
BEGIN
    -- 尝试添加新的枚举值
    ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'eu_customs_monitor';
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'eu_customs_monitor already exists in agent_type enum';
END $$;

-- =====================================================
-- 步骤2：插入小欧间谍 AI员工
-- =====================================================

INSERT INTO ai_agents (name, agent_type, description, status)
SELECT '小欧间谍', 'eu_customs_monitor'::agent_type, 
       '欧洲海关监控员 - 每天监控欧洲海关新闻，关注反倾销、关税调整、进口政策等', 
       'online'
WHERE NOT EXISTS (
    SELECT 1 FROM ai_agents WHERE name = '小欧间谍' OR agent_type = 'eu_customs_monitor'
);

-- =====================================================
-- 步骤3：创建欧洲海关新闻表
-- =====================================================

CREATE TABLE IF NOT EXISTS eu_customs_news (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 新闻基本信息
    title VARCHAR(500) NOT NULL,           -- 原始标题
    title_cn VARCHAR(500),                 -- 中文标题
    content TEXT,                          -- 原始内容
    summary_cn TEXT,                       -- 中文摘要
    url VARCHAR(1000) NOT NULL,            -- 新闻URL
    url_hash VARCHAR(32) UNIQUE NOT NULL,  -- URL的MD5哈希（用于去重）
    
    -- 来源信息
    source_id VARCHAR(50),                 -- 来源ID（eu_official, china_mofcom等）
    source_name VARCHAR(100),              -- 来源名称
    keyword VARCHAR(200),                  -- 搜索关键词
    
    -- 分类和重要性
    news_type VARCHAR(50),                 -- 新闻类型：政策变化/反倾销/关税调整/执法行动/行业动态
    importance_score INTEGER DEFAULT 0,    -- 重要性评分 0-100
    is_important BOOLEAN DEFAULT false,    -- 是否重要
    urgency VARCHAR(20) DEFAULT '一般',    -- 紧急程度：紧急/重要/一般
    
    -- AI分析结果
    affected_countries TEXT[] DEFAULT '{}', -- 涉及国家
    affected_products TEXT[] DEFAULT '{}',  -- 涉及商品类别
    impact_analysis TEXT,                   -- 影响分析
    business_suggestion TEXT,               -- 业务建议
    
    -- 通知状态
    is_notified BOOLEAN DEFAULT false,      -- 是否已发送通知
    notified_at TIMESTAMP WITH TIME ZONE,   -- 通知时间
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_eu_customs_news_url_hash ON eu_customs_news(url_hash);
CREATE INDEX IF NOT EXISTS idx_eu_customs_news_created_at ON eu_customs_news(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_eu_customs_news_is_important ON eu_customs_news(is_important);
CREATE INDEX IF NOT EXISTS idx_eu_customs_news_news_type ON eu_customs_news(news_type);
CREATE INDEX IF NOT EXISTS idx_eu_customs_news_importance_score ON eu_customs_news(importance_score DESC);

-- 添加更新时间触发器
DROP TRIGGER IF EXISTS update_eu_customs_news_updated_at ON eu_customs_news;
CREATE TRIGGER update_eu_customs_news_updated_at 
    BEFORE UPDATE ON eu_customs_news
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 步骤4：创建监控统计表（可选，用于追踪监控效果）
-- =====================================================

CREATE TABLE IF NOT EXISTS eu_customs_monitor_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stat_date DATE NOT NULL UNIQUE,
    total_news INTEGER DEFAULT 0,           -- 当日采集新闻数
    important_news INTEGER DEFAULT 0,       -- 重要新闻数
    notifications_sent INTEGER DEFAULT 0,   -- 发送通知数
    avg_importance_score DECIMAL(5,2),      -- 平均重要性评分
    sources_searched TEXT[] DEFAULT '{}',   -- 搜索的来源
    keywords_used TEXT[] DEFAULT '{}',      -- 使用的关键词
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eu_customs_monitor_stats_date ON eu_customs_monitor_stats(stat_date DESC);

-- =====================================================
-- 验证结果
-- =====================================================

DO $$
DECLARE
    agent_count INTEGER;
    table_exists BOOLEAN;
BEGIN
    -- 检查AI员工是否添加成功
    SELECT COUNT(*) INTO agent_count FROM ai_agents WHERE name = '小欧间谍';
    IF agent_count > 0 THEN
        RAISE NOTICE '✅ 小欧间谍（欧洲海关监控员）已成功添加到AI员工表';
    ELSE
        RAISE WARNING '⚠️ 小欧间谍添加失败，请检查';
    END IF;
    
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'eu_customs_news'
    ) INTO table_exists;
    
    IF table_exists THEN
        RAISE NOTICE '✅ eu_customs_news 表已成功创建';
    ELSE
        RAISE WARNING '⚠️ eu_customs_news 表创建失败';
    END IF;
END $$;

-- 显示当前所有AI员工
-- SELECT name, agent_type, status FROM ai_agents ORDER BY created_at;
