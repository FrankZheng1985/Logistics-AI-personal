-- 026_add_brand_assets.sql
-- 添加品牌资产管理字段

-- 添加品牌资产字段（JSONB格式存储）
ALTER TABLE company_config ADD COLUMN IF NOT EXISTS brand_assets JSONB DEFAULT '{}';

-- 品牌资产结构说明:
-- {
--   "logo": {
--     "main": "主Logo URL/Base64",
--     "white": "白色版Logo（用于深色背景）",
--     "icon": "小图标版"
--   },
--   "qrcode": {
--     "wechat": "微信个人号二维码",
--     "wechat_official": "公众号二维码",
--     "douyin": "抖音二维码",
--     "xiaohongshu": "小红书二维码"
--   },
--   "watermark": {
--     "enabled": true,
--     "position": "bottom-right",
--     "opacity": 0.8,
--     "image": "水印图片URL"
--   },
--   "video_assets": {
--     "intro_video": "公司介绍视频URL",
--     "outro_template": "片尾模板URL"
--   }
-- }

COMMENT ON COLUMN company_config.brand_assets IS '品牌资产JSON，包含Logo、二维码、水印等';

-- 创建素材上传记录表（可选，用于跟踪上传历史）
CREATE TABLE IF NOT EXISTS brand_asset_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type VARCHAR(50) NOT NULL,  -- logo_main, logo_white, qrcode_wechat, etc.
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    storage_path TEXT,  -- 可以是URL或Base64
    uploaded_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_brand_asset_uploads_type ON brand_asset_uploads(asset_type);
CREATE INDEX IF NOT EXISTS idx_brand_asset_uploads_time ON brand_asset_uploads(uploaded_at DESC);
