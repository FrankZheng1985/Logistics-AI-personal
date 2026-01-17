-- =====================================================
-- 内容营销系统数据库表
-- 支持全自动内容生成和发布
-- =====================================================

-- 内容日历表（每日内容计划）
CREATE TABLE IF NOT EXISTS content_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 日期和类型
    content_date DATE NOT NULL,                    -- 内容日期
    day_of_week INTEGER NOT NULL,                  -- 星期几（1-7）
    content_type VARCHAR(50) NOT NULL,             -- 内容类型
    -- 类型包括: knowledge(知识), pricing(运价), case(案例), policy(政策), 
    --          faq(问答), story(故事), weekly(周报)
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',          -- pending/generating/generated/published/failed
    
    -- 生成配置
    topic VARCHAR(500),                            -- 主题/标题
    data_source JSONB DEFAULT '{}',                -- 数据来源配置
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    generated_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(content_date, content_type)
);

-- 内容条目表（生成的具体内容）
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID REFERENCES content_calendar(id) ON DELETE CASCADE,
    
    -- 平台
    platform VARCHAR(30) NOT NULL,                 -- douyin/xiaohongshu/wechat_article/wechat_moments/video_account
    
    -- 内容
    title VARCHAR(200),                            -- 标题
    content TEXT NOT NULL,                         -- 正文内容
    hashtags TEXT[],                               -- 话题标签
    cover_prompt VARCHAR(500),                     -- 封面图生成提示词（用于AI生图）
    video_script TEXT,                             -- 视频脚本（如果是视频内容）
    
    -- 引流钩子
    call_to_action VARCHAR(500),                   -- 行动号召
    contact_info VARCHAR(200),                     -- 联系方式引导
    
    -- 状态
    status VARCHAR(20) DEFAULT 'draft',            -- draft/approved/published/rejected
    
    -- 发布信息
    published_at TIMESTAMP WITH TIME ZONE,
    platform_post_id VARCHAR(100),                 -- 平台发布后的ID
    platform_url VARCHAR(500),                     -- 平台链接
    
    -- 效果追踪
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    leads_generated INTEGER DEFAULT 0,             -- 带来的线索数
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 内容模板表（可复用的内容模板）
CREATE TABLE IF NOT EXISTS content_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基本信息
    name VARCHAR(100) NOT NULL,
    content_type VARCHAR(50) NOT NULL,             -- knowledge/pricing/case/policy/faq/story/weekly
    platform VARCHAR(30) NOT NULL,                 -- douyin/xiaohongshu/wechat_article/wechat_moments
    
    -- 模板内容
    title_template VARCHAR(200),                   -- 标题模板（支持变量如 {route}, {price}）
    content_template TEXT NOT NULL,                -- 内容模板
    hashtags_template TEXT[],                      -- 话题标签模板
    cta_template VARCHAR(500),                     -- CTA模板
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    use_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ERP数据缓存表（缓存从ERP获取的数据，避免频繁调用）
CREATE TABLE IF NOT EXISTS erp_data_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    data_type VARCHAR(50) NOT NULL,                -- pricing/availability/announcements/cases
    data_key VARCHAR(100),                         -- 数据键（如航线名称）
    data_value JSONB NOT NULL,                     -- 数据内容
    
    -- 缓存控制
    expires_at TIMESTAMP WITH TIME ZONE,           -- 过期时间
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(data_type, data_key)
);

-- 内容发布账号表
CREATE TABLE IF NOT EXISTS content_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    platform VARCHAR(30) NOT NULL,                 -- douyin/xiaohongshu/wechat/video_account
    account_name VARCHAR(100) NOT NULL,
    account_id VARCHAR(100),                       -- 平台账号ID
    
    -- API凭证（加密存储）
    credentials JSONB DEFAULT '{}',                -- app_id, app_secret, access_token 等
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',          -- pending/active/expired/disabled
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_content_calendar_date ON content_calendar(content_date);
CREATE INDEX IF NOT EXISTS idx_content_calendar_status ON content_calendar(status);
CREATE INDEX IF NOT EXISTS idx_content_items_calendar ON content_items(calendar_id);
CREATE INDEX IF NOT EXISTS idx_content_items_platform ON content_items(platform);
CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(status);
CREATE INDEX IF NOT EXISTS idx_erp_cache_type ON erp_data_cache(data_type);
CREATE INDEX IF NOT EXISTS idx_erp_cache_expires ON erp_data_cache(expires_at);

