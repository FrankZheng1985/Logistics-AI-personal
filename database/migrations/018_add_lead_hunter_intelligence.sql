-- 小猎24小时智能搜索升级
-- 添加搜索历史表和关键词管理表

-- ==================== 关键词管理表 ====================
CREATE TABLE IF NOT EXISTS lead_hunt_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 关键词信息
    keyword VARCHAR(200) NOT NULL,
    keyword_type VARCHAR(50) DEFAULT 'general',  -- general, industry, platform, location, intent
    platform VARCHAR(50),  -- weibo, zhihu, tieba, google, etc. NULL表示全平台通用
    
    -- 效果统计
    search_count INTEGER DEFAULT 0,           -- 搜索次数
    leads_found INTEGER DEFAULT 0,            -- 找到的线索数
    high_intent_leads INTEGER DEFAULT 0,      -- 高意向线索数
    success_rate FLOAT DEFAULT 0.0,           -- 成功率 (leads_found / search_count)
    
    -- 状态控制
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5,               -- 优先级 1-10，越高越优先
    cooldown_hours INTEGER DEFAULT 2,         -- 冷却时间（小时），同一关键词间隔多久才能再次搜索
    
    -- 时间追踪
    last_searched_at TIMESTAMPTZ,
    next_search_after TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束
    UNIQUE(keyword, platform)
);

-- ==================== 搜索历史表 ====================
CREATE TABLE IF NOT EXISTS lead_hunt_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 搜索信息
    keyword_id UUID REFERENCES lead_hunt_keywords(id),
    keyword VARCHAR(200) NOT NULL,
    platform VARCHAR(50),
    search_query TEXT NOT NULL,              -- 实际搜索的查询语句
    
    -- 搜索结果
    results_count INTEGER DEFAULT 0,          -- 搜索返回结果数
    leads_found INTEGER DEFAULT 0,            -- 发现的线索数
    high_intent_leads INTEGER DEFAULT 0,      -- 高意向线索数
    urls_searched TEXT[],                     -- 搜索过的URL列表
    
    -- 时间
    searched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER                       -- 搜索耗时（毫秒）
);

-- ==================== 已搜索URL表（用于去重）====================
CREATE TABLE IF NOT EXISTS lead_hunt_searched_urls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    url_hash VARCHAR(64) NOT NULL UNIQUE,     -- URL的MD5哈希（用于快速查重）
    url TEXT NOT NULL,
    source_keyword VARCHAR(200),
    platform VARCHAR(50),
    is_lead BOOLEAN DEFAULT false,            -- 是否是有效线索
    lead_id UUID REFERENCES leads(id),        -- 关联的线索ID
    
    searched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 搜索统计表 ====================
CREATE TABLE IF NOT EXISTS lead_hunt_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    stat_date DATE NOT NULL UNIQUE,
    
    -- 当日统计
    total_searches INTEGER DEFAULT 0,         -- 总搜索次数
    total_results INTEGER DEFAULT 0,          -- 总搜索结果数
    total_leads INTEGER DEFAULT 0,            -- 总线索数
    high_intent_leads INTEGER DEFAULT 0,      -- 高意向线索数
    unique_urls INTEGER DEFAULT 0,            -- 去重后的URL数
    
    -- 按平台统计 (JSONB格式)
    platform_stats JSONB DEFAULT '{}',
    
    -- 按关键词类型统计 (JSONB格式)
    keyword_type_stats JSONB DEFAULT '{}',
    
    -- 最佳表现
    best_keyword VARCHAR(200),
    best_platform VARCHAR(50),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==================== 创建索引 ====================
CREATE INDEX IF NOT EXISTS idx_hunt_keywords_active ON lead_hunt_keywords(is_active, priority DESC);
CREATE INDEX IF NOT EXISTS idx_hunt_keywords_next_search ON lead_hunt_keywords(next_search_after);
CREATE INDEX IF NOT EXISTS idx_hunt_keywords_success_rate ON lead_hunt_keywords(success_rate DESC);
CREATE INDEX IF NOT EXISTS idx_hunt_history_searched_at ON lead_hunt_history(searched_at DESC);
CREATE INDEX IF NOT EXISTS idx_hunt_urls_hash ON lead_hunt_searched_urls(url_hash);
CREATE INDEX IF NOT EXISTS idx_hunt_stats_date ON lead_hunt_stats(stat_date DESC);

