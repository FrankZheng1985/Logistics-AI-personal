-- 042_add_performance_indexes.sql
-- 添加性能优化索引
-- 执行前请确保数据库已备份

-- ========================================
-- 1. assistant_schedules 表索引
-- ========================================
-- 用于日期范围查询（替代 DATE(start_time) 函数调用）
CREATE INDEX IF NOT EXISTS idx_assistant_schedules_start_time 
ON assistant_schedules(start_time);

-- 用户日程查询
CREATE INDEX IF NOT EXISTS idx_assistant_schedules_user_date 
ON assistant_schedules(user_id, start_time);

-- ========================================
-- 2. email_logs 表索引
-- ========================================
-- 按客户查询邮件历史
CREATE INDEX IF NOT EXISTS idx_email_logs_customer_id 
ON email_logs(customer_id);

-- 按状态和时间查询
CREATE INDEX IF NOT EXISTS idx_email_logs_status_created 
ON email_logs(status, created_at DESC);

-- 按收件人查询
CREATE INDEX IF NOT EXISTS idx_email_logs_to_email 
ON email_logs(to_email);

-- ========================================
-- 3. conversations 表索引
-- ========================================
-- 客户对话历史查询（按时间倒序）
CREATE INDEX IF NOT EXISTS idx_conversations_customer_created 
ON conversations(customer_id, created_at DESC);

-- 会话来源查询
CREATE INDEX IF NOT EXISTS idx_conversations_source 
ON conversations(source);

-- ========================================
-- 4. customers 表索引
-- ========================================
-- 跟进任务查询优化
CREATE INDEX IF NOT EXISTS idx_customers_follow_query 
ON customers(is_active, intent_level, last_contact_at)
WHERE is_active = true;

-- 下次跟进时间查询
CREATE INDEX IF NOT EXISTS idx_customers_next_follow 
ON customers(next_follow_at)
WHERE is_active = true AND next_follow_at IS NOT NULL;

-- 客户等级查询
CREATE INDEX IF NOT EXISTS idx_customers_intent_level 
ON customers(intent_level)
WHERE is_active = true;

-- ========================================
-- 5. email_cache 表索引
-- ========================================
-- 按账户和时间查询未读邮件
CREATE INDEX IF NOT EXISTS idx_email_cache_account_received 
ON email_cache(account_id, received_at DESC);

-- 重要邮件查询
CREATE INDEX IF NOT EXISTS idx_email_cache_important 
ON email_cache(is_important, received_at DESC)
WHERE is_important = true;

-- ========================================
-- 6. ai_usage_logs 表索引
-- ========================================
-- 按时间范围统计用量
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created 
ON ai_usage_logs(created_at DESC);

-- 按 Agent 统计用量
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_agent 
ON ai_usage_logs(agent_name, created_at DESC);

-- 按 Provider 统计用量
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_provider 
ON ai_usage_logs(provider, created_at DESC);

-- ========================================
-- 7. task_queue 表索引（任务队列）
-- ========================================
-- 待处理任务查询（复合索引优化）
CREATE INDEX IF NOT EXISTS idx_task_queue_pending_priority 
ON task_queue(status, priority DESC, created_at)
WHERE status = 'pending';

-- 按类型查询任务
CREATE INDEX IF NOT EXISTS idx_task_queue_type_status 
ON task_queue(task_type, status);

-- 计划任务查询
CREATE INDEX IF NOT EXISTS idx_task_queue_scheduled_pending 
ON task_queue(scheduled_at)
WHERE status = 'pending' AND scheduled_at IS NOT NULL;

-- 分配给指定 AI 员工的任务
CREATE INDEX IF NOT EXISTS idx_task_queue_assigned 
ON task_queue(assigned_to, status)
WHERE assigned_to IS NOT NULL;

-- ========================================
-- 8. erp_access_audit 表索引
-- ========================================
-- 审计日志查询
CREATE INDEX IF NOT EXISTS idx_erp_audit_endpoint_time 
ON erp_access_audit(endpoint, created_at DESC);

-- 按用户查询
CREATE INDEX IF NOT EXISTS idx_erp_audit_user 
ON erp_access_audit(user_id, created_at DESC);

-- ========================================
-- 9. hot_topics 表索引
-- ========================================
-- 热门话题查询
CREATE INDEX IF NOT EXISTS idx_hot_topics_platform_created 
ON hot_topics(platform, created_at DESC);

-- ========================================
-- 输出创建结果
-- ========================================
DO $$
BEGIN
    RAISE NOTICE '✅ 性能优化索引创建完成';
    RAISE NOTICE '建议：运行 ANALYZE 更新统计信息';
END $$;

-- 更新统计信息（可选，在低峰期执行）
-- ANALYZE assistant_schedules;
-- ANALYZE email_logs;
-- ANALYZE conversations;
-- ANALYZE customers;
-- ANALYZE email_cache;
-- ANALYZE ai_usage_logs;
-- ANALYZE tasks;
-- ANALYZE erp_access_audit;
-- ANALYZE hot_topics;
