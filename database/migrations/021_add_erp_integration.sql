-- ERP业务系统集成表
-- 用于存储ERP连接配置、数据缓存和同步日志
-- 安全说明：只存储只读API的凭证，不存储任何可写入的密钥

-- ERP连接配置表
CREATE TABLE IF NOT EXISTS erp_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_url VARCHAR(500) NOT NULL,                    -- ERP API地址
    auth_type VARCHAR(50) NOT NULL DEFAULT 'bearer',  -- 认证类型: bearer/token/api_key
    auth_token TEXT NOT NULL,                         -- 认证令牌（加密存储）
    username VARCHAR(100),                            -- 用户名（可选）
    description VARCHAR(500) DEFAULT 'BP Logistics ERP', -- 配置描述
    is_active BOOLEAN DEFAULT TRUE,                   -- 是否激活
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_erp_config_active ON erp_config(is_active);

-- ERP数据缓存表
CREATE TABLE IF NOT EXISTS erp_data_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(64) UNIQUE NOT NULL,            -- 缓存键（MD5哈希）
    data JSONB NOT NULL,                              -- 缓存的数据
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,     -- 过期时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 添加索引用于快速查找和清理过期数据
CREATE INDEX IF NOT EXISTS idx_erp_cache_key ON erp_data_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_erp_cache_expires ON erp_data_cache(expires_at);

-- ERP同步日志表
CREATE TABLE IF NOT EXISTS erp_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(200) NOT NULL,                   -- API端点
    params TEXT,                                      -- 请求参数（JSON字符串）
    success BOOLEAN DEFAULT TRUE,                     -- 是否成功
    error_message TEXT,                               -- 错误信息
    response_time_ms INTEGER,                         -- 响应时间（毫秒）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 添加索引用于日志查询
CREATE INDEX IF NOT EXISTS idx_erp_logs_created ON erp_sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_erp_logs_success ON erp_sync_logs(success);
CREATE INDEX IF NOT EXISTS idx_erp_logs_endpoint ON erp_sync_logs(endpoint);

-- 自动清理过期缓存的函数
CREATE OR REPLACE FUNCTION cleanup_erp_cache() RETURNS void AS $$
BEGIN
    DELETE FROM erp_data_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- 自动清理旧日志的函数（保留30天）
CREATE OR REPLACE FUNCTION cleanup_erp_logs() RETURNS void AS $$
BEGIN
    DELETE FROM erp_sync_logs WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- 添加注释说明安全策略
COMMENT ON TABLE erp_config IS 'ERP系统连接配置 - 仅存储只读API凭证';
COMMENT ON TABLE erp_data_cache IS 'ERP数据缓存 - 减少API调用频率';
COMMENT ON TABLE erp_sync_logs IS 'ERP同步日志 - 记录所有API请求';
COMMENT ON COLUMN erp_config.auth_token IS '认证令牌 - 只读API账户的凭证';
