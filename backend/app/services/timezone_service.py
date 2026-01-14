"""
时区服务 - 智能免打扰系统
根据客户所在时区，在客户休息时间避免发送消息
"""
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List, Tuple
import pytz
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker


# 欧洲业务相关时区配置
TIMEZONE_CONFIG = {
    # 中国客户（主要客户群）
    "中国": {"timezone": "Asia/Shanghai", "dnd_start": "22:00", "dnd_end": "08:00"},
    "香港": {"timezone": "Asia/Hong_Kong", "dnd_start": "22:00", "dnd_end": "08:00"},
    "台湾": {"timezone": "Asia/Taipei", "dnd_start": "22:00", "dnd_end": "08:00"},
    
    # 欧洲客户
    "德国": {"timezone": "Europe/Berlin", "dnd_start": "22:00", "dnd_end": "08:00"},
    "法国": {"timezone": "Europe/Paris", "dnd_start": "22:00", "dnd_end": "08:00"},
    "英国": {"timezone": "Europe/London", "dnd_start": "22:00", "dnd_end": "08:00"},
    "荷兰": {"timezone": "Europe/Amsterdam", "dnd_start": "22:00", "dnd_end": "08:00"},
    "意大利": {"timezone": "Europe/Rome", "dnd_start": "22:00", "dnd_end": "08:00"},
    "西班牙": {"timezone": "Europe/Madrid", "dnd_start": "22:00", "dnd_end": "08:00"},
    "波兰": {"timezone": "Europe/Warsaw", "dnd_start": "22:00", "dnd_end": "08:00"},
    "比利时": {"timezone": "Europe/Brussels", "dnd_start": "22:00", "dnd_end": "08:00"},
    
    # 其他常见地区
    "美国东部": {"timezone": "America/New_York", "dnd_start": "22:00", "dnd_end": "08:00"},
    "美国西部": {"timezone": "America/Los_Angeles", "dnd_start": "22:00", "dnd_end": "08:00"},
    "日本": {"timezone": "Asia/Tokyo", "dnd_start": "22:00", "dnd_end": "08:00"},
    "韩国": {"timezone": "Asia/Seoul", "dnd_start": "22:00", "dnd_end": "08:00"},
}


