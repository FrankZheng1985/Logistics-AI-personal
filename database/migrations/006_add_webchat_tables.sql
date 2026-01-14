-- 网站在线客服相关表

-- 会话表
CREATE TABLE IF NOT EXISTS webchat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id),
    status VARCHAR(50) DEFAULT 'active', -- active, closed, converted
    visitor_info JSONB DEFAULT '{}'::jsonb, -- IP, 浏览器, 来源页面等
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webchat_sessions_session_id ON webchat_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_webchat_sessions_status ON webchat_sessions (status);
CREATE INDEX IF NOT EXISTS idx_webchat_sessions_started_at ON webchat_sessions (started_at);

-- 消息表
CREATE TABLE IF NOT EXISTS webchat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    sender VARCHAR(50) NOT NULL, -- 'user' 或 'ai'
    message_type VARCHAR(50) DEFAULT 'text', -- text, image, file, system
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webchat_messages_session_id ON webchat_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_webchat_messages_created_at ON webchat_messages (created_at);

-- 添加外键约束（允许NULL，因为session可能未保存时就有消息）
-- ALTER TABLE webchat_messages 
-- ADD CONSTRAINT fk_webchat_messages_session 
-- FOREIGN KEY (session_id) REFERENCES webchat_sessions(session_id) ON DELETE CASCADE;

COMMENT ON TABLE webchat_sessions IS '网站在线客服会话表';
COMMENT ON TABLE webchat_messages IS '网站在线客服消息表';
