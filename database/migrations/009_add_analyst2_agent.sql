-- 迁移009: 添加小析2（群聊情报员）AI员工
-- 2026-01-14

-- =====================================================
-- 步骤1：添加 analyst2 到 agent_type 枚举
-- =====================================================

DO $$
BEGIN
    -- 尝试添加新的枚举值
    ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'analyst2';
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'analyst2 already exists in agent_type enum';
END $$;

-- =====================================================
-- 步骤2：插入小析2 AI员工
-- =====================================================

INSERT INTO ai_agents (name, agent_type, description, status)
SELECT '小析2', 'analyst2'::agent_type, '群聊情报员 - 监控微信群消息，提取有价值信息入库，知识库更新', 'online'
WHERE NOT EXISTS (
    SELECT 1 FROM ai_agents WHERE name = '小析2' OR agent_type = 'analyst2'
);

-- 验证插入结果
DO $$
DECLARE
    agent_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO agent_count FROM ai_agents WHERE name = '小析2';
    IF agent_count > 0 THEN
        RAISE NOTICE '✅ 小析2（群聊情报员）已成功添加到AI员工表';
    ELSE
        RAISE WARNING '⚠️ 小析2添加失败，请检查';
    END IF;
END $$;

-- 显示当前所有AI员工
-- SELECT name, agent_type, status FROM ai_agents ORDER BY created_at;
