"""
ERP业务系统对接API
负责：提供ERP数据查询接口（只读）

安全说明：
- 所有接口都是只读操作
- 不提供任何写入、修改、删除操作
- 数据来源于ERP系统的只读API账户
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger

from app.services.erp_connector import (
    erp_connector, 
    erp_config_manager,
    ERPConnectionError,
    ERPAuthenticationError,
    ERPPermissionError
)

router = APIRouter(tags=["ERP业务系统"])


# ========== 请求/响应模型 ==========

class ERPConfigRequest(BaseModel):
    """ERP配置请求"""
    api_url: str = Field(..., description="ERP API地址", example="https://api.xianfeng-eu.com")
    auth_type: str = Field(..., description="认证类型: bearer/x_api_key", example="bearer")
    auth_token: str = Field(..., description="认证令牌/密钥 (如: sk_read_xxx)")
    username: Optional[str] = Field(None, description="客户端ID（可选，如: readonly_client）")
    description: Optional[str] = Field(None, description="配置描述")


class ERPConfigResponse(BaseModel):
    """ERP配置响应"""
    id: Optional[str] = None
    api_url: Optional[str] = None
    auth_type: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TestConnectionResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    api_url: Optional[str] = None


class SyncLogResponse(BaseModel):
    """同步日志响应"""
    id: str
    endpoint: str
    params: Optional[str] = None
    success: bool
    error: Optional[str] = None
    created_at: Optional[str] = None


# ========== 配置管理接口 ==========

@router.get("/config", response_model=ERPConfigResponse, summary="获取ERP配置")
async def get_erp_config():
    """获取当前ERP连接配置（不返回敏感信息）"""
    config = await erp_config_manager.get_config()
    if config:
        return ERPConfigResponse(**config)
    return ERPConfigResponse()


@router.post("/config", summary="保存ERP配置")
async def save_erp_config(config: ERPConfigRequest):
    """保存ERP连接配置"""
    success = await erp_config_manager.save_config(
        api_url=config.api_url,
        auth_type=config.auth_type,
        auth_token=config.auth_token,
        username=config.username,
        description=config.description
    )
    
    if success:
        # 重新初始化连接器
        await erp_connector.initialize()
        return {"message": "ERP配置已保存", "success": True}
    
    raise HTTPException(status_code=500, detail="保存配置失败")


@router.post("/test-connection", response_model=TestConnectionResponse, summary="测试ERP连接")
async def test_erp_connection():
    """测试ERP系统连接"""
    result = await erp_connector.test_connection()
    return TestConnectionResponse(**result)


@router.get("/logs", response_model=List[SyncLogResponse], summary="获取同步日志")
async def get_sync_logs(limit: int = Query(50, ge=1, le=200)):
    """获取ERP数据同步日志"""
    logs = await erp_config_manager.get_sync_logs(limit)
    return [SyncLogResponse(**log) for log in logs]


@router.post("/clear-cache", summary="清除缓存")
async def clear_erp_cache():
    """清除ERP数据缓存"""
    success = await erp_config_manager.clear_cache()
    if success:
        return {"message": "缓存已清除", "success": True}
    raise HTTPException(status_code=500, detail="清除缓存失败")


# ========== 订单查询接口（只读） ==========

@router.get("/orders", summary="获取订单列表")
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="订单状态"),
    customer_id: Optional[str] = Query(None, description="客户ID"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD")
):
    """
    获取ERP订单列表
    
    这是只读接口，只能查询订单信息，不能修改订单。
    """
    try:
        data = await erp_connector.get_orders(
            page=page,
            page_size=page_size,
            status=status,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ERPAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"获取订单失败: {e}")
        raise HTTPException(status_code=500, detail="获取订单失败")


@router.get("/orders/{order_id}", summary="获取订单详情")
async def get_order_detail(order_id: str):
    """
    获取单个订单详情
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_order_detail(order_id)
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取订单详情失败")


@router.get("/orders-stats", summary="获取订单统计")
async def get_orders_stats():
    """
    获取订单统计数据
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_orders_stats()
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取订单统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取订单统计失败")


# ========== 报价查询接口（只读） ==========

@router.get("/quotes", summary="获取报价列表")
async def get_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[str] = Query(None, description="客户ID"),
    status: Optional[str] = Query(None, description="报价状态")
):
    """
    获取ERP报价列表
    
    这是只读接口，只能查询报价信息，不能创建或修改报价。
    """
    try:
        data = await erp_connector.get_quotes(
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            status=status
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取报价失败: {e}")
        raise HTTPException(status_code=500, detail="获取报价失败")


@router.get("/pricing", summary="获取产品定价")
async def get_product_pricing(
    route_from: Optional[str] = Query(None, description="起始地"),
    route_to: Optional[str] = Query(None, description="目的地"),
    transport_type: Optional[str] = Query(None, description="运输类型: sea/air/rail")
):
    """
    获取产品定价信息
    
    这是只读接口，用于查询运输线路的参考价格。
    """
    try:
        data = await erp_connector.get_product_pricing(
            route_from=route_from,
            route_to=route_to,
            transport_type=transport_type
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取定价失败: {e}")
        raise HTTPException(status_code=500, detail="获取定价失败")


# ========== 客户查询接口（只读） ==========

@router.get("/customers", summary="获取客户列表")
async def get_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    level: Optional[str] = Query(None, description="客户级别")
):
    """
    获取ERP客户列表
    
    这是只读接口，只能查询客户信息，不能修改客户资料。
    """
    try:
        data = await erp_connector.get_customers(
            page=page,
            page_size=page_size,
            keyword=keyword,
            level=level
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取客户失败: {e}")
        raise HTTPException(status_code=500, detail="获取客户失败")


@router.get("/customers/{customer_id}", summary="获取客户详情")
async def get_customer_detail(customer_id: str):
    """
    获取单个客户详情
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_customer_detail(customer_id)
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取客户详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取客户详情失败")


