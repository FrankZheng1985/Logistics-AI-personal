"""
ERP业务系统只读连接器
负责：安全地从BP Logistics ERP系统获取业务数据

安全策略：
1. 只允许GET请求，硬编码禁止任何写操作
2. 所有数据缓存到本地数据库
3. 请求频率限制，防止过度调用
"""
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import httpx
from functools import wraps

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class ERPConnectionError(Exception):
    """ERP连接错误"""
    pass


class ERPAuthenticationError(Exception):
    """ERP认证错误"""
    pass


class ERPPermissionError(Exception):
    """ERP权限错误 - 尝试执行写操作时抛出"""
    pass


class ReadOnlyERPConnector:
    """
    只读ERP连接器
    
    安全特性：
    - 硬编码只允许GET请求
    - 所有方法都是查询操作
    - 自动缓存减少API调用
    """
    
    # 只允许GET方法 - 这是安全的核心
    ALLOWED_METHODS = frozenset(['GET'])
    
    # 默认缓存时间（秒）
    DEFAULT_CACHE_TTL = 300  # 5分钟
    
    # API请求频率限制
    RATE_LIMIT_REQUESTS = 60  # 每分钟最大请求数
    RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）
    
    def __init__(self):
        self._config: Optional[Dict] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_tokens: List[datetime] = []
        self._initialized = False
    
    async def initialize(self) -> bool:
        """初始化连接器，加载配置"""
        try:
            self._config = await self._load_config()
            if not self._config or not self._config.get('api_url'):
                logger.warning("ERP连接配置未设置")
                return False
            
            # 创建HTTP客户端
            self._client = httpx.AsyncClient(
                base_url=self._config['api_url'],
                timeout=30.0,
                headers=self._build_auth_headers()
            )
            
            self._initialized = True
            logger.info(f"ERP连接器初始化成功: {self._config['api_url']}")
            return True
        except Exception as e:
            logger.error(f"ERP连接器初始化失败: {e}")
            return False
    
    async def _load_config(self) -> Optional[Dict]:
        """从数据库加载ERP配置"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT api_url, auth_type, auth_token, username FROM erp_config WHERE is_active = TRUE LIMIT 1")
                )
                row = result.fetchone()
                if row:
                    return {
                        'api_url': row[0],
                        'auth_type': row[1],
                        'auth_token': row[2],
                        'username': row[3]
                    }
                return None
        except Exception as e:
            logger.error(f"加载ERP配置失败: {e}")
            return None
    
    def _build_auth_headers(self) -> Dict[str, str]:
        """构建认证头"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'LogisticsAI-ReadOnly/1.0'
        }
        
        if not self._config:
            return headers
        
        auth_type = self._config.get('auth_type', 'bearer')
        auth_token = self._config.get('auth_token', '')
        
        # BP Logistics ERP 支持多种认证方式
        if auth_type == 'bearer':
            headers['Authorization'] = f'Bearer {auth_token}'
        elif auth_type == 'x_api_key':
            # 标准 X-API-Key 头
            headers['X-API-Key'] = auth_token
        elif auth_type == 'api_key':
            # Api-Key 头（部分API使用这种格式）
            headers['Api-Key'] = auth_token
        elif auth_type == 'apikey':
            # apikey 头（小写格式）
            headers['apikey'] = auth_token
        elif auth_type == 'token':
            headers['Authorization'] = f'Token {auth_token}'
        
        return headers
    
    async def _check_rate_limit(self) -> bool:
        """检查请求频率限制"""
        now = datetime.now()
        # 清理过期的令牌
        self._rate_limit_tokens = [
            t for t in self._rate_limit_tokens 
            if (now - t).seconds < self.RATE_LIMIT_WINDOW
        ]
        
        if len(self._rate_limit_tokens) >= self.RATE_LIMIT_REQUESTS:
            logger.warning("ERP API请求频率超限")
            return False
        
        self._rate_limit_tokens.append(now)
        return True
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: int = None
    ) -> Dict[str, Any]:
        """
        执行API请求
        
        安全检查：只允许GET请求
        """
        # 【核心安全检查】禁止非GET请求
        method_upper = method.upper()
        if method_upper not in self.ALLOWED_METHODS:
            error_msg = f"安全限制：禁止执行 {method_upper} 操作，只允许读取数据 (GET)"
            logger.error(error_msg)
            raise ERPPermissionError(error_msg)
        
        # 检查初始化
        if not self._initialized or not self._client:
            if not await self.initialize():
                raise ERPConnectionError("ERP连接器未初始化或配置无效")
        
        # 检查频率限制
        if not await self._check_rate_limit():
            raise ERPConnectionError("请求频率超限，请稍后重试")
        
        # 尝试从缓存获取
        cache_key = self._generate_cache_key(endpoint, params)
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"ERP缓存命中: {endpoint}")
                return cached_data
        
        # 执行请求
        try:
            response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 缓存结果
            ttl = cache_ttl or self.DEFAULT_CACHE_TTL
            await self._save_to_cache(cache_key, data, ttl)
            
            # 记录日志
            await self._log_request(endpoint, params, True)
            
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ERPAuthenticationError("ERP认证失败，请检查API凭证")
            elif e.response.status_code == 403:
                raise ERPPermissionError("ERP权限不足")
            else:
                await self._log_request(endpoint, params, False, str(e))
                raise ERPConnectionError(f"ERP请求失败: {e}")
        except Exception as e:
            await self._log_request(endpoint, params, False, str(e))
            raise ERPConnectionError(f"ERP连接错误: {e}")
    
    def _generate_cache_key(self, endpoint: str, params: Optional[Dict]) -> str:
        """生成缓存键"""
        key_data = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT data FROM erp_data_cache 
                        WHERE cache_key = :key AND expires_at > NOW()
                    """),
                    {"key": cache_key}
                )
                row = result.fetchone()
                if row and row[0]:
                    return json.loads(row[0]) if isinstance(row[0], str) else row[0]
                return None
        except Exception as e:
            logger.warning(f"读取ERP缓存失败: {e}")
            return None
    
    async def _save_to_cache(self, cache_key: str, data: Dict, ttl: int):
        """保存数据到缓存"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO erp_data_cache (cache_key, data, expires_at, created_at)
                        VALUES (:key, :data, NOW() + INTERVAL ':ttl seconds', NOW())
                        ON CONFLICT (cache_key) DO UPDATE 
                        SET data = :data, expires_at = NOW() + INTERVAL ':ttl seconds'
                    """.replace(':ttl', str(ttl))),
                    {"key": cache_key, "data": json.dumps(data)}
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"保存ERP缓存失败: {e}")
    
    async def _log_request(
        self, 
        endpoint: str, 
        params: Optional[Dict], 
        success: bool, 
        error: str = None
    ):
        """记录API请求日志"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO erp_sync_logs 
                        (endpoint, params, success, error_message, created_at)
                        VALUES (:endpoint, :params, :success, :error, NOW())
                    """),
                    {
                        "endpoint": endpoint,
                        "params": json.dumps(params or {}),
                        "success": success,
                        "error": error
                    }
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"记录ERP日志失败: {e}")
    
    # ========== 业务数据查询方法（只读） ==========
    # 注意：API端点路径基于BP Logistics ERP的internal-api接口
    
    async def get_orders(
        self, 
        page: int = 1, 
        page_size: int = 100,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        order_type: Optional[str] = None,
        updated_after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取订单列表
        
        参数:
            page: 页码
            page_size: 每页数量（最大100）
            status: 订单状态筛选
            customer_id: 客户ID筛选
            start_date: 开始日期（ISO 8601）
            end_date: 结束日期（ISO 8601）
            order_type: history=已完成, active=进行中, all=全部
            updated_after: 增量同步，只获取此时间后更新的数据
        
        返回:
            订单列表数据
        """
        params = {
            'page': page,
            'pageSize': page_size  # API使用驼峰命名
        }
        if status:
            params['status'] = status
        if customer_id:
            params['customerId'] = customer_id
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if order_type:
            params['type'] = order_type
        if updated_after:
            params['updatedAfter'] = updated_after
        
        return await self._request('GET', '/internal-api/orders', params=params)
    
    async def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """获取订单详情"""
        return await self._request('GET', f'/internal-api/orders/{order_id}')
    
    async def get_orders_stats(self) -> Dict[str, Any]:
        """获取订单统计"""
        return await self._request('GET', '/internal-api/orders/stats', cache_ttl=600)
    
    async def get_invoices(
        self,
        page: int = 1,
        page_size: int = 100,
        status: Optional[str] = None,
        invoice_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        updated_after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取发票列表
        
        参数:
            page: 页码
            page_size: 每页数量（最大100）
            status: 发票状态 (draft/unpaid/partial/paid/overdue/cancelled)
            invoice_type: receivable=应收, payable=应付
            start_date: 创建开始日期
            end_date: 创建结束日期
            updated_after: 增量同步时间
        
        返回:
            发票列表数据
        """
        params = {'page': page, 'pageSize': page_size}
        if status:
            params['status'] = status
        if invoice_type:
            params['type'] = invoice_type
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if updated_after:
            params['updatedAfter'] = updated_after
        
        return await self._request('GET', '/internal-api/invoices', params=params)
    
    async def get_invoice_detail(self, invoice_id: str) -> Dict[str, Any]:
        """获取发票详情"""
        return await self._request('GET', f'/internal-api/invoices/{invoice_id}')
    
    async def get_payments(
        self,
        page: int = 1,
        page_size: int = 100,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        updated_after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取付款记录
        
        参数:
            page: 页码
            page_size: 每页数量（最大100）
            status: 付款状态
            start_date: 付款开始日期
            end_date: 付款结束日期
            updated_after: 增量同步时间
        
        返回:
            付款记录数据
        """
        params = {'page': page, 'pageSize': page_size}
        if status:
            params['status'] = status
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if updated_after:
            params['updatedAfter'] = updated_after
        
        return await self._request('GET', '/internal-api/payments', params=params)
    
    async def get_payment_detail(self, payment_id: str) -> Dict[str, Any]:
        """获取付款详情"""
        return await self._request('GET', f'/internal-api/payments/{payment_id}')
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取综合统计"""
        return await self._request('GET', '/internal-api/stats', cache_ttl=600)
    
    async def get_finance_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取财务汇总
        
        参数:
            start_date: 统计开始日期
            end_date: 统计结束日期
        
        返回:
            财务汇总数据（应收/应付/收款/付款等）
        """
        params = {}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        
        return await self._request('GET', '/internal-api/financial-summary', params=params, cache_ttl=600)
    
    async def get_monthly_stats(
        self,
        months: int = 12
    ) -> Dict[str, Any]:
        """
        获取月度统计
        
        参数:
            months: 统计月数，默认12个月
        
        返回:
            月度统计数据（订单量、收入、成本、利润等）
        """
        params = {'months': months}
        
        return await self._request('GET', '/internal-api/monthly-stats', params=params, cache_ttl=600)
    
    # ========== 以下为扩展接口（如果ERP支持的话） ==========
    
    async def get_quotes(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取报价列表（如果ERP有此接口）
        """
        params = {'page': page, 'page_size': page_size}
        if customer_id:
            params['customer_id'] = customer_id
        if status:
            params['status'] = status
        
        # 尝试调用，如果不存在会返回错误
        return await self._request('GET', '/internal-api/quotes', params=params)
    
    async def get_customers(
        self,
        page: int = 1,
        page_size: int = 100,
        keyword: Optional[str] = None,
        customer_level: Optional[str] = None,
        customer_type: Optional[str] = None,
        customer_region: Optional[str] = None,
        status: Optional[str] = None,
        updated_after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取客户列表
        
        参数:
            page: 页码
            page_size: 每页数量（最大100）
            keyword: 关键词搜索（客户名/编码/公司名）
            customer_level: 客户等级 (normal/silver/gold/vip)
            customer_type: 客户类型 (shipper/consignee/both/agent)
            customer_region: 客户区域 (china/overseas)
            status: 客户状态 (active/inactive)
            updated_after: 增量同步时间
        
        返回:
            客户列表数据
        """
        params = {'page': page, 'pageSize': page_size}
        if keyword:
            params['keyword'] = keyword
        if customer_level:
            params['customerLevel'] = customer_level
        if customer_type:
            params['customerType'] = customer_type
        if customer_region:
            params['customerRegion'] = customer_region
        if status:
            params['status'] = status
        if updated_after:
            params['updatedAfter'] = updated_after
        
        return await self._request('GET', '/internal-api/customers', params=params)
    
    async def get_customer_detail(self, customer_id: str, include_contacts: bool = False) -> Dict[str, Any]:
        """
        获取客户详情
        
        参数:
            customer_id: 客户ID
            include_contacts: 是否包含联系人列表
        
        返回:
            客户详情数据
        """
        params = {}
        if include_contacts:
            params['includeContacts'] = 'true'
        return await self._request('GET', f'/internal-api/customers/{customer_id}', params=params)
    
    async def get_shipments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取运输/物流状态（如果ERP有此接口）
        """
        params = {'page': page, 'page_size': page_size}
        if status:
            params['status'] = status
        if order_id:
            params['order_id'] = order_id
        
        return await self._request('GET', '/internal-api/shipments', params=params)
    
    async def get_shipment_tracking(self, shipment_id: str) -> Dict[str, Any]:
        """获取物流跟踪详情（如果ERP有此接口）"""
        return await self._request('GET', f'/internal-api/shipments/{shipment_id}/tracking')
    
    async def get_product_pricing(
        self,
        route_from: Optional[str] = None,
        route_to: Optional[str] = None,
        transport_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取产品定价（如果ERP有此接口）
        """
        params = {}
        if route_from:
            params['from'] = route_from
        if route_to:
            params['to'] = route_to
        if transport_type:
            params['type'] = transport_type
        
        return await self._request('GET', '/internal-api/pricing', params=params)
    
    async def get_receivables(
        self,
        page: int = 1,
        page_size: int = 20,
        overdue_only: bool = False
    ) -> Dict[str, Any]:
        """
        获取应收账款（如果ERP有此接口）
        """
        params = {'page': page, 'page_size': page_size}
        if overdue_only:
            params['overdue'] = 'true'
        
        return await self._request('GET', '/internal-api/receivables', params=params)
    
    async def get_suppliers(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取供应商列表（如果ERP有此接口）
        """
        params = {'page': page, 'page_size': page_size}
        if category:
            params['category'] = category
        
        return await self._request('GET', '/internal-api/suppliers', params=params)
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试ERP连接"""
        try:
            # 强制重新初始化以加载最新配置
            self._initialized = False
            if self._client:
                await self._client.aclose()
                self._client = None
            
            await self.initialize()
            
            if not self._client:
                return {
                    "success": False,
                    "error": "连接器未初始化，请先配置ERP连接信息"
                }
            
            # 使用健康检查接口测试连接
            response = await self._client.get('/internal-api/health')
            response.raise_for_status()
            
            return {
                "success": True,
                "message": "ERP连接成功",
                "api_url": self._config.get('api_url')
            }
        except ERPAuthenticationError as e:
            return {"success": False, "error": f"认证失败: {str(e)}"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"连接失败: Client error '{e.response.status_code} {e.response.reason_phrase}' for url '{e.request.url}' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/{e.response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"连接失败: {str(e)}"}
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False


class ERPConfigManager:
    """ERP配置管理器"""
    
    @staticmethod
    async def save_config(
        api_url: str,
        auth_type: str,
        auth_token: str,
        username: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """保存ERP配置"""
        try:
            async with AsyncSessionLocal() as db:
                # 如果是保持现有密钥，先获取现有密钥
                actual_token = auth_token
                if auth_token == '__KEEP_EXISTING__':
                    result = await db.execute(
                        text("SELECT auth_token FROM erp_config WHERE is_active = TRUE LIMIT 1")
                    )
                    row = result.fetchone()
                    if row:
                        actual_token = row[0]
                    else:
                        logger.error("尝试保持现有密钥，但没有找到现有配置")
                        return False
                
                # 先将所有配置设为非活动
                await db.execute(
                    text("UPDATE erp_config SET is_active = FALSE")
                )
                
                # 插入新配置
                await db.execute(
                    text("""
                        INSERT INTO erp_config 
                        (api_url, auth_type, auth_token, username, description, is_active, created_at, updated_at)
                        VALUES (:api_url, :auth_type, :auth_token, :username, :description, TRUE, NOW(), NOW())
                    """),
                    {
                        "api_url": api_url,
                        "auth_type": auth_type,
                        "auth_token": actual_token,
                        "username": username,
                        "description": description or "BP Logistics ERP"
                    }
                )
                await db.commit()
                
                logger.info(f"ERP配置已保存: {api_url}")
                return True
        except Exception as e:
            logger.error(f"保存ERP配置失败: {e}")
            return False
    
    @staticmethod
    async def get_config() -> Optional[Dict]:
        """获取当前ERP配置"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT id, api_url, auth_type, username, description, 
                               is_active, created_at, updated_at, auth_token
                        FROM erp_config WHERE is_active = TRUE LIMIT 1
                    """)
                )
                row = result.fetchone()
                if row:
                    # 返回 has_token 标记表示是否已配置密钥，但不返回实际密钥
                    return {
                        "id": str(row[0]),
                        "api_url": row[1],
                        "auth_type": row[2],
                        "username": row[3],
                        "description": row[4],
                        "is_active": row[5],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "has_token": bool(row[8])  # 标记是否已有密钥
                    }
                return None
        except Exception as e:
            logger.error(f"获取ERP配置失败: {e}")
            return None
    
    @staticmethod
    async def get_sync_logs(limit: int = 50) -> List[Dict]:
        """获取同步日志"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT id, endpoint, params, success, error_message, created_at
                        FROM erp_sync_logs
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
                rows = result.fetchall()
                return [
                    {
                        "id": str(row[0]),
                        "endpoint": row[1],
                        "params": row[2],
                        "success": row[3],
                        "error": row[4],
                        "created_at": row[5].isoformat() if row[5] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取同步日志失败: {e}")
            return []
    
    @staticmethod
    async def clear_cache():
        """清除所有缓存"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("DELETE FROM erp_data_cache"))
                await db.commit()
                logger.info("ERP缓存已清除")
                return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False


# 创建全局连接器实例
erp_connector = ReadOnlyERPConnector()
erp_config_manager = ERPConfigManager()
