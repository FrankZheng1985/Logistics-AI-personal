-- 小调企业微信交互记录表
-- 记录通过企业微信与小调的所有交互

-- 创建交互记录表
CREATE TABLE IF NOT EXISTS coordinator_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,           -- 企业微信用户ID
    content TEXT NOT NULL,                    -- 用户发送的内容
    interaction_type VARCHAR(50) NOT NULL,    -- 交互类型: report/task_dispatch/status_check/help
    result JSONB,                             -- 处理结果
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_coordinator_interactions_user_id 
    ON coordinator_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_coordinator_interactions_type 
    ON coordinator_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_coordinator_interactions_created_at 
    ON coordinator_interactions(created_at DESC);

-- 添加注释
COMMENT ON TABLE coordinator_interactions IS '小调企业微信交互记录';
COMMENT ON COLUMN coordinator_interactions.user_id IS '企业微信用户ID';
COMMENT ON COLUMN coordinator_interactions.content IS '用户发送的内容';
COMMENT ON COLUMN coordinator_interactions.interaction_type IS '交互类型: report(日报)/task_dispatch(任务分配)/status_check(状态检查)/help(帮助)';
COMMENT ON COLUMN coordinator_interactions.result IS '处理结果JSON';

-- 确保 ai_tasks 表存在（小调任务分配需要）
CREATE TABLE IF NOT EXISTS ai_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL,          -- 任务类型
    agent_type VARCHAR(50) NOT NULL,          -- 执行的AI员工类型
    status VARCHAR(20) DEFAULT 'pending',     -- 状态: pending/running/completed/failed
    priority INTEGER DEFAULT 5,                -- 优先级 (1最高, 10最低)
    input_data JSONB,                         -- 输入数据
    output_data JSONB,                        -- 输出数据
    error_message TEXT,                       -- 错误信息
    started_at TIMESTAMP WITH TIME ZONE,      -- 开始时间
    completed_at TIMESTAMP WITH TIME ZONE,    -- 完成时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ai_tasks 索引
CREATE INDEX IF NOT EXISTS idx_ai_tasks_agent_type ON ai_tasks(agent_type);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON ai_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_created_at ON ai_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_priority ON ai_tasks(priority);

COMMENT ON TABLE ai_tasks IS 'AI员工任务队列';
