-- 039_add_meeting_created_by.sql
-- 添加会议记录创建者字段

-- 添加created_by字段到meeting_records表
ALTER TABLE meeting_records 
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100);

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_meeting_records_created_by ON meeting_records(created_by);

COMMENT ON COLUMN meeting_records.created_by IS '创建者企业微信用户ID';

SELECT '会议记录创建者字段添加完成' AS message;
