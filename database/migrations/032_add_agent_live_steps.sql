-- ================================================
-- 迁移032: 添加AI员工实时工作步骤表
-- 用于支持实时工作直播功能
-- ================================================

-- 1. AI员工实时工作步骤表
CREATE TABLE IF NOT EXISTS agent_live_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,               -- 员工类型: lead_hunter, copywriter, etc.
    agent_name VARCHAR(50) NOT NULL,               -- 员工名称: 小猎, 小文, etc.
    session_id UUID NOT NULL,                      -- 任务会话ID，一次任务一个session
    step_type VARCHAR(50) NOT NULL,                -- 步骤类型: search/analyze/write/fetch/think/result/error
    step_title VARCHAR(200) NOT NULL,              -- 步骤标题，如"搜索关键词"
    step_content TEXT,                             -- 步骤详细内容
    step_data JSONB,                               -- 结构化数据（URL、关键词等）
    status VARCHAR(20) DEFAULT 'running',          -- 状态: running/completed/failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_live_steps_agent ON agent_live_steps(agent_type);
CREATE INDEX IF NOT EXISTS idx_live_steps_session ON agent_live_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_live_steps_created ON agent_live_steps(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_steps_agent_created ON agent_live_steps(agent_type, created_at DESC);

-- 2. 添加任务会话表，用于追踪每次任务执行
CREATE TABLE IF NOT EXISTS agent_task_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    task_type VARCHAR(100) NOT NULL,               -- 任务类型
    task_description TEXT,                          -- 任务描述
    status VARCHAR(20) DEFAULT 'running',          -- running/completed/failed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,                           -- 执行时长(毫秒)
    result_summary TEXT,                           -- 结果摘要
    error_message TEXT,                            -- 错误信息
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_sessions_agent ON agent_task_sessions(agent_type);
CREATE INDEX IF NOT EXISTS idx_task_sessions_status ON agent_task_sessions(status);
CREATE INDEX IF NOT EXISTS idx_task_sessions_created ON agent_task_sessions(created_at DESC);

-- 3. 清理旧数据的函数（保留最近7天的数据）
CREATE OR REPLACE FUNCTION cleanup_old_live_steps()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_live_steps WHERE created_at < NOW() - INTERVAL '7 days';
    DELETE FROM agent_task_sessions WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- 添加注释
COMMENT ON TABLE agent_live_steps IS 'AI员工实时工作步骤，用于工作直播功能';
COMMENT ON TABLE agent_task_sessions IS 'AI员工任务会话，追踪每次任务执行';
COMMENT ON COLUMN agent_live_steps.step_type IS '步骤类型: search(搜索)/fetch(访问网页)/think(AI分析)/write(写作)/result(结果)/error(错误)';