# ========== 运输/物流查询接口（只读） ==========

@router.get("/shipments", summary="获取运输列表")
async def get_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="运输状态"),
    order_id: Optional[str] = Query(None, description="订单ID")
):
    """
    获取运输/物流状态列表
    
    这是只读接口，用于查询货物运输状态。
    """
    try:
        data = await erp_connector.get_shipments(
            page=page,
            page_size=page_size,
            status=status,
            order_id=order_id
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取运输信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取运输信息失败")


@router.get("/shipments/{shipment_id}/tracking", summary="获取物流跟踪")
async def get_shipment_tracking(shipment_id: str):
    """
    获取物流跟踪详情
    
    这是只读接口，用于查询货物的实时跟踪信息。
    """
    try:
        data = await erp_connector.get_shipment_tracking(shipment_id)
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取物流跟踪失败: {e}")
        raise HTTPException(status_code=500, detail="获取物流跟踪失败")


# ========== 财务查询接口（只读） ==========

@router.get("/finance/summary", summary="获取财务概览")
async def get_finance_summary(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD")
):
    """
    获取财务概览数据
    
    这是只读接口，用于查询财务汇总信息。
    """
    try:
        data = await erp_connector.get_finance_summary(
            start_date=start_date,
            end_date=end_date
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取财务概览失败: {e}")
        raise HTTPException(status_code=500, detail="获取财务概览失败")


@router.get("/finance/invoices", summary="获取发票列表")
async def get_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="发票状态"),
    customer_id: Optional[str] = Query(None, description="客户ID")
):
    """
    获取发票列表
    
    这是只读接口，只能查询发票信息。
    """
    try:
        data = await erp_connector.get_invoices(
            page=page,
            page_size=page_size,
            status=status,
            customer_id=customer_id
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取发票失败: {e}")
        raise HTTPException(status_code=500, detail="获取发票失败")


@router.get("/finance/invoices/{invoice_id}", summary="获取发票详情")
async def get_invoice_detail(invoice_id: str):
    """
    获取发票详情
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_invoice_detail(invoice_id)
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取发票详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取发票详情失败")


@router.get("/finance/payments", summary="获取付款记录")
async def get_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="付款状态"),
    customer_id: Optional[str] = Query(None, description="客户ID")
):
    """
    获取付款记录列表
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_payments(
            page=page,
            page_size=page_size,
            status=status,
            customer_id=customer_id
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取付款记录失败: {e}")
        raise HTTPException(status_code=500, detail="获取付款记录失败")


@router.get("/finance/payments/{payment_id}", summary="获取付款详情")
async def get_payment_detail(payment_id: str):
    """
    获取付款详情
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_payment_detail(payment_id)
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取付款详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取付款详情失败")


@router.get("/finance/receivables", summary="获取应收账款")
async def get_receivables(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    overdue_only: bool = Query(False, description="只显示逾期账款")
):
    """
    获取应收账款列表
    
    这是只读接口，用于查询应收账款情况。
    """
    try:
        data = await erp_connector.get_receivables(
            page=page,
            page_size=page_size,
            overdue_only=overdue_only
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取应收账款失败: {e}")
        raise HTTPException(status_code=500, detail="获取应收账款失败")


# ========== 统计接口（只读） ==========

@router.get("/stats", summary="获取综合统计")
async def get_stats():
    """
    获取系统综合统计数据
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_stats()
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取综合统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取综合统计失败")


@router.get("/monthly-stats", summary="获取月度统计")
async def get_monthly_stats(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, ge=1, le=12, description="月份")
):
    """
    获取月度统计数据
    
    这是只读接口。
    """
    try:
        data = await erp_connector.get_monthly_stats(year=year, month=month)
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取月度统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取月度统计失败")


# ========== 供应商查询接口（只读） ==========

@router.get("/suppliers", summary="获取供应商列表")
async def get_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="供应商类别")
):
    """
    获取供应商列表
    
    这是只读接口，只能查询供应商信息。
    """
    try:
        data = await erp_connector.get_suppliers(
            page=page,
            page_size=page_size,
            category=category
        )
        return data
    except ERPConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"获取供应商失败: {e}")
        raise HTTPException(status_code=500, detail="获取供应商失败")