-- 插入默认内容模板
INSERT INTO content_templates (name, content_type, platform, title_template, content_template, hashtags_template, cta_template)
VALUES 
-- 抖音模板
('运价播报-抖音', 'pricing', 'douyin', 
 '本周{destination}海运运价出炉！',
 '🚢 {destination}海运最新报价

💰 40GP整柜: ${price}
⏰ 时效: {transit_time}
📦 舱位: {availability}

{highlight}

想了解详细报价？评论区扣1，私信发你！',
 ARRAY['物流', '海运', '跨境电商', '外贸'],
 '评论区扣1，私信发你详细报价！'),

('知识科普-抖音', 'knowledge', 'douyin',
 '{topic}，这3点你一定要知道！',
 '做外贸的朋友注意了！

关于{topic}，很多人都踩过这些坑：

1️⃣ {point1}
2️⃣ {point2}  
3️⃣ {point3}

{solution}

需要物流报价？主页加微信，免费咨询！',
 ARRAY['外贸知识', '物流干货', '跨境电商'],
 '主页加微信，免费获取报价！'),

-- 小红书模板
('运价播报-小红书', 'pricing', 'xiaohongshu',
 '📦{month}月{destination}物流运价汇总｜建议收藏',
 '姐妹们！整理了最新的{destination}物流价格 💰

🚢 海运整柜
· 40GP: ${sea_price}
· 时效: {sea_time}

✈️ 空运
· 价格: ¥{air_price}/kg
· 时效: {air_time}

🚄 铁路
· 40GP: ${rail_price}
· 时效: {rail_time}

💡 选择建议：
{recommendation}

需要具体报价的宝子，评论区留言或私信我～',
 ARRAY['跨境物流', '外贸干货', '物流价格', '海运', '空运'],
 '需要报价私信我，备注"小红书"优先回复～'),

('成功案例-小红书', 'case', 'xiaohongshu',
 '真实案例｜{customer_type}发货{destination}，{highlight}',
 '分享一个最近的成功案例 ✨

📦 客户情况：
· 类型: {customer_type}
· 货物: {cargo_type}
· 目的地: {destination}

🚚 服务方案：
{service_detail}

✅ 结果：
{result}

💬 客户反馈：
"{feedback}"

有类似需求的姐妹可以参考～',
 ARRAY['物流案例', '跨境电商', '发货经验'],
 '私信可咨询具体方案～'),

-- 公众号模板
('运价分析-公众号', 'pricing', 'wechat_article',
 '{month}月欧洲物流运价分析：{trend}趋势明显',
 '# {month}月欧洲物流运价分析

## 一、本月运价概况

{overview}

## 二、各航线详细报价

### 海运运价
{sea_freight_detail}

### 空运运价
{air_freight_detail}

### 铁路运价
{rail_freight_detail}

## 三、市场分析

{market_analysis}

## 四、发货建议

{recommendations}

---

**需要详细报价？**

扫描下方二维码，添加客服微信，获取专属报价方案！

{contact_qrcode}',
 ARRAY['物流运价', '欧洲物流', '跨境电商'],
 '扫码添加客服微信，获取专属报价！'),

-- 朋友圈模板
('运价播报-朋友圈', 'pricing', 'wechat_moments',
 NULL,
 '📢 本周欧洲海运运价速报

🇩🇪 德国: ${de_price}/40GP
🇬🇧 英国: ${uk_price}/40GP  
🇫🇷 法国: ${fr_price}/40GP
🇳🇱 荷兰: ${nl_price}/40GP

⏰ 时效: {transit_time}
💡 {highlight}

需要报价的老板私信我 👇',
 ARRAY['欧洲物流', '海运'],
 '需要详细报价私信我')

ON CONFLICT DO NOTHING;

-- 添加内容营销相关的AI员工
INSERT INTO ai_agents (agent_type, name, role, description, avatar, status, capabilities)
VALUES (
    'content_creator',
    '小媒',
    '内容运营',
    '内容运营专员 - 负责每日内容生成、多平台发布、效果追踪',
    '📱',
    'active',
    ARRAY['content_generation', 'multi_platform', 'analytics']
)
ON CONFLICT (agent_type) DO UPDATE SET
    name = EXCLUDED.name,
    role = EXCLUDED.role,
    description = EXCLUDED.description;

COMMENT ON TABLE content_calendar IS '内容日历表 - 管理每日内容生成计划';
COMMENT ON TABLE content_items IS '内容条目表 - 存储生成的具体内容';
COMMENT ON TABLE content_templates IS '内容模板表 - 可复用的内容模板';
COMMENT ON TABLE erp_data_cache IS 'ERP数据缓存表 - 缓存运价等数据';
COMMENT ON TABLE content_accounts IS '内容发布账号表 - 管理各平台账号';
