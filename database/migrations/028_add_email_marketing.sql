-- 028_add_email_marketing.sql
-- 邮件营销功能：邮件模板和发送记录

-- 1. 邮件模板表
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 模板信息
    name VARCHAR(100) NOT NULL,                -- 模板名称
    template_type VARCHAR(50) NOT NULL,        -- 模板类型: follow_up, promotion, welcome, reactivate
    subject VARCHAR(200) NOT NULL,             -- 邮件主题
    html_content TEXT NOT NULL,                -- HTML内容
    text_content TEXT,                         -- 纯文本内容（可选）
    
    -- 模板变量说明（JSON格式）
    -- 支持的变量: {{customer_name}}, {{company}}, {{company_name}}, {{product}}, {{offer}}
    variables JSONB DEFAULT '[]'::jsonb,
    
    -- 状态
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,          -- 是否为默认模板
    
    -- 使用统计
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 邮件发送记录表
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 关联
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    follow_record_id UUID REFERENCES follow_records(id) ON DELETE SET NULL,
    
    -- 邮件信息
    to_email VARCHAR(100) NOT NULL,            -- 收件人邮箱
    subject VARCHAR(200) NOT NULL,             -- 邮件主题
    content TEXT NOT NULL,                     -- 发送的实际内容
    
    -- 发送状态
    status VARCHAR(20) DEFAULT 'pending',      -- pending, sent, failed, bounced, opened, clicked
    
    -- 发送者（AI员工或人工）
    sender_type VARCHAR(20) DEFAULT 'ai',      -- ai, manual
    sender_name VARCHAR(50),                   -- 小跟, 小销, 张三
    
    -- 发送结果
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- 邮件追踪
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    last_opened_at TIMESTAMP WITH TIME ZONE,
    last_clicked_at TIMESTAMP WITH TIME ZONE,
    
    -- 扩展数据
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS idx_email_logs_customer_id ON email_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_email_templates_type ON email_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_email_templates_active ON email_templates(is_active);

