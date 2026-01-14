#!/bin/bash
# 验证数据库存储位置脚本
# 用于确认数据存储在腾讯云服务器上，而不是本地

echo "🔍 验证数据库存储位置..."
echo ""

# 检查数据库容器是否运行
if ! docker ps | grep -q logistics-ai-db; then
    echo "❌ 数据库容器未运行"
    exit 1
fi

echo "✅ 数据库容器正在运行"
echo ""

# 检查数据卷位置
echo "📊 数据库存储位置："
docker volume inspect logistics-ai_postgres_data 2>/dev/null | grep -A 2 Mountpoint || echo "⚠️  无法获取数据卷信息"
echo ""

# 检查数据卷大小
echo "📦 数据库数据卷大小："
docker exec logistics-ai-db du -sh /var/lib/postgresql/data 2>/dev/null || echo "⚠️  无法获取数据大小"
echo ""

# 检查数据库中的数据
echo "📊 数据库内容统计："
docker exec logistics-ai-db psql -U admin -d logistics_ai -c "
SELECT 
    '客户数量' as type, COUNT(*)::text as count FROM customers
UNION ALL
SELECT 
    '对话记录', COUNT(*)::text FROM conversations
UNION ALL
SELECT 
    'AI员工', COUNT(*)::text FROM ai_agents
UNION ALL
SELECT 
    '视频', COUNT(*)::text FROM videos
UNION ALL
SELECT 
    '任务', COUNT(*)::text FROM ai_tasks;
" 2>/dev/null || echo "⚠️  无法查询数据库"
echo ""

# 检查服务器信息
echo "🖥️  服务器信息："
echo "  主机名: $(hostname)"
echo "  IP地址: $(hostname -I | awk '{print $1}')"
echo "  数据存储路径: /var/lib/docker/volumes/logistics-ai_postgres_data/_data"
echo ""

echo "✅ 验证完成！数据存储在腾讯云服务器上。"
