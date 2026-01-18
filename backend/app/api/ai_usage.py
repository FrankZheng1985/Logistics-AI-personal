"""
AI用量监控API
提供用量统计、日志查询、告警配置、价格管理等功能
"""
from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.services.ai_usage_service import AIUsageService


router = APIRouter(prefix="/ai-usage", tags=["AI用量监控"])


# ==================== 请求/响应模型 ====================

class AlertCreate(BaseModel):
    """创建告警请求"""
    alert_name: str = Field(..., description="告警名称")
    alert_type: str = Field(..., description="告警类型: daily, weekly, monthly")
    threshold_amount: float = Field(..., gt=0, description="阈值金额（元）")
    threshold_tokens: Optional[int] = Field(None, description="阈值token数")
    notify_wechat: bool = Field(True, description="是否企业微信通知")
    notify_email: bool = Field(False, description="是否邮件通知")
    notify_users: Optional[str] = Field(None, description="通知用户列表")


class AlertUpdate(BaseModel):
    """更新告警请求"""
    alert_name: Optional[str] = None
    alert_type: Optional[str] = None
    threshold_amount: Optional[float] = None
    threshold_tokens: Optional[int] = None
    notify_wechat: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_users: Optional[str] = None
    is_active: Optional[bool] = None


class PricingUpdate(BaseModel):
    """更新价格请求"""
    input_price_per_1k: Optional[float] = Field(None, gt=0, description="输入价格（元/1000 tokens）")
    output_price_per_1k: Optional[float] = Field(None, gt=0, description="输出价格（元/1000 tokens）")
    is_active: Optional[bool] = None


# ==================== 用量统计API ====================

@router.get("/stats", summary="获取用量统计")
async def get_usage_stats(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    agent_name: Optional[str] = Query(None, description="AI员工名称"),
    provider: Optional[str] = Query(None, description="提供商")
):
    """
    获取AI用量统计数据
    
    返回：
    - 总体统计（请求数、token数、费用）
    - 按提供商统计
    - 按模型统计
    - 按AI员工统计
    - 每日趋势
    """
    try:
        stats = await AIUsageService.get_usage_stats(
            start_date=start_date,
            end_date=end_date,
            agent_name=agent_name,
            provider=provider
        )
        return stats
    except Exception as e:
        logger.error(f"获取用量统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today", summary="获取今日统计")
async def get_today_stats():
    """获取今日AI用量统计"""
    try:
        stats = await AIUsageService.get_today_stats()
        return stats
    except Exception as e:
        logger.error(f"获取今日统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", summary="获取仪表板数据")
async def get_dashboard_data():
    """
    获取用量监控仪表板数据
    
    包含：
    - 今日统计
    - 本周统计
    - 本月统计
    - 费用趋势
    - 告警状态
    """
    try:
        today = date.today()
        
        # 今日统计
        today_stats = await AIUsageService.get_today_stats()
        
        # 本周统计（从周一开始）
        week_start = today - __import__('datetime').timedelta(days=today.weekday())
        week_stats = await AIUsageService.get_usage_stats(start_date=week_start, end_date=today)
        
        # 本月统计
        month_start = today.replace(day=1)
        month_stats = await AIUsageService.get_usage_stats(start_date=month_start, end_date=today)
        
        # 获取告警配置
        alerts = await AIUsageService.get_alerts()
        active_alerts = [a for a in alerts if a["is_active"]]
        
        # 检查告警状态
        alert_status = []
        for alert in active_alerts:
            if alert["alert_type"] == "daily":
                current_cost = today_stats["summary"]["total_cost"]
            elif alert["alert_type"] == "weekly":
                current_cost = week_stats["summary"]["total_cost"]
            elif alert["alert_type"] == "monthly":
                current_cost = month_stats["summary"]["total_cost"]
            else:
                continue
            
            threshold = alert["threshold_amount"]
            percentage = (current_cost / threshold * 100) if threshold > 0 else 0
            
            alert_status.append({
                "name": alert["alert_name"],
                "type": alert["alert_type"],
                "threshold": threshold,
                "current": current_cost,
                "percentage": round(percentage, 1),
                "is_triggered": current_cost >= threshold
            })
        
        return {
            "today": {
                "requests": today_stats["summary"]["total_requests"],
                "tokens": today_stats["summary"]["total_tokens"],
                "cost": today_stats["summary"]["total_cost"],
                "success_rate": today_stats["summary"]["success_rate"]
            },
            "this_week": {
                "requests": week_stats["summary"]["total_requests"],
                "tokens": week_stats["summary"]["total_tokens"],
                "cost": week_stats["summary"]["total_cost"]
            },
            "this_month": {
                "requests": month_stats["summary"]["total_requests"],
                "tokens": month_stats["summary"]["total_tokens"],
                "cost": month_stats["summary"]["total_cost"]
            },
            "by_provider": today_stats.get("by_provider", []),
            "by_agent": today_stats.get("by_agent", []),
            "daily_trend": month_stats.get("daily_trend", []),
            "alert_status": alert_status
        }
        
    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 用量日志API ====================