-- ==================== 初始化关键词库 ====================
INSERT INTO lead_hunt_keywords (keyword, keyword_type, platform, priority, cooldown_hours) VALUES
    -- 核心需求关键词（高优先级）
    ('找货代', 'intent', NULL, 10, 1),
    ('货代推荐', 'intent', NULL, 10, 1),
    ('求推荐货代', 'intent', NULL, 10, 1),
    ('物流报价', 'intent', NULL, 9, 1),
    ('海运询价', 'intent', NULL, 9, 2),
    ('空运报价', 'intent', NULL, 9, 2),
    ('清关报价', 'intent', NULL, 9, 2),
    
    -- 物流服务关键词
    ('跨境物流', 'service', NULL, 8, 2),
    ('FBA物流', 'service', NULL, 8, 2),
    ('国际快递', 'service', NULL, 7, 3),
    ('海运专线', 'service', NULL, 7, 3),
    ('空运专线', 'service', NULL, 7, 3),
    ('清关服务', 'service', NULL, 7, 3),
    ('货代服务', 'service', NULL, 7, 3),
    
    -- 欧洲线路关键词
    ('欧洲清关', 'location', NULL, 9, 2),
    ('发货到欧洲', 'location', NULL, 9, 2),
    ('德国物流', 'location', NULL, 8, 3),
    ('法国物流', 'location', NULL, 8, 3),
    ('英国物流', 'location', NULL, 8, 3),
    ('欧洲FBA', 'location', NULL, 9, 2),
    ('欧洲派送', 'location', NULL, 8, 3),
    ('德国清关', 'location', NULL, 8, 3),
    ('欧洲专线', 'location', NULL, 8, 3),
    
    -- 美国线路关键词
    ('发货到美国', 'location', NULL, 8, 3),
    ('美国FBA', 'location', NULL, 9, 2),
    ('美国专线', 'location', NULL, 8, 3),
    ('美国清关', 'location', NULL, 8, 3),
    
    -- 行业相关关键词
    ('跨境电商物流', 'industry', NULL, 8, 2),
    ('亚马逊物流', 'industry', NULL, 9, 2),
    ('外贸物流', 'industry', NULL, 7, 3),
    ('电商卖家发货', 'industry', NULL, 8, 3),
    ('1688发货', 'industry', NULL, 7, 4),
    
    -- 问题类关键词（用户在找解决方案）
    ('物流怎么选', 'intent', NULL, 9, 2),
    ('货代哪家好', 'intent', NULL, 9, 2),
    ('物流费用', 'intent', NULL, 8, 3),
    ('发货时效', 'intent', NULL, 7, 3),
    ('物流渠道', 'intent', NULL, 7, 3),
    
    -- 紧急需求关键词（最高优先级）
    ('急找货代', 'intent', NULL, 10, 1),
    ('急需发货', 'intent', NULL, 10, 1),
    ('马上发货', 'intent', NULL, 10, 1),
    ('今天发货', 'intent', NULL, 10, 1),
    
    -- 平台特定关键词
    ('找货代 有推荐的吗', 'intent', 'weibo', 9, 2),
    ('欧洲物流 求推荐', 'intent', 'zhihu', 9, 2),
    ('货代吧 求推荐', 'intent', 'tieba', 9, 2)
ON CONFLICT (keyword, platform) DO NOTHING;

-- ==================== 更新触发器 ====================
CREATE OR REPLACE FUNCTION update_lead_hunt_keywords_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_hunt_keywords_updated_at ON lead_hunt_keywords;
CREATE TRIGGER trigger_hunt_keywords_updated_at
    BEFORE UPDATE ON lead_hunt_keywords
    FOR EACH ROW
    EXECUTE FUNCTION update_lead_hunt_keywords_updated_at();

-- ==================== 关键词效果更新函数 ====================
CREATE OR REPLACE FUNCTION update_keyword_stats(
    p_keyword_id UUID,
    p_leads_found INTEGER,
    p_high_intent INTEGER
)
RETURNS VOID AS $$
BEGIN
    UPDATE lead_hunt_keywords
    SET 
        search_count = search_count + 1,
        leads_found = leads_found + p_leads_found,
        high_intent_leads = high_intent_leads + p_high_intent,
        success_rate = CASE 
            WHEN search_count + 1 > 0 
            THEN (leads_found + p_leads_found)::FLOAT / (search_count + 1)
            ELSE 0 
        END,
        last_searched_at = CURRENT_TIMESTAMP,
        next_search_after = CURRENT_TIMESTAMP + (cooldown_hours || ' hours')::INTERVAL,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_keyword_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE lead_hunt_keywords IS '小猎关键词管理表 - 存储搜索关键词及其效果统计';
COMMENT ON TABLE lead_hunt_history IS '小猎搜索历史表 - 记录每次搜索的详细信息';
COMMENT ON TABLE lead_hunt_searched_urls IS '已搜索URL表 - 用于URL去重';
COMMENT ON TABLE lead_hunt_stats IS '搜索统计表 - 每日搜索效果汇总';
