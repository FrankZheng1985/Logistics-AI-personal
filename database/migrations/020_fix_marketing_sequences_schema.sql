-- 020: 修复营销序列表结构
-- 创建日期: 2026-01-15
-- 说明: 使数据库表结构与API代码一致

-- 1. 添加缺少的列到 marketing_sequences 表
ALTER TABLE marketing_sequences 
ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(100);

ALTER TABLE marketing_sequences 
ADD COLUMN IF NOT EXISTS trigger_condition JSONB DEFAULT '{}';

ALTER TABLE marketing_sequences 
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'draft';

ALTER TABLE marketing_sequences 
ADD COLUMN IF NOT EXISTS email_count INTEGER DEFAULT 0;

ALTER TABLE marketing_sequences 
ADD COLUMN IF NOT EXISTS enrolled_count INTEGER DEFAULT 0;

ALTER TABLE marketing_sequences 
ADD COLUMN IF NOT EXISTS converted_count INTEGER DEFAULT 0;

-- 2. 迁移旧数据：将 trigger_event 复制到 trigger_type
UPDATE marketing_sequences 
SET trigger_type = trigger_event 
WHERE trigger_type IS NULL AND trigger_event IS NOT NULL;

-- 3. 迁移 is_active 到 status
UPDATE marketing_sequences 
SET status = CASE 
    WHEN is_active = true THEN 'active'
    ELSE 'draft'
END
WHERE status IS NULL OR status = '';

-- 4. 设置默认值
UPDATE marketing_sequences 
SET trigger_type = 'manual' 
WHERE trigger_type IS NULL;

UPDATE marketing_sequences 
SET status = 'draft' 
WHERE status IS NULL;

-- 5. 添加非空约束（如果有数据的话先更新默认值）
-- ALTER TABLE marketing_sequences ALTER COLUMN trigger_type SET NOT NULL;

-- 6. 创建索引
CREATE INDEX IF NOT EXISTS idx_marketing_sequences_status ON marketing_sequences(status);
CREATE INDEX IF NOT EXISTS idx_marketing_sequences_trigger_type ON marketing_sequences(trigger_type);

-- 7. 添加注释
COMMENT ON COLUMN marketing_sequences.trigger_type IS '触发类型: first_inquiry, no_reply_3d, inactive_30d, manual';
COMMENT ON COLUMN marketing_sequences.trigger_condition IS '触发条件详情(JSON)';
COMMENT ON COLUMN marketing_sequences.status IS '状态: draft, active, paused';
COMMENT ON COLUMN marketing_sequences.email_count IS '邮件数量';
COMMENT ON COLUMN marketing_sequences.enrolled_count IS '已触达人数';
COMMENT ON COLUMN marketing_sequences.converted_count IS '已转化人数';

-- 完成提示
SELECT '营销序列表结构更新完成' AS result;
