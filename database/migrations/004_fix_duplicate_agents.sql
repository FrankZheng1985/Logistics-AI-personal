-- 修复重复的AI员工数据
-- 2026-01-14

-- 步骤1: 删除重复的AI员工，只保留最早创建的那个
DELETE FROM ai_agents a
WHERE a.id NOT IN (
    SELECT DISTINCT ON (agent_type) id
    FROM ai_agents
    ORDER BY agent_type, created_at ASC
);

-- 步骤2: 添加唯一约束，防止将来重复插入
ALTER TABLE ai_agents ADD CONSTRAINT unique_agent_type UNIQUE (agent_type);

-- 步骤3: 同时给name也加个唯一约束（可选，但推荐）
-- ALTER TABLE ai_agents ADD CONSTRAINT unique_agent_name UNIQUE (name);

-- 验证：查看剩余的员工数量（应该是7个）
-- SELECT COUNT(*) FROM ai_agents;
-- SELECT name, agent_type FROM ai_agents ORDER BY agent_type;
