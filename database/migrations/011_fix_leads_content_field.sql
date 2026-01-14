-- 迁移011: 修复 leads 表字段
-- 2026-01-14

-- 添加 content 字段（JSONB格式存储详细线索内容）
ALTER TABLE leads ADD COLUMN IF NOT EXISTS content JSONB;

-- 添加 source_url 唯一索引（用于ON CONFLICT避免重复）
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_source_url_unique ON leads(source_url) WHERE source_url IS NOT NULL;

-- 验证
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count 
    FROM information_schema.columns 
    WHERE table_name = 'leads' AND column_name = 'content';
    
    IF col_count > 0 THEN
        RAISE NOTICE '✅ content 字段已添加到 leads 表';
    ELSE
        RAISE WARNING '⚠️ content 字段添加失败';
    END IF;
END $$;