class TimezoneService:
    """时区服务"""
    
    def __init__(self):
        self.default_timezone = "Asia/Shanghai"
        self.server_timezone = pytz.timezone("Asia/Shanghai")
    
    def get_timezone_by_country(self, country: str) -> str:
        """根据国家获取时区"""
        config = TIMEZONE_CONFIG.get(country)
        if config:
            return config["timezone"]
        return self.default_timezone
    
    def get_dnd_times_by_country(self, country: str) -> Tuple[str, str]:
        """根据国家获取免打扰时间"""
        config = TIMEZONE_CONFIG.get(country, TIMEZONE_CONFIG["中国"])
        return config["dnd_start"], config["dnd_end"]
    
    def get_customer_local_time(self, timezone_str: str) -> datetime:
        """获取客户当地时间"""
        try:
            tz = pytz.timezone(timezone_str)
            return datetime.now(tz)
        except:
            return datetime.now(self.server_timezone)
    
    def is_in_dnd_period(
        self,
        timezone_str: str,
        dnd_start: time = time(22, 0),
        dnd_end: time = time(8, 0)
    ) -> bool:
        """
        检查当前是否在客户的免打扰时间内
        
        Args:
            timezone_str: 客户时区
            dnd_start: 免打扰开始时间 (客户当地时间)
            dnd_end: 免打扰结束时间 (客户当地时间)
        
        Returns:
            True 如果在免打扰时间内
        """
        try:
            tz = pytz.timezone(timezone_str)
            customer_now = datetime.now(tz)
            current_time = customer_now.time()
            
            # 处理跨天的情况 (例如 22:00 - 08:00)
            if dnd_start > dnd_end:
                # 跨天：22:00-23:59 或 00:00-08:00
                return current_time >= dnd_start or current_time <= dnd_end
            else:
                # 不跨天
                return dnd_start <= current_time <= dnd_end
                
        except Exception as e:
            logger.error(f"检查免打扰时间失败: {e}")
            return False
    
    def get_next_available_time(
        self,
        timezone_str: str,
        dnd_end: time = time(8, 0)
    ) -> datetime:
        """
        获取客户下一个可联系时间（免打扰结束后）
        
        Args:
            timezone_str: 客户时区
            dnd_end: 免打扰结束时间
        
        Returns:
            下一个可联系的datetime (服务器时间)
        """
        try:
            tz = pytz.timezone(timezone_str)
            customer_now = datetime.now(tz)
            
            # 构建今天的免打扰结束时间
            today_dnd_end = customer_now.replace(
                hour=dnd_end.hour,
                minute=dnd_end.minute,
                second=0,
                microsecond=0
            )
            
            # 如果当前时间已经过了今天的免打扰结束时间，则返回明天的
            if customer_now.time() > dnd_end:
                next_available = today_dnd_end + timedelta(days=1)
            else:
                next_available = today_dnd_end
            
            # 转换为服务器时间
            return next_available.astimezone(self.server_timezone)
            
        except Exception as e:
            logger.error(f"计算下一个可联系时间失败: {e}")
            # 默认返回明天早上9点（北京时间）
            tomorrow = datetime.now(self.server_timezone) + timedelta(days=1)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    async def check_customer_dnd(self, customer_id: str) -> Dict[str, Any]:
        """
        检查客户是否在免打扰时间
        
        Returns:
            {
                "is_dnd": True/False,
                "customer_local_time": "当地时间",
                "next_available": "下一个可联系时间",
                "reason": "原因说明"
            }
        """
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT timezone, dnd_start, dnd_end, dnd_enabled, country, name
                        FROM customers
                        WHERE id = :customer_id
                    """),
                    {"customer_id": customer_id}
                )
                row = result.fetchone()
                
                if not row:
                    return {
                        "is_dnd": False,
                        "reason": "客户不存在"
                    }
                
                timezone_str = row[0] or self.default_timezone
                dnd_start = row[1] or time(22, 0)
                dnd_end = row[2] or time(8, 0)
                dnd_enabled = row[3] if row[3] is not None else True
                country = row[4] or "未知"
                customer_name = row[5] or "未知"
                
                # 如果客户禁用了免打扰
                if not dnd_enabled:
                    return {
                        "is_dnd": False,
                        "customer_name": customer_name,
                        "reason": "客户已禁用免打扰"
                    }
                
                # 检查是否在免打扰时间
                is_dnd = self.is_in_dnd_period(timezone_str, dnd_start, dnd_end)
                customer_local_time = self.get_customer_local_time(timezone_str)
                
                result = {
                    "is_dnd": is_dnd,
                    "customer_name": customer_name,
                    "country": country,
                    "timezone": timezone_str,
                    "customer_local_time": customer_local_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "dnd_start": str(dnd_start),
                    "dnd_end": str(dnd_end)
                }
                
                if is_dnd:
                    next_available = self.get_next_available_time(timezone_str, dnd_end)
                    result["next_available"] = next_available.strftime("%Y-%m-%d %H:%M:%S")
                    result["reason"] = f"客户({country})当地时间 {customer_local_time.strftime('%H:%M')}，处于休息时间"
                else:
                    result["reason"] = f"客户({country})当地时间 {customer_local_time.strftime('%H:%M')}，可以联系"
                
                return result
                
        except Exception as e:
            logger.error(f"检查客户免打扰状态失败: {e}")
            return {
                "is_dnd": False,
                "reason": f"检查失败: {e}"
            }
    
    async def get_contactable_customers(
        self,
        customer_ids: List[str] = None,
        intent_levels: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取当前可联系的客户列表
        过滤掉处于免打扰时间的客户
        
        Args:
            customer_ids: 客户ID列表（可选，不传则获取所有）
            intent_levels: 意向等级筛选
        
        Returns:
            可联系的客户列表
        """
        try:
            async with async_session_maker() as db:
                # 构建查询
                query = """
                    SELECT id, name, company, timezone, dnd_start, dnd_end, 
                           dnd_enabled, country, intent_level, intent_score
                    FROM customers
                    WHERE 1=1
                """
                params = {}
                
                if customer_ids:
                    query += " AND id = ANY(:customer_ids)"
                    params["customer_ids"] = customer_ids
                
                if intent_levels:
                    query += " AND intent_level = ANY(:intent_levels)"
                    params["intent_levels"] = intent_levels
                
                result = await db.execute(text(query), params)
                rows = result.fetchall()
                
                contactable = []
                for row in rows:
                    customer_id = str(row[0])
                    timezone_str = row[3] or self.default_timezone
                    dnd_start = row[4] or time(22, 0)
                    dnd_end = row[5] or time(8, 0)
                    dnd_enabled = row[6] if row[6] is not None else True
                    
                    # 检查是否可联系
                    if not dnd_enabled:
                        is_contactable = True
                    else:
                        is_contactable = not self.is_in_dnd_period(timezone_str, dnd_start, dnd_end)
                    
                    if is_contactable:
                        contactable.append({
                            "id": customer_id,
                            "name": row[1],
                            "company": row[2],
                            "timezone": timezone_str,
                            "country": row[7],
                            "intent_level": row[8],
                            "intent_score": row[9],
                            "local_time": self.get_customer_local_time(timezone_str).strftime("%H:%M")
                        })
                
                return contactable
                
        except Exception as e:
            logger.error(f"获取可联系客户列表失败: {e}")
            return []
    
    async def schedule_for_timezone(
        self,
        customer_id: str,
        action_type: str,
        action_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据客户时区安排任务
        如果当前在免打扰时间，则安排到下一个可联系时间
        
        Args:
            customer_id: 客户ID
            action_type: 动作类型
            action_data: 动作数据
        
        Returns:
            {
                "scheduled": True/False,
                "execute_at": "执行时间",
                "reason": "原因"
            }
        """
        dnd_check = await self.check_customer_dnd(customer_id)
        
        if dnd_check.get("is_dnd"):
            # 在免打扰时间，安排到队列
            next_available = dnd_check.get("next_available")
            
            try:
                async with async_session_maker() as db:
                    await db.execute(
                        text("""
                            INSERT INTO task_queue 
                            (task_type, task_data, scheduled_at, assigned_to, status, created_at)
                            VALUES (:task_type, :task_data, :scheduled_at, 'follow', 'pending', NOW())
                        """),
                        {
                            "task_type": action_type,
                            "task_data": {
                                "customer_id": customer_id,
                                **action_data
                            },
                            "scheduled_at": next_available
                        }
                    )
                    await db.commit()
                
                return {
                    "scheduled": True,
                    "execute_at": next_available,
                    "reason": dnd_check.get("reason"),
                    "immediate": False
                }
                
            except Exception as e:
                logger.error(f"安排任务失败: {e}")
                return {
                    "scheduled": False,
                    "reason": f"安排失败: {e}"
                }
        else:
            # 不在免打扰时间，可以立即执行
            return {
                "scheduled": True,
                "execute_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reason": dnd_check.get("reason"),
                "immediate": True
            }


# 创建单例
timezone_service = TimezoneService()


# 便捷函数
async def check_can_contact(customer_id: str) -> bool:
    """检查是否可以联系客户"""
    result = await timezone_service.check_customer_dnd(customer_id)
    return not result.get("is_dnd", False)


def get_customer_local_time(timezone_str: str) -> datetime:
    """获取客户当地时间"""
    return timezone_service.get_customer_local_time(timezone_str)
