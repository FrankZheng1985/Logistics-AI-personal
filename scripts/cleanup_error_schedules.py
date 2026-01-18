#!/usr/bin/env python3
"""清理错误的日程记录"""
import asyncio
import sys
import os

# 添加backend目录到路径
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def cleanup():
    async with AsyncSessionLocal() as db:
        # 查询错误的记录
        result = await db.execute(
            text("""
                SELECT id, title, start_time 
                FROM assistant_schedules 
                WHERE title = '查询今日日程安排' OR title IS NULL
                ORDER BY created_at DESC
            """)
        )
        records = result.fetchall()
        
        if not records:
            print("✅ 没有找到错误记录")
            return
        
        print(f"📋 找到 {len(records)} 条错误记录：")
        for r in records:
            print(f"  ID: {r[0]}, 标题: {r[1]}, 时间: {r[2]}")
        
        # 删除这些记录
        result = await db.execute(
            text("DELETE FROM assistant_schedules WHERE title = '查询今日日程安排' OR title IS NULL")
        )
        await db.commit()
        
        print(f"\n✅ 已删除 {result.rowcount} 条错误记录")

if __name__ == "__main__":
    asyncio.run(cleanup())
