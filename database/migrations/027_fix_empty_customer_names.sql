-- 修复客户表中空的 name 字段
-- 根据来源和创建时间生成有意义的默认名称

-- 1. 更新来源为 wechat 的客户
UPDATE customers 
SET name = CONCAT('微信客户_', LEFT(wechat_id, 8)),
    updated_at = NOW()
WHERE (name IS NULL OR name = '' OR name = '未知客户')
  AND source = 'wechat'
  AND wechat_id IS NOT NULL;

-- 2. 更新来源为 website 的客户
UPDATE customers 
SET name = CONCAT('网站访客_', TO_CHAR(created_at, 'MMDD'), '_', SUBSTRING(id::text, 1, 4)),
    updated_at = NOW()
WHERE (name IS NULL OR name = '' OR name = '未知客户')
  AND source = 'website';

-- 3. 更新其他来源的客户
UPDATE customers 
SET name = CONCAT(
    CASE source
        WHEN 'referral' THEN '推荐客户_'
        WHEN 'ad' THEN '广告客户_'
        ELSE '新客户_'
    END,
    TO_CHAR(created_at, 'MMDD'), '_', SUBSTRING(id::text, 1, 4)
),
    updated_at = NOW()
WHERE (name IS NULL OR name = '' OR name = '未知客户')
  AND source NOT IN ('wechat', 'website');

-- 4. 对于仍然没有名称的客户（兜底处理）
UPDATE customers 
SET name = CONCAT('客户_', TO_CHAR(created_at, 'YYYYMMDD'), '_', SUBSTRING(id::text, 1, 4)),
    updated_at = NOW()
WHERE name IS NULL OR name = '' OR name = '未知客户';

-- 5. 添加备注说明迁移完成
COMMENT ON TABLE customers IS '客户表 - 已修复空名称问题 (027_fix_empty_customer_names.sql)';
