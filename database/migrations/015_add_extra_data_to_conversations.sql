-- Migration: 015_add_extra_data_to_conversations
-- Description: 添加 extra_data 字段到 conversations 表
-- Date: 2026-01-15

-- 添加 extra_data 列到 conversations 表
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS extra_data JSONB DEFAULT '{}';

-- 添加注释
COMMENT ON COLUMN conversations.extra_data IS '额外数据，如消息元数据等';
