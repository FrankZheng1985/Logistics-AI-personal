-- 修复 leads 表的 source_url 唯一索引问题
-- 原来的部分索引无法支持 ON CONFLICT (source_url) 语法
-- 需要改为普通唯一索引

-- 删除旧的部分唯一索引
DROP INDEX IF EXISTS idx_leads_source_url_unique;

-- 创建新的普通唯一索引（允许 NULL，因为 PostgreSQL 的 UNIQUE 索引允许多个 NULL）
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_source_url ON leads(source_url);

-- 确保 lead_hunt_searched_urls 表的 url_hash 有唯一约束
-- 检查是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'lead_hunt_searched_urls_url_hash_key'
    ) THEN
        ALTER TABLE lead_hunt_searched_urls 
        ADD CONSTRAINT lead_hunt_searched_urls_url_hash_unique UNIQUE (url_hash);
    END IF;
END $$;

-- 添加注释
COMMENT ON INDEX idx_leads_source_url IS '线索来源URL唯一索引，用于ON CONFLICT去重';
