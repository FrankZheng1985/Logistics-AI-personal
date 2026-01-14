-- ================================================
-- 迁移007: AI员工能力升级 - 新增表结构
-- 包含：工作标准、视频素材库、物流知识库、系统监控等
-- ================================================

-- =====================================================
-- 1. AI员工工作标准表
-- =====================================================
CREATE TABLE IF NOT EXISTS agent_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,              -- AI员工类型
    standard_category VARCHAR(100) NOT NULL,      -- 标准分类：quality/efficiency/professional
    standard_name VARCHAR(200) NOT NULL,          -- 标准名称
    standard_content JSONB NOT NULL DEFAULT '{}', -- 标准详细内容
    quality_metrics JSONB DEFAULT '{}',           -- 质量指标
    version INTEGER DEFAULT 1,                    -- 版本号
    is_active BOOLEAN DEFAULT TRUE,               -- 是否激活
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agent_standards_type ON agent_standards(agent_type);
CREATE INDEX idx_agent_standards_category ON agent_standards(standard_category);
CREATE INDEX idx_agent_standards_active ON agent_standards(is_active) WHERE is_active = TRUE;

-- 添加版本历史记录
CREATE TABLE IF NOT EXISTS agent_standards_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_id UUID REFERENCES agent_standards(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    standard_content JSONB NOT NULL,
    quality_metrics JSONB,
    changed_by VARCHAR(100),
    change_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 2. 视频模板表
-- =====================================================
CREATE TABLE IF NOT EXISTS video_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,                   -- 模板名称
    description TEXT,                             -- 模板描述
    template_type VARCHAR(50) NOT NULL,           -- 类型：opening/main/transition/ending
    category VARCHAR(100),                        -- 分类：logistics/corporate/product
    duration_seconds INTEGER,                     -- 模板时长
    structure JSONB NOT NULL DEFAULT '[]',        -- 模板结构定义（分镜）
    default_prompts JSONB DEFAULT '[]',           -- 默认AI生成提示词
    thumbnail_url VARCHAR(500),                   -- 缩略图
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,                -- 使用次数
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_video_templates_type ON video_templates(template_type);
CREATE INDEX idx_video_templates_category ON video_templates(category);

-- =====================================================
-- 3. 视频素材库表
-- =====================================================
CREATE TABLE IF NOT EXISTS video_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,                   -- 素材名称
    asset_type VARCHAR(50) NOT NULL,              -- 类型：video_clip/image/audio/transition
    category VARCHAR(100),                        -- 分类：warehouse/port/truck/airplane/ship
    subcategory VARCHAR(100),                     -- 子分类
    file_url VARCHAR(500) NOT NULL,               -- 文件URL
    thumbnail_url VARCHAR(500),                   -- 缩略图URL
    duration_seconds INTEGER,                     -- 时长（视频/音频）
    file_size BIGINT,                             -- 文件大小
    format VARCHAR(20),                           -- 格式：mp4/mp3/png/jpg
    resolution VARCHAR(20),                       -- 分辨率：1080p/4k
    tags TEXT[] DEFAULT '{}',                     -- 标签
    metadata JSONB DEFAULT '{}',                  -- 其他元数据
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_video_assets_type ON video_assets(asset_type);
CREATE INDEX idx_video_assets_category ON video_assets(category);
CREATE INDEX idx_video_assets_tags ON video_assets USING GIN(tags);

-- =====================================================
-- 4. 背景音乐库表
-- =====================================================
CREATE TABLE IF NOT EXISTS bgm_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,                   -- 音乐名称
    music_type VARCHAR(50) NOT NULL,              -- 类型：corporate/upbeat/warm/tech/epic/international
    mood VARCHAR(100),                            -- 情绪：激昂/温馨/专业/轻快
    file_url VARCHAR(500) NOT NULL,               -- 文件URL
    duration_seconds INTEGER NOT NULL,            -- 时长
    bpm INTEGER,                                  -- 节拍
    is_loopable BOOLEAN DEFAULT FALSE,            -- 是否可循环
    suitable_for TEXT[] DEFAULT '{}',             -- 适合场景
    license_type VARCHAR(50) DEFAULT 'royalty_free', -- 版权类型
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_bgm_music_type ON bgm_library(music_type);
CREATE INDEX idx_bgm_mood ON bgm_library(mood);

-- =====================================================
-- 5. 物流专业知识库表
-- =====================================================
CREATE TABLE IF NOT EXISTS logistics_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,                -- 分类：clearance/transit/pricing/risk/faq/terminology
    subcategory VARCHAR(100),                     -- 子分类
    title VARCHAR(500) NOT NULL,                  -- 标题
    content TEXT NOT NULL,                        -- 知识内容
    summary TEXT,                                 -- 摘要
    applicable_routes TEXT[] DEFAULT '{}',        -- 适用航线
    applicable_cargos TEXT[] DEFAULT '{}',        -- 适用货物类型
    applicable_countries TEXT[] DEFAULT '{}',     -- 适用国家
    experience_level VARCHAR(20) DEFAULT 'intermediate', -- 经验级别：beginner/intermediate/expert
    keywords TEXT[] DEFAULT '{}',                 -- 关键词
    is_verified BOOLEAN DEFAULT FALSE,            -- 是否经过验证
    source VARCHAR(100),                          -- 来源
    source_url VARCHAR(500),                      -- 来源链接
    usage_count INTEGER DEFAULT 0,                -- 使用次数
    last_used_at TIMESTAMP WITH TIME ZONE,        -- 最后使用时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_logistics_knowledge_category ON logistics_knowledge(category);
CREATE INDEX idx_logistics_knowledge_level ON logistics_knowledge(experience_level);
CREATE INDEX idx_logistics_knowledge_keywords ON logistics_knowledge USING GIN(keywords);
CREATE INDEX idx_logistics_knowledge_routes ON logistics_knowledge USING GIN(applicable_routes);
CREATE INDEX idx_logistics_knowledge_countries ON logistics_knowledge USING GIN(applicable_countries);

-- =====================================================
-- 6. 系统健康日志表
-- =====================================================
CREATE TABLE IF NOT EXISTS system_health_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_type VARCHAR(50) NOT NULL,              -- 检查类型：api/database/redis/certificate
    component_name VARCHAR(100) NOT NULL,         -- 组件名称
    status VARCHAR(20) NOT NULL,                  -- 状态：healthy/degraded/unhealthy/unknown
    response_time_ms INTEGER,                     -- 响应时间（毫秒）
    error_message TEXT,                           -- 错误信息
    details JSONB DEFAULT '{}',                   -- 详细信息
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_system_health_type ON system_health_logs(check_type);
CREATE INDEX idx_system_health_component ON system_health_logs(component_name);
CREATE INDEX idx_system_health_status ON system_health_logs(status);
CREATE INDEX idx_system_health_checked_at ON system_health_logs(checked_at DESC);

-- 保留最近30天的健康日志
CREATE OR REPLACE FUNCTION cleanup_old_health_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM system_health_logs WHERE checked_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 7. API状态监控表
-- =====================================================
CREATE TABLE IF NOT EXISTS api_status_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_name VARCHAR(100) NOT NULL,               -- API名称：keling_ai/dashscope/serper/smtp
    api_url VARCHAR(500),                         -- API地址
    status VARCHAR(20) NOT NULL,                  -- 状态：available/unavailable/degraded
    response_time_ms INTEGER,                     -- 响应时间
    http_status_code INTEGER,                     -- HTTP状态码
    error_type VARCHAR(50),                       -- 错误类型
    error_message TEXT,                           -- 错误信息
    request_count_today INTEGER DEFAULT 0,        -- 今日请求次数
    error_count_today INTEGER DEFAULT 0,          -- 今日错误次数
    quota_used JSONB DEFAULT '{}',                -- 配额使用情况
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_status_name ON api_status_logs(api_name);
CREATE INDEX idx_api_status_status ON api_status_logs(status);
CREATE INDEX idx_api_status_checked_at ON api_status_logs(checked_at DESC);

-- =====================================================
-- 8. SSL证书监控表
-- =====================================================
CREATE TABLE IF NOT EXISTS certificate_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(200) NOT NULL,                 -- 域名
    issuer VARCHAR(200),                          -- 颁发机构
    subject VARCHAR(500),                         -- 主题
    valid_from TIMESTAMP WITH TIME ZONE,          -- 有效期开始
    valid_until TIMESTAMP WITH TIME ZONE,         -- 有效期结束
    days_until_expiry INTEGER,                    -- 距离过期天数
    status VARCHAR(20) NOT NULL,                  -- 状态：valid/expiring_soon/expired/error
    last_check_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_certificate_domain ON certificate_status(domain);

-- =====================================================
-- 9. 每日报告表
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE NOT NULL,                    -- 报告日期
    report_type VARCHAR(50) NOT NULL,             -- 报告类型：daily/weekly/monthly
    
    -- AI员工工作统计
    agent_stats JSONB DEFAULT '{}',               -- 各员工工作统计
    
    -- 系统健康统计
    system_health JSONB DEFAULT '{}',             -- 系统健康状态
    
    -- 业务指标
    business_metrics JSONB DEFAULT '{}',          -- 业务指标
    
    -- 报告内容
    summary TEXT,                                 -- 摘要
    highlights JSONB DEFAULT '[]',                -- 亮点
    issues JSONB DEFAULT '[]',                    -- 问题
    recommendations JSONB DEFAULT '[]',           -- 建议
    
    -- 元数据
    generated_by VARCHAR(50) DEFAULT 'coordinator', -- 生成者
    generation_time_ms INTEGER,                   -- 生成耗时
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_daily_reports_date_type ON daily_reports(report_date, report_type);
CREATE INDEX idx_daily_reports_date ON daily_reports(report_date DESC);

-- =====================================================
-- 10. 多语言配音配置表
-- =====================================================
CREATE TABLE IF NOT EXISTS tts_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language_code VARCHAR(10) NOT NULL,           -- 语言代码：zh-CN/en-US/de-DE等
    language_name VARCHAR(50) NOT NULL,           -- 语言名称
    voice_id VARCHAR(100) NOT NULL,               -- TTS服务的voice ID
    voice_name VARCHAR(100) NOT NULL,             -- 语音名称
    gender VARCHAR(10),                           -- 性别：male/female
    provider VARCHAR(50) DEFAULT 'edge_tts',      -- TTS提供商：edge_tts/elevenlabs/azure
    sample_url VARCHAR(500),                      -- 示例音频URL
    is_default BOOLEAN DEFAULT FALSE,             -- 是否默认
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tts_voices_language ON tts_voices(language_code);
CREATE INDEX idx_tts_voices_provider ON tts_voices(provider);

-- 插入默认TTS语音配置
INSERT INTO tts_voices (language_code, language_name, voice_id, voice_name, gender, provider, is_default) VALUES
    ('zh-CN', '中文(普通话)', 'zh-CN-XiaoxiaoNeural', '晓晓', 'female', 'edge_tts', TRUE),
    ('zh-CN', '中文(普通话)', 'zh-CN-YunxiNeural', '云希', 'male', 'edge_tts', FALSE),
    ('zh-HK', '中文(粤语)', 'zh-HK-HiuMaanNeural', '晓曼', 'female', 'edge_tts', FALSE),
    ('en-US', '英语(美式)', 'en-US-JennyNeural', 'Jenny', 'female', 'edge_tts', TRUE),
    ('en-US', '英语(美式)', 'en-US-GuyNeural', 'Guy', 'male', 'edge_tts', FALSE),
    ('en-GB', '英语(英式)', 'en-GB-SoniaNeural', 'Sonia', 'female', 'edge_tts', FALSE),
    ('de-DE', '德语', 'de-DE-KatjaNeural', 'Katja', 'female', 'edge_tts', FALSE),
    ('fr-FR', '法语', 'fr-FR-DeniseNeural', 'Denise', 'female', 'edge_tts', FALSE),
    ('es-ES', '西班牙语', 'es-ES-ElviraNeural', 'Elvira', 'female', 'edge_tts', FALSE),
    ('ja-JP', '日语', 'ja-JP-NanamiNeural', 'Nanami', 'female', 'edge_tts', FALSE),
    ('ko-KR', '韩语', 'ko-KR-SunHiNeural', 'SunHi', 'female', 'edge_tts', FALSE),
    ('ar-SA', '阿拉伯语', 'ar-SA-ZariyahNeural', 'Zariyah', 'female', 'edge_tts', FALSE),
    ('pt-BR', '葡萄牙语(巴西)', 'pt-BR-FranciscaNeural', 'Francisca', 'female', 'edge_tts', FALSE),
    ('ru-RU', '俄语', 'ru-RU-SvetlanaNeural', 'Svetlana', 'female', 'edge_tts', FALSE)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 11. 视频生成任务详情表（长视频支持）
-- =====================================================
CREATE TABLE IF NOT EXISTS video_generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    
    -- 任务配置
    target_duration_seconds INTEGER NOT NULL,     -- 目标时长
    language_code VARCHAR(10) DEFAULT 'zh-CN',    -- 语言
    voice_id VARCHAR(100),                        -- 配音语音ID
    bgm_id UUID REFERENCES bgm_library(id),       -- 背景音乐ID
    template_id UUID REFERENCES video_templates(id), -- 使用的模板
    
    -- 分镜/片段
    segments JSONB NOT NULL DEFAULT '[]',         -- 视频片段列表
    current_segment INTEGER DEFAULT 0,            -- 当前处理的片段
    total_segments INTEGER DEFAULT 0,             -- 总片段数
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',         -- pending/generating/processing/composing/completed/failed
    progress_percent INTEGER DEFAULT 0,           -- 进度百分比
    
    -- 生成结果
    generated_clips JSONB DEFAULT '[]',           -- 已生成的片段信息
    final_video_url VARCHAR(500),                 -- 最终视频URL
    
    -- 错误处理
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- 时间追踪
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_video_gen_tasks_status ON video_generation_tasks(status);
CREATE INDEX idx_video_gen_tasks_video_id ON video_generation_tasks(video_id);

-- =====================================================
-- 12. 更新通知表，添加优先级和分类
-- =====================================================
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS action_url VARCHAR(500);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;

-- =====================================================
-- 触发器：自动更新updated_at
-- =====================================================
CREATE TRIGGER update_agent_standards_updated_at 
    BEFORE UPDATE ON agent_standards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_video_templates_updated_at 
    BEFORE UPDATE ON video_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_logistics_knowledge_updated_at 
    BEFORE UPDATE ON logistics_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 表注释
-- =====================================================
COMMENT ON TABLE agent_standards IS 'AI员工工作标准配置表';
COMMENT ON TABLE agent_standards_history IS 'AI员工工作标准历史版本';
COMMENT ON TABLE video_templates IS '视频模板库';
COMMENT ON TABLE video_assets IS '视频素材库';
COMMENT ON TABLE bgm_library IS '背景音乐库';
COMMENT ON TABLE logistics_knowledge IS '物流专业知识库';
COMMENT ON TABLE system_health_logs IS '系统健康检查日志';
COMMENT ON TABLE api_status_logs IS 'API状态监控日志';
COMMENT ON TABLE certificate_status IS 'SSL证书状态监控';
COMMENT ON TABLE daily_reports IS '每日/周/月工作报告';
COMMENT ON TABLE tts_voices IS '多语言TTS语音配置';
COMMENT ON TABLE video_generation_tasks IS '视频生成任务详情（支持长视频）';
