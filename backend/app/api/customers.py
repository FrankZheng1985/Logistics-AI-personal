"""
客户管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models import get_db, Customer, IntentLevel, CustomerSource
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListResponse

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    intent_level: Optional[IntentLevel] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取客户列表"""
    query = select(Customer).where(Customer.is_active == True)
    
    # 筛选条件
    if intent_level:
        query = query.where(Customer.intent_level == intent_level)
    
    if search:
        query = query.where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Customer.company.ilike(f"%{search}%")
            )
        )
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.order_by(Customer.intent_score.desc(), Customer.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return {
        "items": customers,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/high-intent")
async def get_high_intent_customers(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取高意向客户列表"""
    query = (
        select(Customer)
        .where(Customer.intent_level.in_([IntentLevel.S, IntentLevel.A]))
        .where(Customer.is_active == True)
        .order_by(Customer.intent_score.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return {
        "customers": [
            {
                "id": str(c.id),
                "name": c.name,
                "company": c.company,
                "intent_score": c.intent_score,
                "intent_level": c.intent_level.value,
                "phone": c.phone,
                "last_contact_at": c.last_contact_at.isoformat() if c.last_contact_at else None
            }
            for c in customers
        ]
    }


@router.get("/{customer_id}")
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取客户详情"""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    return customer


@router.post("", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新客户"""
    customer = Customer(**customer_data.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新客户信息"""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    await db.commit()
    await db.refresh(customer)
    return customer


@router.post("/{customer_id}/update-intent")
async def update_customer_intent(
    customer_id: UUID,
    delta: int,
    reason: str = "",
    db: AsyncSession = Depends(get_db)
):
    """更新客户意向分数"""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    old_score = customer.intent_score
    old_level = customer.intent_level
    
    customer.intent_score = max(0, customer.intent_score + delta)
    customer.update_intent_level()
    
    await db.commit()
    
    return {
        "customer_id": str(customer_id),
        "old_score": old_score,
        "new_score": customer.intent_score,
        "old_level": old_level.value,
        "new_level": customer.intent_level.value,
        "delta": delta,
        "reason": reason
    }


@router.post("/{customer_id}/mark-high-intent")
async def mark_high_intent(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """标记为高意向客户"""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    old_level = customer.intent_level
    
    # 直接设置为S级客户，分数提升到80+
    customer.intent_level = IntentLevel.S
    if customer.intent_score < 80:
        customer.intent_score = 80
    
    await db.commit()
    
    return {
        "message": "已标记为高意向客户",
        "customer_id": str(customer_id),
        "old_level": old_level.value,
        "new_level": customer.intent_level.value,
        "new_score": customer.intent_score
    }


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """删除客户（软删除）"""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 软删除
    customer.is_active = False
    await db.commit()
    
    return {
        "message": "客户已删除",
        "customer_id": str(customer_id)
    }
