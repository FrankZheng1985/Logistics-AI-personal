"""
客户相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.customer import IntentLevel, CustomerSource


class CustomerBase(BaseModel):
    """客户基础模型"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat_id: Optional[str] = None
    company: Optional[str] = None
    source: CustomerSource = CustomerSource.OTHER
    source_detail: Optional[str] = None
    tags: List[str] = []
    cargo_types: Optional[List[str]] = None
    routes: Optional[List[str]] = None
    estimated_volume: Optional[str] = None


class CustomerCreate(CustomerBase):
    """创建客户"""
    pass


class CustomerUpdate(BaseModel):
    """更新客户"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat_id: Optional[str] = None
    company: Optional[str] = None
    tags: Optional[List[str]] = None
    cargo_types: Optional[List[str]] = None
    routes: Optional[List[str]] = None
    estimated_volume: Optional[str] = None
    next_follow_at: Optional[datetime] = None
    language: Optional[str] = None  # 语言偏好: auto, zh, en


class CustomerResponse(CustomerBase):
    """客户响应"""
    id: UUID
    intent_score: int
    intent_level: IntentLevel
    follow_count: int
    last_contact_at: Optional[datetime]
    next_follow_at: Optional[datetime]
    language: str = "auto"  # 语言偏好
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """客户列表响应"""
    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
