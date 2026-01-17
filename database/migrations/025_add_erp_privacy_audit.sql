-- =====================================================
-- 025: ERP数据隐私保护 - 审计日志表
-- 创建时间: 2026-01-17
-- 功能: 记录ERP数据访问审计日志，增强数据安全
-- =====================================================

-- 创建ERP访问审计日志表
CREATE TABLE IF NOT EXISTS erp_access_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 访问信息
    endpoint VARCHAR(500) NOT NULL,          -- 访问的API端点
    user_id VARCHAR(100) DEFAULT 'anonymous', -- 访问用户ID
    user_ip VARCHAR(50),                     -- 访问者IP地址
    
    -- 请求参数（脱敏后存储）
    params JSONB DEFAULT '{}',
    
    -- 响应信息
    data_count INTEGER DEFAULT 0,            -- 返回的数据条数
    success BOOLEAN DEFAULT TRUE,            -- 是否成功
    error_message TEXT,                      -- 错误信息
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引以优化查询
CREATE INDEX IF NOT EXISTS idx_erp_audit_endpoint ON erp_access_audit(endpoint);
CREATE INDEX IF NOT EXISTS idx_erp_audit_user_id ON erp_access_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_erp_audit_created_at ON erp_access_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_erp_audit_success ON erp_access_audit(success);

-- 添加表注释
COMMENT ON TABLE erp_access_audit IS 'ERP数据访问审计日志表，用于追踪敏感数据的访问记录';
COMMENT ON COLUMN erp_access_audit.endpoint IS 'API端点路径';
COMMENT ON COLUMN erp_access_audit.user_id IS '访问用户标识';
COMMENT ON COLUMN erp_access_audit.user_ip IS '访问者IP地址';
COMMENT ON COLUMN erp_access_audit.params IS '请求参数（已脱敏）';
COMMENT ON COLUMN erp_access_audit.data_count IS '返回数据条数';
COMMENT ON COLUMN erp_access_audit.success IS '请求是否成功';
COMMENT ON COLUMN erp_access_audit.error_message IS '错误信息';

-- 修改erp_data_cache表，添加加密标记字段
ALTER TABLE erp_data_cache 
    ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS data_hash VARCHAR(64);

-- 添加erp_data_cache表注释
COMMENT ON COLUMN erp_data_cache.is_encrypted IS '数据是否已加密';
COMMENT ON COLUMN erp_data_cache.data_hash IS '数据哈希值，用于完整性校验';

-- 创建定期清理旧审计日志的函数（保留90天）
CREATE OR REPLACE FUNCTION cleanup_old_erp_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM erp_access_audit 
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- 创建ERP隐私配置表
CREATE TABLE IF NOT EXISTS erp_privacy_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 脱敏配置
    mask_phone BOOLEAN DEFAULT TRUE,         -- 是否脱敏手机号
    mask_email BOOLEAN DEFAULT TRUE,         -- 是否脱敏邮箱
    mask_address BOOLEAN DEFAULT TRUE,       -- 是否脱敏地址
    mask_bank_card BOOLEAN DEFAULT TRUE,     -- 是否脱敏银行卡
    mask_amounts BOOLEAN DEFAULT TRUE,       -- 是否脱敏金额
    mask_contact_names BOOLEAN DEFAULT TRUE, -- 是否脱敏联系人姓名
    
    -- 访问控制
    require_auth BOOLEAN DEFAULT TRUE,       -- 是否要求登录
    allowed_roles TEXT[],                    -- 允许访问的角色
    blocked_endpoints TEXT[],                -- 禁止访问的端点
    
    -- 审计配置
    enable_audit BOOLEAN DEFAULT TRUE,       -- 是否启用审计
    audit_retention_days INTEGER DEFAULT 90, -- 审计日志保留天数
    
    -- 加密配置
    encrypt_cache BOOLEAN DEFAULT TRUE,      -- 是否加密缓存
    
    -- 元数据
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- 插入默认隐私配置
INSERT INTO erp_privacy_config (
    mask_phone, mask_email, mask_address, mask_bank_card, 
    mask_amounts, mask_contact_names, require_auth,
    enable_audit, encrypt_cache
) VALUES (
    TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE
) ON CONFLICT DO NOTHING;

-- 创建获取隐私配置的函数
CREATE OR REPLACE FUNCTION get_erp_privacy_config()
RETURNS TABLE (
    mask_phone BOOLEAN,
    mask_email BOOLEAN,
    mask_address BOOLEAN,
    mask_bank_card BOOLEAN,
    mask_amounts BOOLEAN,
    mask_contact_names BOOLEAN,
    require_auth BOOLEAN,
    enable_audit BOOLEAN,
    encrypt_cache BOOLEAN
) AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        p.mask_phone,
        p.mask_email,
        p.mask_address,
        p.mask_bank_card,
        p.mask_amounts,
        p.mask_contact_names,
        p.require_auth,
        p.enable_audit,
        p.encrypt_cache
    FROM erp_privacy_config p
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 输出完成信息
DO $$ 
BEGIN 
    RAISE NOTICE 'ERP隐私保护数据库迁移完成';
    RAISE NOTICE '- 创建了审计日志表 erp_access_audit';
    RAISE NOTICE '- 创建了隐私配置表 erp_privacy_config';
    RAISE NOTICE '- 添加了缓存加密字段';
END $$;