@router.get("/logs", summary="获取用量日志")
async def get_usage_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    agent_name: Optional[str] = Query(None, description="AI员工名称"),
    provider: Optional[str] = Query(None, description="提供商"),
    model_name: Optional[str] = Query(None, description="模型名称"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """
    获取用量日志列表
    
    支持分页和多条件筛选
    """
    try:
        result = await AIUsageService.get_usage_logs(
            page=page,
            page_size=page_size,
            agent_name=agent_name,
            provider=provider,
            model_name=model_name,
            start_date=start_date,
            end_date=end_date
        )
        return result
    except Exception as e:
        logger.error(f"获取用量日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 告警配置API ====================

@router.get("/alerts", summary="获取告警配置列表")
async def get_alerts():
    """获取所有告警配置"""
    try:
        alerts = await AIUsageService.get_alerts()
        return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        logger.error(f"获取告警配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts", summary="创建告警配置")
async def create_alert(data: AlertCreate):
    """
    创建新的告警配置
    
    告警类型：
    - daily: 每日告警
    - weekly: 每周告警
    - monthly: 每月告警
    """
    try:
        if data.alert_type not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="告警类型必须是 daily, weekly 或 monthly")
        
        alert_id = await AIUsageService.create_alert(
            alert_name=data.alert_name,
            alert_type=data.alert_type,
            threshold_amount=data.threshold_amount,
            threshold_tokens=data.threshold_tokens,
            notify_wechat=data.notify_wechat,
            notify_email=data.notify_email,
            notify_users=data.notify_users
        )
        
        if alert_id:
            return {"message": "告警配置创建成功", "id": alert_id}
        else:
            raise HTTPException(status_code=500, detail="创建失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建告警配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/{alert_id}", summary="更新告警配置")
async def update_alert(alert_id: int, data: AlertUpdate):
    """更新告警配置"""
    try:
        update_data = data.model_dump(exclude_unset=True)
        
        if "alert_type" in update_data and update_data["alert_type"] not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="告警类型必须是 daily, weekly 或 monthly")
        
        success = await AIUsageService.update_alert(alert_id, **update_data)
        
        if success:
            return {"message": "告警配置更新成功"}
        else:
            raise HTTPException(status_code=404, detail="告警配置不存在或更新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{alert_id}", summary="删除告警配置")
async def delete_alert(alert_id: int):
    """删除告警配置"""
    try:
        success = await AIUsageService.delete_alert(alert_id)
        
        if success:
            return {"message": "告警配置删除成功"}
        else:
            raise HTTPException(status_code=404, detail="告警配置不存在")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/toggle", summary="切换告警启用状态")
async def toggle_alert(alert_id: int):
    """切换告警的启用/禁用状态"""
    try:
        # 先获取当前状态
        alerts = await AIUsageService.get_alerts()
        alert = next((a for a in alerts if a["id"] == alert_id), None)
        
        if not alert:
            raise HTTPException(status_code=404, detail="告警配置不存在")
        
        # 切换状态
        new_status = not alert["is_active"]
        success = await AIUsageService.update_alert(alert_id, is_active=new_status)
        
        if success:
            return {"message": f"告警已{'启用' if new_status else '禁用'}", "is_active": new_status}
        else:
            raise HTTPException(status_code=500, detail="切换失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换告警状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 价格配置API ====================

@router.get("/pricing", summary="获取模型价格配置")
async def get_model_pricing():
    """获取所有模型的价格配置"""
    try:
        pricing = await AIUsageService.get_model_pricing()
        return {"pricing": pricing, "total": len(pricing)}
    except Exception as e:
        logger.error(f"获取价格配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pricing/{pricing_id}", summary="更新模型价格配置")
async def update_model_pricing(pricing_id: int, data: PricingUpdate):
    """
    更新模型价格配置
    
    注意：价格单位为 元/1000 tokens
    """
    try:
        success = await AIUsageService.update_model_pricing(
            pricing_id=pricing_id,
            input_price_per_1k=data.input_price_per_1k,
            output_price_per_1k=data.output_price_per_1k,
            is_active=data.is_active
        )
        
        if success:
            return {"message": "价格配置更新成功"}
        else:
            raise HTTPException(status_code=404, detail="价格配置不存在或更新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新价格配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 费用估算API ====================

@router.post("/estimate", summary="估算API调用费用")
async def estimate_cost(
    provider: str = Query(..., description="提供商"),
    model_name: str = Query(..., description="模型名称"),
    input_tokens: int = Query(..., ge=0, description="输入token数"),
    output_tokens: int = Query(..., ge=0, description="输出token数")
):
    """
    估算API调用费用
    
    用于预估某次调用的费用
    """
    try:
        # 确保价格缓存已加载
        await AIUsageService._load_pricing_cache()
        
        cost = AIUsageService.calculate_cost(
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        return {
            "provider": provider,
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost": cost,
            "formatted_cost": f"¥{cost:.4f}"
        }
        
    except Exception as e:
        logger.error(f"费用估算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 导出API ====================

@router.get("/export", summary="导出用量数据")
async def export_usage_data(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    format: str = Query("json", description="导出格式: json 或 csv")
):
    """
    导出用量数据
    
    支持JSON和CSV格式
    """
    try:
        # 获取日志数据（最多10000条）
        result = await AIUsageService.get_usage_logs(
            page=1,
            page_size=10000,
            start_date=start_date,
            end_date=end_date
        )
        
        logs = result["logs"]
        
        if format == "csv":
            import csv
            import io
            from fastapi.responses import StreamingResponse
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "id", "created_at", "agent_name", "provider", "model_name",
                "input_tokens", "output_tokens", "total_tokens", "cost_estimate",
                "task_type", "response_time_ms", "is_success", "error_message"
            ])
            writer.writeheader()
            writer.writerows(logs)
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=ai_usage_{date.today().isoformat()}.csv"}
            )
        else:
            return {
                "export_date": datetime.now().isoformat(),
                "total_records": len(logs),
                "data": logs
            }
            
    except Exception as e:
        logger.error(f"导出用量数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
