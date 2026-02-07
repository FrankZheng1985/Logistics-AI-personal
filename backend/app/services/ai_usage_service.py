"""
AI用量监控服务
记录大模型API调用用量、费用估算、告警通知
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import asyncio
from loguru import logger
from sqlalchemy import text

from app.models.database import AsyncSessionLocal


class AIUsageService:
    """AI用量监控服务"""
    
    # 默认价格配置（元/1000 tokens）- 当数据库中没有配置时使用
    DEFAULT_PRICING = {
        # 通义千问
        ('dashscope', 'qwen-turbo'): {'input': 0.002, 'output': 0.006},
        ('dashscope', 'qwen-plus'): {'input': 0.004, 'output': 0.012},
        ('dashscope', 'qwen-max'): {'input': 0.02, 'output': 0.06},
        ('dashscope', 'qwen-long'): {'input': 0.0005, 'output': 0.002},
        # OpenAI (人民币)
        ('openai', 'gpt-4-turbo-preview'): {'input': 0.072, 'output': 0.216},
        ('openai', 'gpt-4'): {'input': 0.216, 'output': 0.432},
        ('openai', 'gpt-3.5-turbo'): {'input': 0.0036, 'output': 0.0108},
        # Anthropic Claude (人民币)
        ('anthropic', 'claude-3-opus-20240229'): {'input': 0.108, 'output': 0.54},
        ('anthropic', 'claude-3-sonnet-20240229'): {'input': 0.0216, 'output': 0.108},
        ('anthropic', 'claude-3-haiku-20240307'): {'input': 0.0018, 'output': 0.009},
        # DeepSeek
        ('deepseek', 'deepseek-chat'): {'input': 0.001, 'output': 0.002},
    }
    
    # 价格缓存
    _pricing_cache: Dict[tuple, Dict] = {}
    _cache_loaded: bool = False
    
    @classmethod
    async def _load_pricing_cache(cls):
        """加载价格配置到缓存"""
        if cls._cache_loaded:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT provider, model_name, input_price_per_1k, output_price_per_1k
                        FROM ai_model_pricing
                        WHERE is_active = TRUE
                    """)
                )
                rows = result.fetchall()
                
                for row in rows:
                    cls._pricing_cache[(row[0], row[1])] = {
                        'input': float(row[2]),
                        'output': float(row[3])
                    }
                
                cls._cache_loaded = True
                logger.debug(f"已加载 {len(rows)} 个模型价格配置")
        except Exception as e:
            logger.warning(f"加载价格配置失败，使用默认配置: {e}")
            cls._pricing_cache = cls.DEFAULT_PRICING.copy()
            cls._cache_loaded = True
    
    @classmethod
    def _get_pricing(cls, provider: str, model_name: str) -> Dict[str, float]:
        """获取模型价格配置"""
        # 先从缓存查找
        key = (provider, model_name)
        if key in cls._pricing_cache:
            return cls._pricing_cache[key]
        
        # 再从默认配置查找
        if key in cls.DEFAULT_PRICING:
            return cls.DEFAULT_PRICING[key]
        
        # 模糊匹配（处理模型版本号问题）
        for (p, m), pricing in {**cls._pricing_cache, **cls.DEFAULT_PRICING}.items():
            if p == provider and (m in model_name or model_name in m):
                return pricing
        
        # 默认返回通义千问Plus的价格
        logger.warning(f"未找到模型 {provider}/{model_name} 的价格配置，使用默认价格")
        return {'input': 0.004, 'output': 0.012}
    
    @classmethod
    def calculate_cost(
        cls,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        计算API调用费用
        
        Args:
            provider: 提供商
            model_name: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
        
        Returns:
            估算费用（元）
        """
        pricing = cls._get_pricing(provider, model_name)
        
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        
        return round(input_cost + output_cost, 6)
    
    @classmethod
    async def record_usage(
        cls,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        agent_name: Optional[str] = None,
        agent_id: Optional[int] = None,
        task_type: Optional[str] = None,
        request_id: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        is_success: bool = True,
        error_message: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> Optional[int]:
        """
        记录AI用量
        
        Args:
            provider: 提供商 (dashscope, openai, anthropic)
            model_name: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            agent_name: AI员工名称
            agent_id: AI员工ID
            task_type: 任务类型
            request_id: 请求ID
            response_time_ms: 响应时间（毫秒）
            is_success: 是否成功
            error_message: 错误信息
            extra_data: 额外数据
        
        Returns:
            日志ID
        """
        try:
            # 确保价格缓存已加载
            await cls._load_pricing_cache()
            
            total_tokens = input_tokens + output_tokens
            cost_estimate = cls.calculate_cost(provider, model_name, input_tokens, output_tokens)
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO ai_usage_logs (
                            agent_name, agent_id, model_name, provider,
                            input_tokens, output_tokens, total_tokens,
                            cost_estimate, task_type, request_id,
                            response_time_ms, is_success, error_message, extra_data
                        ) VALUES (
                            :agent_name, :agent_id, :model_name, :provider,
                            :input_tokens, :output_tokens, :total_tokens,
                            :cost_estimate, :task_type, :request_id,
                            :response_time_ms, :is_success, :error_message, :extra_data
                        )
                        RETURNING id
                    """),
                    {
                        "agent_name": agent_name,
                        "agent_id": agent_id,
                        "model_name": model_name,
                        "provider": provider,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "cost_estimate": cost_estimate,
                        "task_type": task_type,
                        "request_id": request_id,
                        "response_time_ms": response_time_ms,
                        "is_success": is_success,
                        "error_message": error_message,
                        "extra_data": json.dumps(extra_data or {})
                    }
                )
                await db.commit()
                
                row = result.fetchone()
                log_id = row[0] if row else None
                
                logger.debug(
                    f"记录AI用量: {provider}/{model_name}, "
                    f"tokens: {input_tokens}+{output_tokens}={total_tokens}, "
                    f"费用: ¥{cost_estimate:.4f}"
                )
                
                # 异步检查告警（不阻塞主流程）
                asyncio.create_task(cls._check_alerts())
                
                return log_id
                
        except Exception as e:
            logger.error(f"记录AI用量失败: {e}")
            return None
    
    @classmethod
    async def get_usage_stats(
        cls,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        agent_name: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用量统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            agent_name: AI员工名称过滤
            provider: 提供商过滤
        
        Returns:
            统计数据
        """
        try:
            # 默认统计最近30天
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # 转换为datetime以避免SQL类型转换问题
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
            
            async with AsyncSessionLocal() as db:
                # 构建查询条件
                conditions = ["created_at >= :start_datetime", "created_at < :end_datetime"]
                params = {"start_datetime": start_datetime, "end_datetime": end_datetime}
                
                if agent_name:
                    conditions.append("agent_name = :agent_name")
                    params["agent_name"] = agent_name
                
                if provider:
                    conditions.append("provider = :provider")
                    params["provider"] = provider
                
                where_clause = " AND ".join(conditions)
                
                # 总体统计
                result = await db.execute(
                    text(f"""
                        SELECT 
                            COUNT(*) as total_requests,
                            SUM(CASE WHEN is_success THEN 1 ELSE 0 END) as success_count,
                            SUM(input_tokens) as total_input_tokens,
                            SUM(output_tokens) as total_output_tokens,
                            SUM(total_tokens) as total_tokens,
                            SUM(cost_estimate) as total_cost,
                            AVG(response_time_ms) as avg_response_time,
                            MAX(response_time_ms) as max_response_time
                        FROM ai_usage_logs
                        WHERE {where_clause}
                    """),
                    params
                )
                row = result.fetchone()
                
                # 按提供商统计
                provider_result = await db.execute(
                    text(f"""
                        SELECT 
                            provider,
                            COUNT(*) as requests,
                            SUM(total_tokens) as tokens,
                            SUM(cost_estimate) as cost
                        FROM ai_usage_logs
                        WHERE {where_clause}
                        GROUP BY provider
                        ORDER BY cost DESC
                    """),
                    params
                )
                provider_stats = [
                    {"provider": r[0], "requests": r[1], "tokens": int(r[2] or 0), "cost": float(r[3] or 0)}
                    for r in provider_result.fetchall()
                ]
                
                # 按模型统计
                model_result = await db.execute(
                    text(f"""
                        SELECT 
                            provider,
                            model_name,
                            COUNT(*) as requests,
                            SUM(total_tokens) as tokens,
                            SUM(cost_estimate) as cost
                        FROM ai_usage_logs
                        WHERE {where_clause}
                        GROUP BY provider, model_name
                        ORDER BY cost DESC
                        LIMIT 10
                    """),
                    params
                )
                model_stats = [
                    {"provider": r[0], "model": r[1], "requests": r[2], "tokens": int(r[3] or 0), "cost": float(r[4] or 0)}
                    for r in model_result.fetchall()
                ]
                
                # 按AI员工统计
                agent_result = await db.execute(
                    text(f"""
                        SELECT 
                            COALESCE(agent_name, '未知') as agent_name,
                            COUNT(*) as requests,
                            SUM(total_tokens) as tokens,
                            SUM(cost_estimate) as cost
                        FROM ai_usage_logs
                        WHERE {where_clause}
                        GROUP BY agent_name
                        ORDER BY cost DESC
                    """),
                    params
                )
                agent_stats = [
                    {"agent": r[0], "requests": r[1], "tokens": int(r[2] or 0), "cost": float(r[3] or 0)}
                    for r in agent_result.fetchall()
                ]
                
                # 按天统计趋势
                daily_result = await db.execute(
                    text(f"""
                        SELECT 
                            DATE(created_at) as stat_date,
                            COUNT(*) as requests,
                            SUM(total_tokens) as tokens,
                            SUM(cost_estimate) as cost
                        FROM ai_usage_logs
                        WHERE {where_clause}
                        GROUP BY DATE(created_at)
                        ORDER BY stat_date
                    """),
                    params
                )
                daily_stats = [
                    {
                        "date": r[0].isoformat() if r[0] else None,
                        "requests": r[1],
                        "tokens": int(r[2] or 0),
                        "cost": float(r[3] or 0)
                    }
                    for r in daily_result.fetchall()
                ]
                
                return {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "summary": {
                        "total_requests": row[0] or 0,
                        "success_count": row[1] or 0,
                        "error_count": (row[0] or 0) - (row[1] or 0),
                        "success_rate": round((row[1] or 0) / (row[0] or 1) * 100, 2),
                        "total_input_tokens": int(row[2] or 0),
                        "total_output_tokens": int(row[3] or 0),
                        "total_tokens": int(row[4] or 0),
                        "total_cost": float(row[5] or 0),
                        "avg_response_time_ms": int(row[6] or 0),
                        "max_response_time_ms": int(row[7] or 0)
                    },
                    "by_provider": provider_stats,
                    "by_model": model_stats,
                    "by_agent": agent_stats,
                    "daily_trend": daily_stats
                }
                
        except Exception as e:
            logger.error(f"获取用量统计失败: {e}")
            return {
                "error": str(e),
                "summary": {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0
                }
            }
    
    @classmethod
    async def get_today_stats(cls) -> Dict[str, Any]:
        """获取今日统计"""
        today = date.today()
        return await cls.get_usage_stats(start_date=today, end_date=today)
    
    @classmethod
    async def get_usage_logs(
        cls,
        page: int = 1,
        page_size: int = 50,
        agent_name: Optional[str] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        获取用量日志列表
        
        Args:
            page: 页码
            page_size: 每页数量
            agent_name: AI员工名称过滤
            provider: 提供商过滤
            model_name: 模型名称过滤
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            日志列表
        """
        try:
            async with AsyncSessionLocal() as db:
                # 构建查询条件
                conditions = ["1=1"]
                params = {"offset": (page - 1) * page_size, "limit": page_size}
                
                if agent_name:
                    conditions.append("agent_name = :agent_name")
                    params["agent_name"] = agent_name
                
                if provider:
                    conditions.append("provider = :provider")
                    params["provider"] = provider
                
                if model_name:
                    conditions.append("model_name ILIKE :model_name")
                    params["model_name"] = f"%{model_name}%"
                
                if start_date:
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    conditions.append("created_at >= :start_datetime")
                    params["start_datetime"] = start_datetime
                
                if end_date:
                    end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
                    conditions.append("created_at < :end_datetime")
                    params["end_datetime"] = end_datetime
                
                where_clause = " AND ".join(conditions)
                
                # 查询总数
                count_result = await db.execute(
                    text(f"SELECT COUNT(*) FROM ai_usage_logs WHERE {where_clause}"),
                    params
                )
                total = count_result.scalar() or 0
                
                # 查询数据
                result = await db.execute(
                    text(f"""
                        SELECT 
                            id, agent_name, model_name, provider,
                            input_tokens, output_tokens, total_tokens,
                            cost_estimate, task_type, response_time_ms,
                            is_success, error_message, created_at
                        FROM ai_usage_logs
                        WHERE {where_clause}
                        ORDER BY created_at DESC
                        OFFSET :offset LIMIT :limit
                    """),
                    params
                )
                
                logs = [
                    {
                        "id": r[0],
                        "agent_name": r[1],
                        "model_name": r[2],
                        "provider": r[3],
                        "input_tokens": r[4],
                        "output_tokens": r[5],
                        "total_tokens": r[6],
                        "cost_estimate": float(r[7]),
                        "task_type": r[8],
                        "response_time_ms": r[9],
                        "is_success": r[10],
                        "error_message": r[11],
                        "created_at": r[12].isoformat() if r[12] else None
                    }
                    for r in result.fetchall()
                ]
                
                return {
                    "logs": logs,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
                
        except Exception as e:
            logger.error(f"获取用量日志失败: {e}")
            return {"logs": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 0}
    
    # ==================== 告警功能 ====================
    
    @classmethod
    async def get_alerts(cls) -> List[Dict[str, Any]]:
        """获取告警配置列表"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT 
                            id, alert_name, alert_type, threshold_amount, threshold_tokens,
                            notify_wechat, notify_email, notify_users,
                            is_active, last_triggered_at, trigger_count,
                            created_at, updated_at
                        FROM ai_usage_alerts
                        ORDER BY id
                    """)
                )
                
                return [
                    {
                        "id": r[0],
                        "alert_name": r[1],
                        "alert_type": r[2],
                        "threshold_amount": float(r[3]),
                        "threshold_tokens": r[4],
                        "notify_wechat": r[5],
                        "notify_email": r[6],
                        "notify_users": r[7],
                        "is_active": r[8],
                        "last_triggered_at": r[9].isoformat() if r[9] else None,
                        "trigger_count": r[10],
                        "created_at": r[11].isoformat() if r[11] else None,
                        "updated_at": r[12].isoformat() if r[12] else None
                    }
                    for r in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"获取告警配置失败: {e}")
            return []
    
    @classmethod
    async def create_alert(
        cls,
        alert_name: str,
        alert_type: str,
        threshold_amount: float,
        threshold_tokens: Optional[int] = None,
        notify_wechat: bool = True,
        notify_email: bool = False,
        notify_users: Optional[str] = None
    ) -> Optional[int]:
        """创建告警配置"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO ai_usage_alerts (
                            alert_name, alert_type, threshold_amount, threshold_tokens,
                            notify_wechat, notify_email, notify_users, is_active
                        ) VALUES (
                            :alert_name, :alert_type, :threshold_amount, :threshold_tokens,
                            :notify_wechat, :notify_email, :notify_users, TRUE
                        )
                        RETURNING id
                    """),
                    {
                        "alert_name": alert_name,
                        "alert_type": alert_type,
                        "threshold_amount": threshold_amount,
                        "threshold_tokens": threshold_tokens,
                        "notify_wechat": notify_wechat,
                        "notify_email": notify_email,
                        "notify_users": notify_users
                    }
                )
                await db.commit()
                
                row = result.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"创建告警配置失败: {e}")
            return None
    
    @classmethod
    async def update_alert(
        cls,
        alert_id: int,
        **kwargs
    ) -> bool:
        """更新告警配置"""
        try:
            # 构建更新字段
            update_fields = []
            params = {"id": alert_id}
            
            for key in ['alert_name', 'alert_type', 'threshold_amount', 'threshold_tokens',
                       'notify_wechat', 'notify_email', 'notify_users', 'is_active']:
                if key in kwargs:
                    update_fields.append(f"{key} = :{key}")
                    params[key] = kwargs[key]
            
            if not update_fields:
                return False
            
            update_fields.append("updated_at = NOW()")
            
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"""
                        UPDATE ai_usage_alerts
                        SET {', '.join(update_fields)}
                        WHERE id = :id
                    """),
                    params
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"更新告警配置失败: {e}")
            return False
    
    @classmethod
    async def delete_alert(cls, alert_id: int) -> bool:
        """删除告警配置"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("DELETE FROM ai_usage_alerts WHERE id = :id"),
                    {"id": alert_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"删除告警配置失败: {e}")
            return False
    
    @classmethod
    async def _check_alerts(cls):
        """检查并触发告警"""
        try:
            async with AsyncSessionLocal() as db:
                # 获取启用的告警
                result = await db.execute(
                    text("""
                        SELECT id, alert_name, alert_type, threshold_amount, 
                               notify_wechat, notify_email, notify_users, last_triggered_at
                        FROM ai_usage_alerts
                        WHERE is_active = TRUE
                    """)
                )
                alerts = result.fetchall()
                
                today = date.today()
                
                for alert in alerts:
                    alert_id, alert_name, alert_type, threshold, notify_wechat, notify_email, notify_users, last_triggered = alert
                    
                    # 确定统计时间范围
                    if alert_type == 'daily':
                        start_date = today
                        # 每天只触发一次
                        if last_triggered and last_triggered.date() == today:
                            continue
                    elif alert_type == 'weekly':
                        start_date = today - timedelta(days=today.weekday())
                        # 每周只触发一次
                        if last_triggered and last_triggered.date() >= start_date:
                            continue
                    elif alert_type == 'monthly':
                        start_date = today.replace(day=1)
                        # 每月只触发一次
                        if last_triggered and last_triggered.date() >= start_date:
                            continue
                    else:
                        continue
                    
                    # 计算当前费用
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    cost_result = await db.execute(
                        text("""
                            SELECT SUM(cost_estimate)
                            FROM ai_usage_logs
                            WHERE created_at >= :start_datetime
                        """),
                        {"start_datetime": start_datetime}
                    )
                    current_cost = cost_result.scalar() or 0
                    
                    # 检查是否超过阈值
                    if current_cost >= float(threshold):
                        await cls._trigger_alert(
                            db, alert_id, alert_name, alert_type,
                            float(threshold), float(current_cost),
                            notify_wechat, notify_email, notify_users
                        )
                        
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
    
    @classmethod
    async def _trigger_alert(
        cls,
        db,
        alert_id: int,
        alert_name: str,
        alert_type: str,
        threshold: float,
        current_cost: float,
        notify_wechat: bool,
        notify_email: bool,
        notify_users: Optional[str]
    ):
        """触发告警"""
        try:
            # 更新告警触发记录
            await db.execute(
                text("""
                    UPDATE ai_usage_alerts
                    SET last_triggered_at = NOW(),
                        trigger_count = trigger_count + 1,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": alert_id}
            )
            await db.commit()
            
            # 构建告警消息
            type_names = {
                'daily': '今日',
                'weekly': '本周',
                'monthly': '本月'
            }
            period_name = type_names.get(alert_type, alert_type)
            
            message = f"""⚠️ **AI用量费用告警**

📋 告警名称: {alert_name}
📊 统计周期: {period_name}
💰 当前费用: ¥{current_cost:.2f}
🚨 告警阈值: ¥{threshold:.2f}
📈 超出比例: {((current_cost - threshold) / threshold * 100):.1f}%

请及时关注AI用量情况，避免费用超支。"""
            
            logger.warning(f"触发告警 [{alert_name}]: 当前费用 ¥{current_cost:.2f} 超过阈值 ¥{threshold:.2f}")
            
            # 发送企业微信通知
            if notify_wechat:
                try:
                    from app.services.notification import notify_high_intent_lead
                    # 复用现有的通知服务
                    await notify_high_intent_lead(
                        customer_name="AI用量告警",
                        channel="系统",
                        intent_score=100,
                        summary=message
                    )
                except Exception as e:
                    logger.error(f"发送企业微信告警失败: {e}")
            
            # 发送邮件通知
            if notify_email:
                try:
                    from app.services.notification import send_email_notification
                    await send_email_notification(
                        subject=f"⚠️ AI用量费用告警 - {period_name}费用超过阈值",
                        content=message
                    )
                except Exception as e:
                    logger.error(f"发送邮件告警失败: {e}")
                    
        except Exception as e:
            logger.error(f"触发告警失败: {e}")
    
    # ==================== 价格配置管理 ====================
    
    @classmethod
    async def get_model_pricing(cls) -> List[Dict[str, Any]]:
        """获取模型价格配置"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT 
                            id, provider, model_name, display_name,
                            input_price_per_1k, output_price_per_1k,
                            description, is_active, created_at, updated_at
                        FROM ai_model_pricing
                        ORDER BY provider, model_name
                    """)
                )
                
                return [
                    {
                        "id": r[0],
                        "provider": r[1],
                        "model_name": r[2],
                        "display_name": r[3],
                        "input_price_per_1k": float(r[4]),
                        "output_price_per_1k": float(r[5]),
                        "description": r[6],
                        "is_active": r[7],
                        "created_at": r[8].isoformat() if r[8] else None,
                        "updated_at": r[9].isoformat() if r[9] else None
                    }
                    for r in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"获取模型价格配置失败: {e}")
            return []
    
    @classmethod
    async def update_model_pricing(
        cls,
        pricing_id: int,
        input_price_per_1k: Optional[float] = None,
        output_price_per_1k: Optional[float] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """更新模型价格配置"""
        try:
            update_fields = []
            params = {"id": pricing_id}
            
            if input_price_per_1k is not None:
                update_fields.append("input_price_per_1k = :input_price")
                params["input_price"] = input_price_per_1k
            
            if output_price_per_1k is not None:
                update_fields.append("output_price_per_1k = :output_price")
                params["output_price"] = output_price_per_1k
            
            if is_active is not None:
                update_fields.append("is_active = :is_active")
                params["is_active"] = is_active
            
            if not update_fields:
                return False
            
            update_fields.append("updated_at = NOW()")
            
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"""
                        UPDATE ai_model_pricing
                        SET {', '.join(update_fields)}
                        WHERE id = :id
                    """),
                    params
                )
                await db.commit()
                
                # 清除价格缓存
                cls._cache_loaded = False
                cls._pricing_cache.clear()
                
                return True
                
        except Exception as e:
            logger.error(f"更新模型价格配置失败: {e}")
            return False


# 便捷函数
async def record_ai_usage(
    provider: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    **kwargs
) -> Optional[int]:
    """记录AI用量的便捷函数"""
    return await AIUsageService.record_usage(
        provider=provider,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        **kwargs
    )
