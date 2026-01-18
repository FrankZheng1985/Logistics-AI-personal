-- 添加客户语言偏好字段
-- auto: 自动检测（默认）
-- zh: 中文
-- en: 英文

ALTER TABLE customers 
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'auto';

-- 添加注释
COMMENT ON COLUMN customers.language IS '客户语言偏好: auto(自动检测), zh(中文), en(英文)';

-- 创建索引方便查询
CREATE INDEX IF NOT EXISTS idx_customers_language ON customers(language);