-- 4. 插入默认邮件模板
INSERT INTO email_templates (name, template_type, subject, html_content, text_content, variables, is_default) VALUES
-- 首次跟进模板
(
    '首次跟进邮件',
    'follow_up',
    '感谢您关注我们的物流服务 - {{company_name}}',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #2563eb; font-size: 24px; margin-bottom: 20px; }
        .content { line-height: 1.8; color: #333; }
        .highlight { background: #e0f2fe; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .cta { display: inline-block; background: #2563eb; color: white; padding: 12px 24px; border-radius: 5px; text-decoration: none; margin-top: 20px; }
        .footer { color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">您好，{{customer_name}}！</div>
        <div class="content">
            <p>感谢您关注{{company_name}}的物流服务。</p>
            <p>我们是一家专业的跨境物流服务商，专注于为客户提供安全、高效、经济的物流解决方案。</p>
            <div class="highlight">
                <strong>我们的优势：</strong>
                <ul>
                    <li>全球覆盖200+国家和地区</li>
                    <li>多种运输方式灵活选择</li>
                    <li>实时在线追踪</li>
                    <li>专业的客服团队7x24小时服务</li>
                </ul>
            </div>
            <p>如果您有任何物流需求，欢迎随时联系我们，我们将竭诚为您服务。</p>
            <a href="#" class="cta">了解更多服务</a>
        </div>
        <div class="footer">
            <p>{{company_name}} | 您的可靠物流伙伴</p>
            <p>如不需要此类邮件，请回复"退订"</p>
        </div>
    </div>
</body>
</html>',
    '您好，{{customer_name}}！

感谢您关注{{company_name}}的物流服务。

我们是一家专业的跨境物流服务商，专注于为客户提供安全、高效、经济的物流解决方案。

我们的优势：
- 全球覆盖200+国家和地区
- 多种运输方式灵活选择
- 实时在线追踪
- 专业的客服团队7x24小时服务

如果您有任何物流需求，欢迎随时联系我们，我们将竭诚为您服务。

---
{{company_name}} | 您的可靠物流伙伴',
    '["customer_name", "company_name"]',
    true
),
-- 报价跟进模板
(
    '报价跟进邮件',
    'follow_up',
    '关于您的物流报价咨询 - {{company_name}}',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #059669; font-size: 24px; margin-bottom: 20px; }
        .content { line-height: 1.8; color: #333; }
        .price-box { background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #059669; }
        .cta { display: inline-block; background: #059669; color: white; padding: 12px 24px; border-radius: 5px; text-decoration: none; margin-top: 20px; }
        .footer { color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">{{customer_name}}，您好！</div>
        <div class="content">
            <p>之前您咨询过我们的物流报价，不知道您对方案还有什么疑问吗？</p>
            <div class="price-box">
                <p><strong>温馨提示：</strong></p>
                <p>我们可以根据您的具体需求提供定制化报价，包括但不限于：</p>
                <ul>
                    <li>货物类型和重量</li>
                    <li>出发地和目的地</li>
                    <li>时效要求</li>
                    <li>特殊服务需求</li>
                </ul>
            </div>
            <p>如果您有任何问题或需要进一步的方案调整，随时可以联系我们。</p>
            <a href="#" class="cta">获取最新报价</a>
        </div>
        <div class="footer">
            <p>{{company_name}} | 您的可靠物流伙伴</p>
            <p>如不需要此类邮件，请回复"退订"</p>
        </div>
    </div>
</body>
</html>',
    '{{customer_name}}，您好！

之前您咨询过我们的物流报价，不知道您对方案还有什么疑问吗？

我们可以根据您的具体需求提供定制化报价，包括：
- 货物类型和重量
- 出发地和目的地
- 时效要求
- 特殊服务需求

如果您有任何问题或需要进一步的方案调整，随时可以联系我们。

---
{{company_name}} | 您的可靠物流伙伴',
    '["customer_name", "company_name"]',
    false
),
-- 沉默客户激活模板
(
    '沉默客户激活邮件',
    'reactivate',
    '好久不见，{{customer_name}}！我们有新优惠 - {{company_name}}',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #dc2626; font-size: 24px; margin-bottom: 20px; }
        .content { line-height: 1.8; color: #333; }
        .offer-box { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }
        .offer-text { font-size: 28px; font-weight: bold; color: #dc2626; }
        .cta { display: inline-block; background: #dc2626; color: white; padding: 12px 24px; border-radius: 5px; text-decoration: none; margin-top: 20px; }
        .footer { color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">{{customer_name}}，好久不见！</div>
        <div class="content">
            <p>距离我们上次联系已经有一段时间了，您是否还在寻找可靠的物流合作伙伴呢？</p>
            <div class="offer-box">
                <p style="margin:0;color:#92400e;">限时优惠</p>
                <p class="offer-text">新客户首单9折</p>
                <p style="margin:0;color:#92400e;">活动截止至月底</p>
            </div>
            <p>无论您需要空运、海运还是陆运服务，我们都能为您提供最优质的解决方案。</p>
            <p>期待与您再次合作！</p>
            <a href="#" class="cta">立即咨询</a>
        </div>
        <div class="footer">
            <p>{{company_name}} | 您的可靠物流伙伴</p>
            <p>如不需要此类邮件，请回复"退订"</p>
        </div>
    </div>
</body>
</html>',
    '{{customer_name}}，好久不见！

距离我们上次联系已经有一段时间了，您是否还在寻找可靠的物流合作伙伴呢？

【限时优惠】新客户首单9折，活动截止至月底！

无论您需要空运、海运还是陆运服务，我们都能为您提供最优质的解决方案。

期待与您再次合作！

---
{{company_name}} | 您的可靠物流伙伴',
    '["customer_name", "company_name"]',
    false
),
-- 促销推送模板
(
    '促销活动邮件',
    'promotion',
    '🎉 {{company_name}}特惠活动：{{offer}}',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { color: #7c3aed; font-size: 24px; margin-bottom: 20px; text-align: center; }
        .content { line-height: 1.8; color: #333; }
        .promo-box { background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%); color: white; padding: 30px; border-radius: 12px; margin: 20px 0; text-align: center; }
        .promo-title { font-size: 32px; font-weight: bold; margin-bottom: 10px; }
        .promo-desc { font-size: 16px; opacity: 0.9; }
        .cta { display: inline-block; background: white; color: #7c3aed; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: bold; margin-top: 15px; }
        .footer { color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">🎉 限时特惠活动</div>
        <div class="content">
            <p>亲爱的{{customer_name}}：</p>
            <div class="promo-box">
                <div class="promo-title">{{offer}}</div>
                <div class="promo-desc">活动期间下单即可享受</div>
                <a href="#" class="cta">立即参与</a>
            </div>
            <p>活动说明：</p>
            <ul>
                <li>活动时间有限，先到先得</li>
                <li>与其他优惠不可叠加</li>
                <li>最终解释权归{{company_name}}所有</li>
            </ul>
        </div>
        <div class="footer">
            <p>{{company_name}} | 您的可靠物流伙伴</p>
            <p>如不需要此类邮件，请回复"退订"</p>
        </div>
    </div>
</body>
</html>',
    '亲爱的{{customer_name}}：

🎉 限时特惠活动

{{offer}}

活动说明：
- 活动时间有限，先到先得
- 与其他优惠不可叠加
- 最终解释权归{{company_name}}所有

---
{{company_name}} | 您的可靠物流伙伴',
    '["customer_name", "company_name", "offer"]',
    false
)
ON CONFLICT DO NOTHING;

-- 5. 更新follow_records表，添加邮件关联字段（如果还没有）
ALTER TABLE follow_records 
ADD COLUMN IF NOT EXISTS email_log_id UUID REFERENCES email_logs(id);

COMMENT ON TABLE email_templates IS '邮件模板表';
COMMENT ON TABLE email_logs IS '邮件发送记录表';
COMMENT ON COLUMN email_templates.template_type IS '模板类型: follow_up(跟进), promotion(促销), welcome(欢迎), reactivate(激活)';
COMMENT ON COLUMN email_logs.status IS '发送状态: pending(待发送), sent(已发送), failed(失败), bounced(退信), opened(已打开), clicked(已点击)';
