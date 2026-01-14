-- 迁移脚本：添加小猎（线索猎手）AI员工
-- 执行前请备份数据库！

-- =====================================================
-- 步骤1：添加 lead_hunter 到 agent_type 枚举
-- =====================================================

-- 先检查是否已存在
DO $$
BEGIN
    -- 尝试添加新的枚举值
    ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'lead_hunter';
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'lead_hunter already exists in agent_type enum';
END $$;

-- =====================================================
-- 步骤2：插入小猎AI员工
-- =====================================================

-- 使用 ON CONFLICT 避免重复插入
INSERT INTO ai_agents (name, agent_type, description, status)
SELECT '小猎', 'lead_hunter'::agent_type, '线索猎手 - 自动搜索互联网上的潜在客户线索，发现物流需求商机', 'online'
WHERE NOT EXISTS (
    SELECT 1 FROM ai_agents WHERE name = '小猎'
);

-- 验证插入结果
DO $$
DECLARE
    agent_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO agent_count FROM ai_agents WHERE name = '小猎';
    IF agent_count > 0 THEN
        RAISE NOTICE '✅ 小猎（线索猎手）已成功添加到AI员工表';
    ELSE
        RAISE WARNING '⚠️ 小猎添加失败，请检查agent_type枚举';
    END IF;
END $$;

-- 显示当前所有AI员工
-- SELECT name, agent_type, status FROM ai_agents ORDER BY created_at;
