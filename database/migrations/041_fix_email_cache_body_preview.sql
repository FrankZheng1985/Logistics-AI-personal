-- 041_fix_email_cache_body_preview.sql
-- 修复邮件缓存表：添加 body_preview 字段
-- 该字段存储邮件正文的简短预览（前200字符）

-- =====================================================
-- 1. 添加 body_preview 字段
-- =====================================================

ALTER TABLE email_cache 
ADD COLUMN IF NOT EXISTS body_preview VARCHAR(300);

COMMENT ON COLUMN email_cache.body_preview IS '邮件正文预览（前200字符）';

-- =====================================================
-- 2. 为现有邮件生成 body_preview
-- =====================================================

UPDATE email_cache
SET body_preview = LEFT(
    REGEXP_REPLACE(
        COALESCE(body_text, ''), 
        E'\\s+', 
        ' ', 
        'g'
    ), 
    200
)
WHERE body_preview IS NULL;

-- =====================================================
-- 完成
-- =====================================================

SELECT '邮件缓存表 body_preview 字段添加完成' AS message;
