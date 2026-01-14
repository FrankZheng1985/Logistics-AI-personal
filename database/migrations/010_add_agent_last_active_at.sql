-- 迁移010: 添加 ai_agents.last_active_at 字段
-- 2026-01-14

-- 添加最后活跃时间字段
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE;

-- 初始化为当前时间
UPDATE ai_agents SET last_active_at = NOW() WHERE last_active_at IS NULL;

-- 验证
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count 
    FROM information_schema.columns 
    WHERE table_name = 'ai_agents' AND column_name = 'last_active_at';
    
    IF col_count > 0 THEN
        RAISE NOTICE '✅ last_active_at 字段已添加到 ai_agents 表';
    ELSE
        RAISE WARNING '⚠️ last_active_at 字段添加失败';
    END IF;
END $$;
