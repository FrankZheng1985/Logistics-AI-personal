"""
ERP数据隐私保护服务
负责：数据脱敏、敏感字段过滤、访问审计

安全策略：
1. 自动识别并脱敏敏感数据（手机号、银行账号、身份证等）
2. 过滤财务详细数据，只返回汇总信息
3. 记录所有数据访问审计日志
4. 缓存数据加密存储
"""
import re
import json
import hashlib
import base64
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from loguru import logger
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class DataMasker:
    """
    数据脱敏器
    
    支持脱敏的数据类型：
    - 手机号码
    - 身份证号
    - 银行卡号
    - 邮箱地址
    - 姓名
    - 地址
    - 金额（可选）
    """
    
    # 手机号正则（中国大陆）
    PHONE_PATTERN = re.compile(r'1[3-9]\d{9}')
    
    # 身份证号正则（18位）
    ID_CARD_PATTERN = re.compile(r'\d{17}[\dXx]')
    
    # 银行卡号正则（16-19位）
    BANK_CARD_PATTERN = re.compile(r'\d{16,19}')
    
    # 邮箱正则
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    
    # 需要脱敏的字段名（不区分大小写）
    SENSITIVE_FIELDS = {
        # 手机号相关
        'phone', 'mobile', 'tel', 'telephone', 'cellphone',
        'contactPhone', 'contact_phone', 'mobilePhone', 'mobile_phone',
        # 身份证相关
        'idcard', 'id_card', 'idNumber', 'id_number', 'identityCard',
        # 银行卡相关
        'bankCard', 'bank_card', 'cardNumber', 'card_number',
        'bankAccount', 'bank_account', 'accountNumber', 'account_number',
        # 邮箱相关
        'email', 'mail', 'emailAddress', 'email_address',
        # 地址相关
        'address', 'detailAddress', 'detail_address', 'fullAddress',
        # 联系人相关
        'contactName', 'contact_name', 'contactPerson', 'contact_person',
    }
    
    # 需要完全隐藏的字段（财务敏感）
    HIDDEN_FIELDS = {
        'password', 'secret', 'token', 'apiKey', 'api_key',
        'privateKey', 'private_key', 'credential',
    }
    
    # 需要模糊化的金额字段（只显示范围）
    AMOUNT_FIELDS = {
        'amount', 'totalAmount', 'total_amount', 'price', 'cost',
        'profit', 'revenue', 'balance', 'payment', 'receivable',
        'payable', 'fee', 'charge', 'income', 'expense',
    }
    
    @classmethod
    def mask_phone(cls, phone: str) -> str:
        """
        脱敏手机号
        13812345678 -> 138****5678
        """
        if not phone or len(phone) < 7:
            return phone
        return f"{phone[:3]}****{phone[-4:]}"
    
    @classmethod
    def mask_id_card(cls, id_card: str) -> str:
        """
        脱敏身份证号
        110101199001011234 -> 110101********1234
        """
        if not id_card or len(id_card) < 10:
            return id_card
        return f"{id_card[:6]}********{id_card[-4:]}"
    
    @classmethod
    def mask_bank_card(cls, card: str) -> str:
        """
        脱敏银行卡号
        6222021234567890123 -> 6222****0123
        """
        if not card or len(card) < 8:
            return card
        return f"{card[:4]}****{card[-4:]}"
    
    @classmethod
    def mask_email(cls, email: str) -> str:
        """
        脱敏邮箱
        example@domain.com -> exa***@domain.com
        """
        if not email or '@' not in email:
            return email
        parts = email.split('@')
        username = parts[0]
        domain = parts[1]
        if len(username) <= 3:
            masked_username = username[0] + '***'
        else:
            masked_username = username[:3] + '***'
        return f"{masked_username}@{domain}"
    
    @classmethod
    def mask_name(cls, name: str) -> str:
        """
        脱敏姓名
        张三 -> 张*
        张三丰 -> 张*丰
        """
        if not name or len(name) < 2:
            return name
        if len(name) == 2:
            return f"{name[0]}*"
        return f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}"
    
    @classmethod
    def mask_address(cls, address: str) -> str:
        """
        脱敏地址（保留省市，隐藏详细地址）
        """
        if not address or len(address) < 10:
            return address
        # 尝试提取省市信息
        province_city = address[:6] if len(address) > 6 else address[:len(address)//2]
        return f"{province_city}****"
    
    @classmethod
    def mask_amount(cls, amount: Union[int, float, str], show_range: bool = True) -> str:
        """
        脱敏金额（转为范围显示）
        12345.67 -> "1万-5万" 或 "****"
        """
        try:
            value = float(amount) if isinstance(amount, str) else amount
            
            if not show_range:
                return "****"
            
            if value < 1000:
                return "1千以下"
            elif value < 10000:
                return "1千-1万"
            elif value < 50000:
                return "1万-5万"
            elif value < 100000:
                return "5万-10万"
            elif value < 500000:
                return "10万-50万"
            elif value < 1000000:
                return "50万-100万"
            else:
                return "100万以上"
        except (ValueError, TypeError):
            return "****"
    
    @classmethod
    def mask_string_content(cls, text: str) -> str:
        """
        自动检测并脱敏字符串中的敏感信息
        """
        if not text or not isinstance(text, str):
            return text
        
        result = text
        
        # 脱敏手机号
        for match in cls.PHONE_PATTERN.finditer(text):
            phone = match.group()
            result = result.replace(phone, cls.mask_phone(phone))
        
        # 脱敏身份证
        for match in cls.ID_CARD_PATTERN.finditer(text):
            id_card = match.group()
            result = result.replace(id_card, cls.mask_id_card(id_card))
        
        # 脱敏邮箱
        for match in cls.EMAIL_PATTERN.finditer(text):
            email = match.group()
            result = result.replace(email, cls.mask_email(email))
        
        return result
    
    @classmethod
    def is_sensitive_field(cls, field_name: str) -> bool:
        """判断是否为敏感字段"""
        field_lower = field_name.lower()
        return field_lower in cls.SENSITIVE_FIELDS or any(
            s in field_lower for s in ['phone', 'mobile', 'email', 'card', 'account', 'address', 'contact']
        )
    
    @classmethod
    def is_hidden_field(cls, field_name: str) -> bool:
        """判断是否为完全隐藏字段"""
        field_lower = field_name.lower()
        return field_lower in cls.HIDDEN_FIELDS or any(
            s in field_lower for s in ['password', 'secret', 'token', 'key', 'credential']
        )
    
    @classmethod
    def is_amount_field(cls, field_name: str) -> bool:
        """判断是否为金额字段"""
        field_lower = field_name.lower()
        return field_lower in cls.AMOUNT_FIELDS or any(
            s in field_lower for s in ['amount', 'price', 'cost', 'fee', 'balance', 'total']
        )


class ERPDataPrivacyService:
    """
    ERP数据隐私保护服务
    
    功能：
    1. 自动脱敏敏感数据
    2. 过滤敏感字段
    3. 加密缓存数据
    4. 记录审计日志
    """
    
    # 加密密钥（生产环境应从环境变量获取）
    _encryption_key: Optional[bytes] = None
    _fernet: Optional[Fernet] = None
    
    # 需要详细审计的接口
    AUDIT_ENDPOINTS = {
        '/internal-api/customers',
        '/internal-api/orders',
        '/internal-api/invoices',
        '/internal-api/payments',
        '/internal-api/financial-summary',
    }
    
    @classmethod
    def _get_fernet(cls) -> Fernet:
        """获取加密器"""
        if cls._fernet is None:
            # 从环境变量或配置获取密钥种子
            # 生产环境应该使用更安全的密钥管理
            key_seed = "logistics-ai-erp-privacy-2024"
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'logistics_ai_salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key_seed.encode()))
            cls._fernet = Fernet(key)
        
        return cls._fernet
    
    @classmethod
    def encrypt_data(cls, data: Union[str, Dict]) -> str:
        """
        加密数据
        
        用于缓存敏感数据时加密存储
        """
        try:
            fernet = cls._get_fernet()
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False, default=str)
            encrypted = fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    @classmethod
    def decrypt_data(cls, encrypted_data: str) -> Union[str, Dict]:
        """
        解密数据
        """
        try:
            fernet = cls._get_fernet()
            decrypted = fernet.decrypt(encrypted_data.encode())
            data = decrypted.decode()
            # 尝试解析为JSON
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise
    
    @classmethod
    def mask_erp_response(
        cls, 
        data: Union[Dict, List], 
        mask_amounts: bool = True,
        mask_contacts: bool = True
    ) -> Union[Dict, List]:
        """
        脱敏ERP响应数据
        
        递归处理所有字段，自动识别并脱敏敏感信息
        
        参数:
            data: 原始数据
            mask_amounts: 是否脱敏金额（默认True）
            mask_contacts: 是否脱敏联系方式（默认True）
        
        返回:
            脱敏后的数据
        """
        if data is None:
            return data
        
        if isinstance(data, list):
            return [cls.mask_erp_response(item, mask_amounts, mask_contacts) for item in data]
        
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                # 完全隐藏的字段
                if DataMasker.is_hidden_field(key):
                    masked_data[key] = "[已隐藏]"
                    continue
                
                # 递归处理嵌套对象
                if isinstance(value, (dict, list)):
                    masked_data[key] = cls.mask_erp_response(value, mask_amounts, mask_contacts)
                    continue
                
                # 金额字段脱敏
                if mask_amounts and DataMasker.is_amount_field(key):
                    if isinstance(value, (int, float)):
                        masked_data[key] = DataMasker.mask_amount(value)
                    else:
                        masked_data[key] = value
                    continue
                
                # 联系方式脱敏
                if mask_contacts and DataMasker.is_sensitive_field(key):
                    if isinstance(value, str):
                        key_lower = key.lower()
                        if 'phone' in key_lower or 'mobile' in key_lower or 'tel' in key_lower:
                            masked_data[key] = DataMasker.mask_phone(value)
                        elif 'email' in key_lower or 'mail' in key_lower:
                            masked_data[key] = DataMasker.mask_email(value)
                        elif 'card' in key_lower or 'account' in key_lower:
                            masked_data[key] = DataMasker.mask_bank_card(value)
                        elif 'address' in key_lower:
                            masked_data[key] = DataMasker.mask_address(value)
                        elif 'name' in key_lower and 'company' not in key_lower:
                            # 联系人姓名脱敏，但公司名不脱敏
                            masked_data[key] = DataMasker.mask_name(value)
                        else:
                            masked_data[key] = DataMasker.mask_string_content(value)
                    else:
                        masked_data[key] = value
                    continue
                
                # 字符串内容自动检测脱敏
                if isinstance(value, str):
                    masked_data[key] = DataMasker.mask_string_content(value)
                else:
                    masked_data[key] = value
            
            return masked_data
        
        # 其他类型直接返回
        return data
    
    @classmethod
    def filter_sensitive_fields(
        cls, 
        data: Union[Dict, List],
        allowed_fields: Optional[List[str]] = None,
        blocked_fields: Optional[List[str]] = None
    ) -> Union[Dict, List]:
        """
        过滤敏感字段
        
        可以指定允许的字段列表或禁止的字段列表
        """
        if data is None:
            return data
        
        if isinstance(data, list):
            return [cls.filter_sensitive_fields(item, allowed_fields, blocked_fields) for item in data]
        
        if isinstance(data, dict):
            filtered_data = {}
            for key, value in data.items():
                # 检查是否在禁止列表
                if blocked_fields and key.lower() in [f.lower() for f in blocked_fields]:
                    continue
                
                # 检查是否在允许列表
                if allowed_fields and key.lower() not in [f.lower() for f in allowed_fields]:
                    continue
                
                # 递归处理
                if isinstance(value, (dict, list)):
                    filtered_data[key] = cls.filter_sensitive_fields(value, allowed_fields, blocked_fields)
                else:
                    filtered_data[key] = value
            
            return filtered_data
        
        return data
    
    @classmethod
    async def log_access(
        cls,
        endpoint: str,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
        params: Optional[Dict] = None,
        data_count: int = 0,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        记录数据访问审计日志
        """
        try:
            async with AsyncSessionLocal() as db:
                # 脱敏参数中的敏感信息
                safe_params = cls._sanitize_params(params) if params else {}
                params_json = json.dumps(safe_params, ensure_ascii=False, default=str)
                
                # 准备值
                safe_user_id = user_id or "anonymous"
                safe_user_ip = user_ip or "unknown"
                success_str = "true" if success else "false"
                error_str = "NULL" if error_message is None else f"'{error_message}'"
                
                # 转义单引号防止SQL注入
                endpoint_safe = endpoint.replace("'", "''")
                safe_user_id = safe_user_id.replace("'", "''")
                safe_user_ip = safe_user_ip.replace("'", "''")
                params_json_safe = params_json.replace("'", "''")
                
                sql = f"""
                    INSERT INTO erp_access_audit 
                    (endpoint, user_id, user_ip, params, data_count, success, error_message, created_at)
                    VALUES (
                        '{endpoint_safe}', 
                        '{safe_user_id}', 
                        '{safe_user_ip}', 
                        '{params_json_safe}'::jsonb, 
                        {data_count}, 
                        {success_str}, 
                        {error_str}, 
                        NOW()
                    )
                """
                
                await db.execute(text(sql))
                await db.commit()
        except Exception as e:
            # 审计日志记录失败不应该影响主业务
            logger.warning(f"记录审计日志失败: {e}")
    
    @classmethod
    def _sanitize_params(cls, params: Dict) -> Dict:
        """
        清理参数中的敏感信息
        移除空值、脱敏敏感参数
        """
        if not params:
            return {}
        
        safe_params = {}
        sensitive_param_names = {'token', 'password', 'secret', 'key', 'auth'}
        
        for key, value in params.items():
            # 跳过空值
            if value is None:
                continue
            # 隐藏敏感参数
            if any(s in key.lower() for s in sensitive_param_names):
                safe_params[key] = "[已隐藏]"
            else:
                safe_params[key] = value
        
        return safe_params
    
    @classmethod
    async def get_access_logs(
        cls,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取访问审计日志
        """
        try:
            async with AsyncSessionLocal() as db:
                query = """
                    SELECT id, endpoint, user_id, user_ip, params, data_count, 
                           success, error_message, created_at
                    FROM erp_access_audit
                    WHERE 1=1
                """
                query_params = {}
                
                if endpoint:
                    query += " AND endpoint = :endpoint"
                    query_params["endpoint"] = endpoint
                
                if user_id:
                    query += " AND user_id = :user_id"
                    query_params["user_id"] = user_id
                
                if start_date:
                    query += " AND created_at >= :start_date"
                    query_params["start_date"] = start_date
                
                if end_date:
                    query += " AND created_at <= :end_date"
                    query_params["end_date"] = end_date
                
                query += " ORDER BY created_at DESC LIMIT :limit"
                query_params["limit"] = limit
                
                result = await db.execute(text(query), query_params)
                rows = result.fetchall()
                
                logs = []
                for row in rows:
                    # 处理params字段 - 可能是dict或str
                    params_value = row[4]
                    if isinstance(params_value, str):
                        try:
                            params_value = json.loads(params_value)
                        except:
                            params_value = {}
                    elif params_value is None:
                        params_value = {}
                    
                    logs.append({
                        "id": str(row[0]),
                        "endpoint": row[1],
                        "user_id": row[2],
                        "user_ip": row[3],
                        "params": params_value,
                        "data_count": row[5] or 0,
                        "success": row[6],
                        "error_message": row[7],
                        "created_at": row[8].isoformat() if row[8] else None
                    })
                
                return logs
        except Exception as e:
            logger.error(f"获取审计日志失败: {e}")
            return []


# 创建全局实例
data_masker = DataMasker()
privacy_service = ERPDataPrivacyService()
