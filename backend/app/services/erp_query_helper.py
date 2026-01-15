"""
ERP查询辅助服务
供AI Agent使用，提供简化的ERP数据查询接口

安全说明：
- 所有操作都是只读的
- 数据来自erp_connector的缓存
- AI Agent只能查询，不能修改任何数据
"""
from typing import Dict, Any, Optional, List
from loguru import logger

from app.services.erp_connector import erp_connector, ERPConnectionError


class ERPQueryHelper:
    """
    ERP查询辅助类
    为AI Agent提供简化的数据查询接口
    """
    
    async def is_available(self) -> bool:
        """检查ERP连接是否可用"""
        try:
            result = await erp_connector.test_connection()
            return result.get("success", False)
        except:
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单状态（供AI Agent回答客户关于订单的问题）
        
        返回:
            订单信息摘要，适合AI理解和转述
        """
        try:
            data = await erp_connector.get_order_detail(order_id)
            if not data:
                return None
            
            # 简化数据格式，便于AI理解
            return {
                "order_id": data.get("order_no", order_id),
                "status": data.get("status", "未知"),
                "status_text": self._translate_order_status(data.get("status")),
                "customer_name": data.get("customer_name", ""),
                "route": f"{data.get('from_location', '')} → {data.get('to_location', '')}",
                "transport_type": data.get("transport_type", ""),
                "created_at": data.get("created_at", ""),
                "estimated_arrival": data.get("eta", ""),
                "cargo_info": data.get("cargo_description", "")
            }
        except ERPConnectionError as e:
            logger.warning(f"查询订单状态失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取订单状态出错: {e}")
            return None
    
    async def search_orders_by_customer(
        self, 
        customer_name: str = None,
        customer_phone: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根据客户信息搜索订单（供AI Agent查询客户的订单）
        
        返回:
            订单列表摘要
        """
        try:
            # 注意：这里假设ERP API支持按客户搜索
            # 实际实现可能需要调整
            data = await erp_connector.get_orders(page_size=limit)
            
            if not data or "items" not in data:
                return []
            
            orders = []
            for item in data.get("items", [])[:limit]:
                orders.append({
                    "order_id": item.get("order_no", ""),
                    "status": self._translate_order_status(item.get("status")),
                    "route": f"{item.get('from_location', '')} → {item.get('to_location', '')}",
                    "created_at": item.get("created_at", ""),
                    "amount": item.get("total_amount", "")
                })
            
            return orders
        except Exception as e:
            logger.error(f"搜索客户订单失败: {e}")
            return []
    
    async def get_pricing_info(
        self,
        from_location: str = None,
        to_location: str = None,
        transport_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取报价信息（供AI Agent回答客户的报价询问）
        
        返回:
            参考报价信息
        """
        try:
            data = await erp_connector.get_product_pricing(
                route_from=from_location,
                route_to=to_location,
                transport_type=transport_type
            )
            
            if not data:
                return None
            
            # 简化返回格式
            return {
                "route": f"{from_location or '中国'} → {to_location or '目的地'}",
                "transport_type": transport_type or "海运",
                "prices": data.get("prices", []),
                "valid_until": data.get("valid_until", ""),
                "notes": data.get("notes", "报价仅供参考，具体以实际货物和时间为准"),
                "currency": data.get("currency", "CNY")
            }
        except Exception as e:
            logger.error(f"获取报价信息失败: {e}")
            return None
    
    async def get_shipment_tracking(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取物流跟踪信息（供AI Agent回答客户的物流查询）
        
        返回:
            物流跟踪信息
        """
        try:
            # 先获取订单关联的shipment
            order = await erp_connector.get_order_detail(order_id)
            if not order:
                return None
            
            shipment_id = order.get("shipment_id")
            if not shipment_id:
                return {
                    "order_id": order_id,
                    "status": "待发运",
                    "message": "货物尚未发运，暂无物流信息"
                }
            
            # 获取物流跟踪
            tracking = await erp_connector.get_shipment_tracking(shipment_id)
            if not tracking:
                return None
            
            return {
                "order_id": order_id,
                "shipment_id": shipment_id,
                "status": tracking.get("current_status", ""),
                "location": tracking.get("current_location", ""),
                "eta": tracking.get("estimated_arrival", ""),
                "history": tracking.get("tracking_events", [])[:5],  # 只返回最近5条
                "carrier": tracking.get("carrier_name", "")
            }
        except Exception as e:
            logger.error(f"获取物流跟踪失败: {e}")
            return None
    
    async def get_customer_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        获取客户档案（供AI Agent了解客户背景）
        
        返回:
            客户信息摘要
        """
        try:
            data = await erp_connector.get_customer_detail(customer_id)
            if not data:
                return None
            
            return {
                "customer_id": customer_id,
                "name": data.get("company_name", data.get("name", "")),
                "level": data.get("level", ""),
                "total_orders": data.get("total_orders", 0),
                "total_amount": data.get("total_amount", 0),
                "main_routes": data.get("frequent_routes", []),
                "contact_person": data.get("contact_name", ""),
                "last_order_date": data.get("last_order_at", ""),
                "credit_status": data.get("credit_status", "正常")
            }
        except Exception as e:
            logger.error(f"获取客户档案失败: {e}")
            return None
    
    async def get_finance_overview(self, customer_id: str = None) -> Optional[Dict[str, Any]]:
        """
        获取财务概览（供AI Agent回答财务相关问题）
        
        返回:
            财务概览信息
        """
        try:
            # 如果指定了客户，获取该客户的应收情况
            if customer_id:
                receivables = await erp_connector.get_receivables(page_size=10)
                customer_receivables = []
                for item in receivables.get("items", []):
                    if item.get("customer_id") == customer_id:
                        customer_receivables.append({
                            "invoice_no": item.get("invoice_no", ""),
                            "amount": item.get("amount", 0),
                            "due_date": item.get("due_date", ""),
                            "status": item.get("status", "")
                        })
                
                return {
                    "customer_id": customer_id,
                    "receivables": customer_receivables,
                    "total_receivable": sum(r.get("amount", 0) for r in customer_receivables)
                }
            
            # 获取整体财务概览
            summary = await erp_connector.get_finance_summary()
            return {
                "period": summary.get("period", "本月"),
                "total_revenue": summary.get("total_revenue", 0),
                "total_receivable": summary.get("total_receivable", 0),
                "total_payable": summary.get("total_payable", 0),
                "overdue_amount": summary.get("overdue_amount", 0)
            }
        except Exception as e:
            logger.error(f"获取财务概览失败: {e}")
            return None
    
    def _translate_order_status(self, status: str) -> str:
        """翻译订单状态为中文"""
        status_map = {
            "pending": "待处理",
            "confirmed": "已确认",
            "in_transit": "运输中",
            "arrived": "已到港",
            "customs": "清关中",
            "delivered": "已签收",
            "completed": "已完成",
            "cancelled": "已取消"
        }
        return status_map.get(status, status or "未知")
    
    async def format_for_ai_context(self, query_type: str, data: Any) -> str:
        """
        将ERP数据格式化为AI可以理解的上下文文本
        
        Args:
            query_type: 查询类型 (order/pricing/tracking/customer/finance)
            data: 查询结果数据
        
        Returns:
            格式化的文本，可直接加入AI的上下文
        """
        if not data:
            return f"[ERP数据] 未找到相关的{query_type}信息"
        
        if query_type == "order":
            return f"""[ERP订单信息]
订单号: {data.get('order_id', '未知')}
状态: {data.get('status_text', '未知')}
路线: {data.get('route', '未知')}
预计到达: {data.get('estimated_arrival', '未知')}
货物: {data.get('cargo_info', '未知')}"""
        
        elif query_type == "pricing":
            prices_text = "\n".join([
                f"  - {p.get('service', '')}: {p.get('price', '')} {data.get('currency', 'CNY')}"
                for p in data.get('prices', [])[:5]
            ])
            return f"""[ERP报价信息]
路线: {data.get('route', '未知')}
运输方式: {data.get('transport_type', '未知')}
参考报价:
{prices_text if prices_text else '  暂无报价'}
有效期至: {data.get('valid_until', '未知')}
备注: {data.get('notes', '')}"""
        
        elif query_type == "tracking":
            return f"""[ERP物流跟踪]
订单号: {data.get('order_id', '未知')}
当前状态: {data.get('status', '未知')}
当前位置: {data.get('location', '未知')}
预计到达: {data.get('eta', '未知')}
承运商: {data.get('carrier', '未知')}"""
        
        elif query_type == "customer":
            return f"""[ERP客户档案]
客户名称: {data.get('name', '未知')}
客户级别: {data.get('level', '未知')}
历史订单: {data.get('total_orders', 0)}单
累计金额: {data.get('total_amount', 0)}
常用航线: {', '.join(data.get('main_routes', [])) or '未知'}
信用状态: {data.get('credit_status', '未知')}"""
        
        elif query_type == "finance":
            return f"""[ERP财务信息]
应收账款: {data.get('total_receivable', 0)}元
应付账款: {data.get('total_payable', 0)}元
逾期金额: {data.get('overdue_amount', 0)}元"""
        
        return f"[ERP数据] {str(data)[:200]}"


# 创建全局实例
erp_query_helper = ERPQueryHelper()
