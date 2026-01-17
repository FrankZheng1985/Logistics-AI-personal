-- 024_enhance_company_config.sql
-- 增强公司配置表，添加Logo、聚焦市场、社交媒体等字段

-- 添加新字段
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS focus_markets TEXT[];  -- 聚焦市场/服务区域
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS company_website VARCHAR(300);
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS founded_year INTEGER;  -- 成立年份
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS employee_count VARCHAR(50);  -- 员工规模
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS business_scope TEXT;  -- 业务范围描述

-- 社交媒体账号
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS social_media JSONB DEFAULT '{}';
-- 格式: {"wechat_official": "公众号ID", "douyin": "抖音号", "xiaohongshu": "小红书号", "video_account": "视频号"}

-- 品牌相关
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS brand_slogan VARCHAR(200);  -- 品牌口号
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS brand_colors JSONB DEFAULT '{}';  -- 品牌色 {"primary": "#xxx", "secondary": "#xxx"}
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS company_values TEXT[];  -- 企业价值观

-- 内容生成相关配置
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS content_tone VARCHAR(50) DEFAULT 'professional';  -- 内容风格: professional/friendly/creative
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS content_focus_keywords TEXT[];  -- 内容关键词
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS forbidden_content TEXT[];  -- 禁止出现的内容/竞品名称

-- 添加注释
COMMENT ON COLUMN company_config.logo_url IS '公司Logo URL';
COMMENT ON COLUMN company_config.focus_markets IS '聚焦市场/服务区域，如: 德国,荷兰,英国';
COMMENT ON COLUMN company_config.social_media IS '社交媒体账号JSON';
COMMENT ON COLUMN company_config.content_tone IS '内容风格: professional/friendly/creative';
COMMENT ON COLUMN company_config.forbidden_content IS '禁止出现的内容，如竞品名称';
