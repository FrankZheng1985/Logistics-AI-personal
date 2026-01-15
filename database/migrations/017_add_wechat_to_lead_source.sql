-- 添加 wechat 到 lead_source 枚举类型
-- 执行日期: 2026-01-15

-- 检查并添加 wechat 枚举值
DO $$
BEGIN
    -- 检查枚举类型是否存在
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_source') THEN
        -- 检查 wechat 值是否已存在
        IF NOT EXISTS (
            SELECT 1 FROM pg_enum 
            WHERE enumtypid = 'lead_source'::regtype 
            AND enumlabel = 'wechat'
        ) THEN
            ALTER TYPE lead_source ADD VALUE 'wechat';
            RAISE NOTICE '已添加 wechat 到 lead_source 枚举';
        ELSE
            RAISE NOTICE 'wechat 已存在于 lead_source 枚举中';
        END IF;
    ELSE
        RAISE NOTICE 'lead_source 枚举类型不存在';
    END IF;
END $$;
