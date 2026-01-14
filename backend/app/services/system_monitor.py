"""
系统监控服务
负责：API状态监控、系统健康检查、证书监控
"""
import asyncio
import ssl
import socket
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from loguru import logger

from app.core.config import settings
from app.models.database import AsyncSessionLocal


class SystemMonitor:
    """系统监控服务"""
    
    # API配置列表
    API_CONFIGS = {
        "keling_ai": {
            "name": "可灵AI视频",
            "url": "https://api.klingai.com",
            "check_endpoint": "/v1/videos/text2video",
            "method": "health_check",
            "required": True
        },
        "dashscope": {
            "name": "通义千问",
            "url": "https://dashscope.aliyuncs.com",
            "check_endpoint": "/compatible-mode/v1/models",
            "method": "get",
            "required": True
        },
        "serper": {
            "name": "Serper搜索",
            "url": "https://google.serper.dev",
            "check_endpoint": "/search",
            "method": "health_check",
            "required": False
        }
    }
    
    # 需要监控的域名证书
    MONITORED_DOMAINS = [
        "api.klingai.com",
        "dashscope.aliyuncs.com"
    ]
    
    async def check_all_apis(self) -> Dict[str, Any]:
        """检查所有API状态"""
        results = {
            "check_time": datetime.now().isoformat(),
            "apis": {},
            "overall_status": "healthy",
            "unhealthy_count": 0
        }
        
        for api_id, config in self.API_CONFIGS.items():
            api_result = await self._check_single_api(api_id, config)
            results["apis"][api_id] = api_result
            
            if api_result["status"] != "available":
                results["unhealthy_count"] += 1
                if config.get("required"):
                    results["overall_status"] = "degraded"
        
        if results["unhealthy_count"] >= len(self.API_CONFIGS) // 2:
            results["overall_status"] = "unhealthy"
        
        # 保存到数据库
        await self._save_api_status(results)
        
        return results
    
    async def _check_single_api(
        self, 
        api_id: str, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查单个API状态"""
        result = {
            "name": config["name"],
            "url": config["url"],
            "status": "unknown",
            "response_time_ms": None,
            "error": None,
            "checked_at": datetime.now().isoformat()
        }
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient() as client:
                if config["method"] == "health_check":
                    # 简单的连接检查
                    response = await client.head(
                        config["url"],
                        timeout=10.0
                    )
                else:
                    response = await client.get(
                        f"{config['url']}{config['check_endpoint']}",
                        timeout=10.0
                    )
                
                end_time = asyncio.get_event_loop().time()
                response_time = int((end_time - start_time) * 1000)
                
                result["response_time_ms"] = response_time
                
                if response.status_code < 500:
                    result["status"] = "available"
                else:
                    result["status"] = "degraded"
                    result["error"] = f"HTTP {response.status_code}"
                    
        except httpx.TimeoutException:
            result["status"] = "unavailable"
            result["error"] = "请求超时"
        except Exception as e:
            result["status"] = "unavailable"
            result["error"] = str(e)
        
        return result
    
    async def check_database(self) -> Dict[str, Any]:
        """检查数据库连接状态"""
        result = {
            "component": "database",
            "status": "unknown",
            "response_time_ms": None,
            "details": {}
        }
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                await db.execute(text("SELECT 1"))
            
            end_time = asyncio.get_event_loop().time()
            
            result["status"] = "healthy"
            result["response_time_ms"] = int((end_time - start_time) * 1000)
            
        except Exception as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
        
        return result
    
    async def check_certificates(self) -> List[Dict[str, Any]]:
        """检查SSL证书状态"""
        results = []
        
        for domain in self.MONITORED_DOMAINS:
            cert_info = await self._check_certificate(domain)
            results.append(cert_info)
        
        # 保存到数据库
        await self._save_certificate_status(results)
        
        return results
    
    async def _check_certificate(self, domain: str) -> Dict[str, Any]:
        """检查单个域名的SSL证书"""
        result = {
            "domain": domain,
            "status": "unknown",
            "valid_from": None,
            "valid_until": None,
            "days_until_expiry": None,
            "issuer": None
        }
        
        try:
            loop = asyncio.get_event_loop()
            cert_info = await loop.run_in_executor(
                None, self._get_certificate_sync, domain
            )
            result.update(cert_info)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    def _get_certificate_sync(self, domain: str) -> Dict[str, Any]:
        """同步获取证书信息"""
        context = ssl.create_default_context()
        
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        
        # 解析证书信息
        not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
        days_until_expiry = (not_after - datetime.now()).days
        
        # 确定状态
        if days_until_expiry < 0:
            status = "expired"
        elif days_until_expiry < 30:
            status = "expiring_soon"
        else:
            status = "valid"
        
        # 获取颁发者
        issuer = dict(x[0] for x in cert['issuer'])
        issuer_name = issuer.get('organizationName', issuer.get('commonName', 'Unknown'))
        
        return {
            "status": status,
            "valid_from": not_before.isoformat(),
            "valid_until": not_after.isoformat(),
            "days_until_expiry": days_until_expiry,
            "issuer": issuer_name
        }
    
    async def get_system_health_summary(self) -> Dict[str, Any]:
        """获取系统健康状态摘要"""
        # 并行检查所有组件
        api_task = self.check_all_apis()
        db_task = self.check_database()
        cert_task = self.check_certificates()
        
        api_results, db_result, cert_results = await asyncio.gather(
            api_task, db_task, cert_task
        )
        
        # 计算整体健康状态
        issues = []
        
        if api_results["overall_status"] != "healthy":
            issues.append(f"API状态异常: {api_results['unhealthy_count']}个不可用")
        
        if db_result["status"] != "healthy":
            issues.append("数据库连接异常")
        
        expiring_certs = [c for c in cert_results if c.get("status") == "expiring_soon"]
        if expiring_certs:
            issues.append(f"{len(expiring_certs)}个证书即将过期")
        
        expired_certs = [c for c in cert_results if c.get("status") == "expired"]
        if expired_certs:
            issues.append(f"{len(expired_certs)}个证书已过期")
        
        overall_status = "healthy"
        if issues:
            overall_status = "warning" if len(issues) == 1 else "critical"
        
        return {
            "check_time": datetime.now().isoformat(),
            "overall_status": overall_status,
            "issues": issues,
            "components": {
                "apis": api_results,
                "database": db_result,
                "certificates": cert_results
            }
        }
    
    async def _save_api_status(self, results: Dict[str, Any]):
        """保存API状态到数据库"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                for api_id, api_data in results.get("apis", {}).items():
                    await db.execute(
                        text("""
                            INSERT INTO api_status_logs 
                            (api_name, api_url, status, response_time_ms, error_message, checked_at)
                            VALUES (:name, :url, :status, :response_time, :error, NOW())
                        """),
                        {
                            "name": api_id,
                            "url": api_data.get("url"),
                            "status": api_data.get("status"),
                            "response_time": api_data.get("response_time_ms"),
                            "error": api_data.get("error")
                        }
                    )
                await db.commit()
        except Exception as e:
            logger.error(f"保存API状态失败: {e}")
    
    async def _save_certificate_status(self, results: List[Dict[str, Any]]):
        """保存证书状态到数据库"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                for cert in results:
                    await db.execute(
                        text("""
                            INSERT INTO certificate_status 
                            (domain, issuer, valid_from, valid_until, days_until_expiry, status, last_check_at)
                            VALUES (:domain, :issuer, :valid_from, :valid_until, :days, :status, NOW())
                            ON CONFLICT (domain) DO UPDATE SET
                                issuer = EXCLUDED.issuer,
                                valid_from = EXCLUDED.valid_from,
                                valid_until = EXCLUDED.valid_until,
                                days_until_expiry = EXCLUDED.days_until_expiry,
                                status = EXCLUDED.status,
                                last_check_at = NOW()
                        """),
                        {
                            "domain": cert.get("domain"),
                            "issuer": cert.get("issuer"),
                            "valid_from": cert.get("valid_from"),
                            "valid_until": cert.get("valid_until"),
                            "days": cert.get("days_until_expiry"),
                            "status": cert.get("status")
                        }
                    )
                await db.commit()
        except Exception as e:
            logger.error(f"保存证书状态失败: {e}")


# 创建服务实例
system_monitor = SystemMonitor()
