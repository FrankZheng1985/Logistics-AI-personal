-- 029: 添加热门话题表（小猎话题发现模式）
-- 用于存储小猎发现的待回答热门话题

-- 热门话题表
CREATE TABLE IF NOT EXISTS hot_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 话题基本信息
    title TEXT NOT NULL,                          -- 话题标题（问题标题）
    url TEXT NOT NULL,                            -- 话题链接
    platform VARCHAR(50) NOT NULL,                -- 平台：zhihu, xiaohongshu, weibo, douyin, bilibili
    
    -- 话题分析
    topic_type VARCHAR(50),                       -- 话题类型：question(问答), article(文章), video(视频)
    category VARCHAR(100),                        -- 分类：报价咨询、流程咨询、问题求助、行业讨论
    keywords TEXT[],                              -- 关键词标签
    
    -- 价值评估
    view_count INTEGER DEFAULT 0,                 -- 浏览量
    answer_count INTEGER DEFAULT 0,               -- 已有回答数
    follower_count INTEGER DEFAULT 0,             -- 关注人数
    value_score INTEGER DEFAULT 0,                -- 价值评分（0-100）
    
    -- AI分析
    ai_summary TEXT,                              -- AI总结的话题核心
    ai_answer_strategy TEXT,                      -- AI建议的回答策略
    ai_recommended_points TEXT[],                 -- AI建议的回答要点
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'new',             -- 状态：new(新发现), answered(已回答), skipped(跳过), expired(过期)
    priority VARCHAR(20) DEFAULT 'medium',        -- 优先级：high, medium, low
    
    -- 生成的回答内容
    generated_content TEXT,                       -- 小文生成的回答内容
    generated_at TIMESTAMP WITH TIME ZONE,        -- 生成时间
    
    -- 发布记录
    published_at TIMESTAMP WITH TIME ZONE,        -- 发布时间
    published_by VARCHAR(100),                    -- 发布人
    
    -- 效果追踪
    result_views INTEGER DEFAULT 0,               -- 回答获得的浏览量
    result_likes INTEGER DEFAULT 0,               -- 回答获得的点赞数
    result_leads INTEGER DEFAULT 0,               -- 带来的线索数
    
    -- 时间戳
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- 发现时间
    topic_created_at TIMESTAMP WITH TIME ZONE,    -- 话题原始创建时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 去重
    url_hash VARCHAR(64) UNIQUE                   -- URL哈希，用于去重
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_hot_topics_platform ON hot_topics(platform);
CREATE INDEX IF NOT EXISTS idx_hot_topics_status ON hot_topics(status);
CREATE INDEX IF NOT EXISTS idx_hot_topics_priority ON hot_topics(priority);
CREATE INDEX IF NOT EXISTS idx_hot_topics_value_score ON hot_topics(value_score DESC);
CREATE INDEX IF NOT EXISTS idx_hot_topics_discovered_at ON hot_topics(discovered_at DESC);

-- 话题搜索关键词配置表
CREATE TABLE IF NOT EXISTS topic_search_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword VARCHAR(200) NOT NULL,                -- 搜索关键词
    category VARCHAR(100),                        -- 分类
    platform VARCHAR(50),                         -- 指定平台（空表示所有平台）
    priority INTEGER DEFAULT 5,                   -- 优先级 1-10
    is_active BOOLEAN DEFAULT true,
    
    -- 效果统计
    search_count INTEGER DEFAULT 0,
    topics_found INTEGER DEFAULT 0,
    success_rate DECIMAL(5,4) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 插入默认的搜索关键词（针对物流/货代行业）
INSERT INTO topic_search_keywords (keyword, category, priority) VALUES
-- 报价咨询类（高价值）
('国际物流报价', '报价咨询', 9),
('海运费用多少', '报价咨询', 9),
('空运价格', '报价咨询', 9),
('FBA头程费用', '报价咨询', 10),
('欧洲物流报价', '报价咨询', 9),

-- 流程咨询类（建立专业形象）
('第一次发国际快递', '流程咨询', 8),
('海运清关流程', '流程咨询', 8),
('FBA发货流程', '流程咨询', 9),
('出口报关需要什么', '流程咨询', 8),

-- 问题求助类（高转化）
('货物被扣怎么办', '问题求助', 10),
('清关失败', '问题求助', 10),
('海运延误', '问题求助', 9),
('货代靠谱吗', '问题求助', 8),
('物流丢件', '问题求助', 9),

-- 选择咨询类（决策阶段）
('货代怎么选', '选择咨询', 9),
('物流公司推荐', '选择咨询', 8),
('FBA物流哪家好', '选择咨询', 9),
('海运还是空运', '选择咨询', 7),

-- 行业讨论类（内容引流）
('跨境电商物流', '行业讨论', 7),
('亚马逊卖家物流', '行业讨论', 8),
('外贸物流', '行业讨论', 7)

ON CONFLICT DO NOTHING;

-- 添加注释
COMMENT ON TABLE hot_topics IS '热门话题表 - 存储小猎发现的待回答话题';
COMMENT ON TABLE topic_search_keywords IS '话题搜索关键词配置';
