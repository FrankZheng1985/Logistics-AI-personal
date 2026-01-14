-- 公司配置表迁移脚本
-- 创建时间: 2026-01-14

-- 创建公司配置表
CREATE TABLE IF NOT EXISTS company_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 公司基本信息
    company_name VARCHAR(200) DEFAULT '',
    company_intro TEXT,
    contact_phone VARCHAR(50),
    contact_email VARCHAR(100),
    contact_wechat VARCHAR(100),
    address VARCHAR(500),
    
    -- 产品与服务 (JSON格式存储)
    -- 格式: [{"name": "海运整柜", "description": "...", "features": ["..."]}]
    products JSONB DEFAULT '[]',
    
    -- 服务区域/航线
    -- 格式: [{"from_location": "中国", "to_location": "美国", "time": "25-30天", "price_ref": "...", "transport": "海运"}]
    service_routes JSONB DEFAULT '[]',
    
    -- 公司优势
    -- 格式: ["价格优惠", "时效快", "服务好"]
    advantages TEXT[] DEFAULT '{}',
    
    -- 常见FAQ
    -- 格式: [{"question": "...", "answer": "..."}]
    faq JSONB DEFAULT '[]',
    
    -- 价格参考说明
    price_policy TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建更新时间触发器
CREATE TRIGGER update_company_config_updated_at 
    BEFORE UPDATE ON company_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 添加注释
COMMENT ON TABLE company_config IS '公司配置表 - 存储公司产品、服务、区域等信息，供AI员工使用';
COMMENT ON COLUMN company_config.products IS '产品与服务列表，JSON数组格式';
COMMENT ON COLUMN company_config.service_routes IS '服务航线列表，JSON数组格式';
COMMENT ON COLUMN company_config.advantages IS '公司优势标签';
COMMENT ON COLUMN company_config.faq IS '常见问题与回答';
