"""
系统监控API
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import httpx
import ssl
import socket

from app.models.database import AsyncSessionLocal
from app.core.config import settings

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class AgentPerformance(BaseModel):
    agent_type: str
    agent_name: str
    tasks_today: int
    tasks_completed_today: int
    tasks_failed_today: int
    success_rate: float
    avg_response_time_ms: Optional[float]
    status: str


class APIStatus(BaseModel):
    api_name: str
    status: str
    response_time_ms: Optional[int]
    last_check: datetime
    error_message: Optional[str]


class CertificateStatus(BaseModel):
    domain: str
    issuer: str
    expires_at: datetime
    days_until_expiry: int
    status: str


class SystemOverview(BaseModel):
    total_customers: int
    new_customers_today: int
    total_conversations: int
    conversations_today: int
    total_videos: int
    videos_today: int
    system_uptime_hours: float


@router.get("/overview", response_model=SystemOverview)
async def get_system_overview():
    """获取系统概览"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            # 获取统计数据
            today = datetime.now().date()
            
            result = await db.execute(text("SELECT COUNT(*) FROM customers"))
            total_customers = result.scalar() or 0
            
            result = await db.execute(
                text("SELECT COUNT(*) FROM customers WHERE DATE(created_at) = :today"),
                {"today": today}
            )
            new_customers_today = result.scalar() or 0
            
            result = await db.execute(text("SELECT COUNT(*) FROM conversations"))
            total_conversations = result.scalar() or 0
            
            result = await db.execute(
                text("SELECT COUNT(*) FROM conversations WHERE DATE(created_at) = :today"),
                {"today": today}
            )
            conversations_today = result.scalar() or 0
            
            result = await db.execute(text("SELECT COUNT(*) FROM videos"))
            total_videos = result.scalar() or 0
            
            result = await db.execute(
                text("SELECT COUNT(*) FROM videos WHERE DATE(created_at) = :today"),
                {"today": today}
            )
            videos_today = result.scalar() or 0
            
            return SystemOverview(
                total_customers=total_customers,
                new_customers_today=new_customers_today,
                total_conversations=total_conversations,
                conversations_today=conversations_today,
                total_videos=total_videos,
                videos_today=videos_today,
                system_uptime_hours=24.0  # 需要实际实现
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=List[AgentPerformance])
async def get_agent_performance():
    """获取AI员工性能数据"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            today = datetime.now().date()
            
            result = await db.execute(text("""
                SELECT 
                    aa.agent_type,
                    aa.name,
                    aa.status,
                    COUNT(wl.id) as tasks_today,
                    SUM(CASE WHEN wl.status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN wl.status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(wl.duration_ms) as avg_duration
                FROM ai_agents aa
                LEFT JOIN work_logs wl ON aa.id = wl.agent_id AND DATE(wl.created_at) = :today
                GROUP BY aa.id, aa.agent_type, aa.name, aa.status
                ORDER BY aa.agent_type
            """), {"today": today})
            
            rows = result.fetchall()
            
            performances = []
            for row in rows:
                tasks = row[3] or 0
                completed = row[4] or 0
                success_rate = (completed / tasks * 100) if tasks > 0 else 0
                
                performances.append(AgentPerformance(
                    agent_type=row[0],
                    agent_name=row[1],
                    tasks_today=tasks,
                    tasks_completed_today=completed,
                    tasks_failed_today=row[5] or 0,
                    success_rate=success_rate,
                    avg_response_time_ms=row[6],
                    status=row[2]
                ))
            
            return performances
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-status", response_model=List[APIStatus])
async def check_api_status():
    """检查外部API状态"""
    apis_to_check = [
        {"name": "OpenAI/DeepSeek", "url": f"{settings.DEEPSEEK_API_BASE}/models", "headers": {"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"}},
        {"name": "Keling AI", "url": "https://api.klingai.com", "headers": {}},
    ]
    
    results = []
    
    for api in apis_to_check:
        status = "unknown"
        response_time = None
        error_msg = None
        
        try:
            start = datetime.now()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(api["url"], headers=api.get("headers", {}))
                response_time = int((datetime.now() - start).total_seconds() * 1000)
                
                if resp.status_code < 400:
                    status = "healthy"
                elif resp.status_code < 500:
                    status = "degraded"
                else:
                    status = "error"
        except httpx.TimeoutException:
            status = "timeout"
            error_msg = "请求超时"
        except Exception as e:
            status = "error"
            error_msg = str(e)
        
        results.append(APIStatus(
            api_name=api["name"],
            status=status,
            response_time_ms=response_time,
            last_check=datetime.now(),
            error_message=error_msg
        ))
    
    return results


@router.get("/certificates", response_model=List[CertificateStatus])
async def check_certificate_status():
    """检查SSL证书状态"""
    domains_to_check = [
        "api.openai.com",
        "api.deepseek.com",
    ]
    
    results = []
    
    for domain in domains_to_check:
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # 解析过期时间
                    expires_str = cert.get('notAfter', '')
                    expires_at = datetime.strptime(expires_str, '%b %d %H:%M:%S %Y %Z')
                    days_until = (expires_at - datetime.now()).days
                    
                    # 获取颁发者
                    issuer = dict(x[0] for x in cert.get('issuer', []))
                    issuer_name = issuer.get('organizationName', 'Unknown')
                    
                    status = "valid"
                    if days_until < 0:
                        status = "expired"
                    elif days_until < 30:
                        status = "expiring_soon"
                    
                    results.append(CertificateStatus(
                        domain=domain,
                        issuer=issuer_name,
                        expires_at=expires_at,
                        days_until_expiry=days_until,
                        status=status
                    ))
        except Exception as e:
            results.append(CertificateStatus(
                domain=domain,
                issuer="Unknown",
                expires_at=datetime.now(),
                days_until_expiry=0,
                status="error"
            ))
    
    return results


@router.post("/report")
async def generate_team_report(period: str = "daily"):
    """生成团队工作报告"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            # 确定时间范围
            if period == "daily":
                start_date = datetime.now().date()
            elif period == "weekly":
                start_date = datetime.now().date() - timedelta(days=7)
            elif period == "monthly":
                start_date = datetime.now().date() - timedelta(days=30)
            else:
                start_date = datetime.now().date()
            
            # 获取各项统计数据
            report = {
                "period": period,
                "generated_at": datetime.now().isoformat(),
                "overview": {},
                "agent_details": [],
                "api_status": [],
                "recommendations": []
            }
            
            # 概览数据
            result = await db.execute(
                text("SELECT COUNT(*) FROM customers WHERE created_at >= :start"),
                {"start": start_date}
            )
            report["overview"]["new_customers"] = result.scalar() or 0
            
            result = await db.execute(
                text("SELECT COUNT(*) FROM conversations WHERE created_at >= :start"),
                {"start": start_date}
            )
            report["overview"]["conversations"] = result.scalar() or 0
            
            result = await db.execute(
                text("SELECT COUNT(*) FROM videos WHERE created_at >= :start"),
                {"start": start_date}
            )
            report["overview"]["videos_created"] = result.scalar() or 0
            
            # AI员工详情
            result = await db.execute(text("""
                SELECT 
                    aa.name,
                    aa.agent_type,
                    COUNT(wl.id) as total_tasks,
                    SUM(CASE WHEN wl.status = 'completed' THEN 1 ELSE 0 END) as completed,
                    AVG(wl.duration_ms) as avg_duration,
                    aa.status
                FROM ai_agents aa
                LEFT JOIN work_logs wl ON aa.id = wl.agent_id AND wl.created_at >= :start
                GROUP BY aa.id
            """), {"start": start_date})
            
            for row in result.fetchall():
                total = row[2] or 0
                completed = row[3] or 0
                report["agent_details"].append({
                    "name": row[0],
                    "type": row[1],
                    "tasks": total,
                    "completed": completed,
                    "success_rate": f"{(completed/total*100):.1f}%" if total > 0 else "N/A",
                    "avg_duration_ms": row[4],
                    "status": row[5]
                })
            
            # 智能建议
            if report["overview"]["new_customers"] < 10:
                report["recommendations"].append("建议加强线索狩猎力度，增加新客户获取")
            if report["overview"]["videos_created"] == 0:
                report["recommendations"].append("视频产出为0，建议检查小影工作状态")
            
            return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
