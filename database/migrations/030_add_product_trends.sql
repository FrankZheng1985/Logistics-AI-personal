-- 030: 添加产品趋势表（小猎产品发现功能）
-- 用于存储欧洲跨境电商热门产品趋势

-- 产品趋势表
CREATE TABLE IF NOT EXISTS product_trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 产品基本信息
    product_name TEXT NOT NULL,                   -- 产品名称
    category VARCHAR(200),                        -- 产品类别
    description TEXT,                             -- 产品描述
    
    -- 来源信息
    source_url TEXT,                              -- 来源链接
    source_platform VARCHAR(100),                 -- 来源平台：amazon, temu, shein, aliexpress 等
    source_region VARCHAR(50) DEFAULT 'europe',   -- 目标地区
    
    -- 趋势数据
    sales_rank INTEGER,                           -- 销量排名
    sales_volume VARCHAR(100),                    -- 销量描述（如 "10万+"）
    price_range VARCHAR(100),                     -- 价格区间
    growth_rate VARCHAR(50),                      -- 增长率
    trend_score INTEGER DEFAULT 0,                -- 趋势评分（0-100）
    
    -- AI分析
    ai_analysis TEXT,                             -- AI分析摘要
    ai_opportunity TEXT,                          -- AI识别的商机
    ai_logistics_tips TEXT,                       -- 物流建议
    keywords TEXT[],                              -- 关键词标签
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'new',             -- 状态：new, processed, archived
    is_added_to_knowledge BOOLEAN DEFAULT false,  -- 是否已添加到知识库
    is_email_sent BOOLEAN DEFAULT false,          -- 是否已发送邮件
    
    -- 时间戳
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_product_trends_status ON product_trends(status);
CREATE INDEX IF NOT EXISTS idx_product_trends_platform ON product_trends(source_platform);
CREATE INDEX IF NOT EXISTS idx_product_trends_score ON product_trends(trend_score DESC);
CREATE INDEX IF NOT EXISTS idx_product_trends_discovered_at ON product_trends(discovered_at DESC);

-- 产品趋势搜索关键词配置
CREATE TABLE IF NOT EXISTS product_trend_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword VARCHAR(200) NOT NULL,                -- 搜索关键词
    category VARCHAR(100),                        -- 分类
    platform VARCHAR(50),                         -- 指定平台
    priority INTEGER DEFAULT 5,                   -- 优先级 1-10
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 插入默认的搜索关键词（欧洲跨境电商热门产品）
INSERT INTO product_trend_keywords (keyword, category, priority) VALUES
-- 热门品类
('欧洲热销产品 2026', '综合', 10),
('欧洲跨境电商爆款', '综合', 10),
('德国亚马逊热销', '亚马逊', 9),
('英国亚马逊Best Seller', '亚马逊', 9),
('法国电商热卖', '综合', 8),

-- 具体品类
('欧洲家居用品热销', '家居', 8),
('欧洲户外用品趋势', '户外', 8),
('欧洲电子产品热门', '电子', 8),
('欧洲服装流行趋势', '服装', 7),
('欧洲美妆护肤热销', '美妆', 7),

-- 季节性产品
('欧洲圣诞礼物热销', '节日', 8),
('欧洲夏季热卖产品', '季节', 7),
('欧洲冬季保暖产品', '季节', 7),

-- 新兴趋势
('Temu欧洲热销', '新平台', 9),
('Shein欧洲爆款', '新平台', 8),
('TikTok Shop欧洲热门', '社交电商', 9)

ON CONFLICT DO NOTHING;

-- 添加注释
COMMENT ON TABLE product_trends IS '产品趋势表 - 存储小猎发现的欧洲热门产品';
COMMENT ON TABLE product_trend_keywords IS '产品趋势搜索关键词配置';
