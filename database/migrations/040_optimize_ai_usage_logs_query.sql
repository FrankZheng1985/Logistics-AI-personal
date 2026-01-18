-- 优化AI用量日志查询性能
-- 针对 /api/ai-usage/logs 接口的性能优化

-- 1. 添加复合索引,优化分页查询
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created_at_desc ON ai_usage_logs(created_at DESC);

-- 2. 添加复合索引,优化多条件筛选
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_agent_created ON ai_usage_logs(agent_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_provider_created ON ai_usage_logs(provider, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_model_created ON ai_usage_logs(model_name, created_at DESC);

-- 3. 添加局部索引,优化成功/失败查询
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_success ON ai_usage_logs(is_success, created_at DESC);

-- 4. 添加任务类型+时间的复合索引
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_task_created ON ai_usage_logs(task_type, created_at DESC);

-- 5. 分析表,更新统计信息
ANALYZE ai_usage_logs;

-- 6. 建议:定期清理旧数据(可选,保留最近6个月的数据)
-- 创建一个函数用于清理旧数据
CREATE OR REPLACE FUNCTION cleanup_old_ai_usage_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 删除6个月前的数据
    DELETE FROM ai_usage_logs 
    WHERE created_at < NOW() - INTERVAL '6 months';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 添加注释
COMMENT ON INDEX idx_ai_usage_logs_created_at_desc IS '优化按时间倒序查询性能';
COMMENT ON INDEX idx_ai_usage_logs_agent_created IS '优化按AI员工+时间查询';
COMMENT ON INDEX idx_ai_usage_logs_provider_created IS '优化按提供商+时间查询';
COMMENT ON INDEX idx_ai_usage_logs_model_created IS '优化按模型+时间查询';
COMMENT ON FUNCTION cleanup_old_ai_usage_logs IS '清理6个月前的AI用量日志数据';
