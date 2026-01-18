"""
语言检测服务
用于检测客户消息语言、根据姓名/公司名推断语言
"""
import re
from typing import Optional
from loguru import logger


class LanguageDetector:
    """语言检测器"""
    
    # 中文字符范围
    CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
    
    # 常见中文域名后缀
    CHINESE_DOMAINS = ['.cn', '.com.cn', '.net.cn', '.org.cn', '.中国', '.公司', '.网络']
    
    # 常见英文名前缀/后缀
    ENGLISH_NAME_PATTERNS = [
        r'\b(Mr|Mrs|Ms|Dr|Prof)\b',
        r'\b(John|James|Michael|David|Robert|William|Richard|Joseph|Thomas|Charles)\b',
        r'\b(Mary|Patricia|Jennifer|Linda|Elizabeth|Barbara|Susan|Jessica|Sarah|Karen)\b',
        r'\b(Smith|Johnson|Williams|Brown|Jones|Miller|Davis|Garcia|Rodriguez|Wilson)\b',
    ]
    
    def detect_text_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            'zh' 中文, 'en' 英文, 'auto' 无法确定
        """
        if not text or not text.strip():
            return 'auto'
        
        text = text.strip()
        
        # 统计中文字符数量
        chinese_chars = len(self.CHINESE_PATTERN.findall(text))
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            return 'auto'
        
        chinese_ratio = chinese_chars / total_chars
        
        # 如果中文占比超过20%，判定为中文
        if chinese_ratio > 0.2:
            return 'zh'
        
        # 如果几乎没有中文字符，判定为英文
        if chinese_ratio < 0.05:
            return 'en'
        
        return 'auto'
    
    def detect_from_name(self, name: str) -> str:
        """
        根据姓名推断语言
        
        Args:
            name: 姓名
            
        Returns:
            'zh' 中文, 'en' 英文, 'auto' 无法确定
        """
        if not name or not name.strip():
            return 'auto'
        
        name = name.strip()
        
        # 检查是否包含中文
        if self.CHINESE_PATTERN.search(name):
            return 'zh'
        
        # 检查是否匹配英文名模式
        for pattern in self.ENGLISH_NAME_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return 'en'
        
        # 如果全是英文字母和空格，可能是英文名
        if re.match(r'^[A-Za-z\s\-\.]+$', name):
            return 'en'
        
        return 'auto'
    
    def detect_from_email(self, email: str) -> str:
        """
        根据邮箱域名推断语言
        
        Args:
            email: 邮箱地址
            
        Returns:
            'zh' 中文, 'en' 英文, 'auto' 无法确定
        """
        if not email or '@' not in email:
            return 'auto'
        
        domain = email.split('@')[1].lower()
        
        # 检查是否是中国域名
        for cn_domain in self.CHINESE_DOMAINS:
            if domain.endswith(cn_domain):
                return 'zh'
        
        # 常见国际邮箱默认英文
        international_domains = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com']
        for intl_domain in international_domains:
            if domain == intl_domain:
                return 'en'
        
        return 'auto'
    
    def detect_from_company(self, company: str) -> str:
        """
        根据公司名推断语言
        
        Args:
            company: 公司名称
            
        Returns:
            'zh' 中文, 'en' 英文, 'auto' 无法确定
        """
        if not company or not company.strip():
            return 'auto'
        
        company = company.strip()
        
        # 检查是否包含中文
        if self.CHINESE_PATTERN.search(company):
            return 'zh'
        
        # 检查是否包含常见中国公司后缀
        chinese_suffixes = ['有限公司', '股份', '集团', '贸易', '物流', '科技', '实业']
        for suffix in chinese_suffixes:
            if suffix in company:
                return 'zh'
        
        # 检查是否包含常见英文公司后缀
        english_suffixes = ['Ltd', 'LLC', 'Inc', 'Corp', 'Co.', 'Company', 'Limited', 'Trading', 'Logistics']
        for suffix in english_suffixes:
            if suffix.lower() in company.lower():
                return 'en'
        
        # 如果全是英文字母和空格，可能是英文公司
        if re.match(r'^[A-Za-z0-9\s\-\.\&]+$', company):
            return 'en'
        
        return 'auto'
    
    def detect_customer_language(
        self, 
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        message: Optional[str] = None
    ) -> str:
        """
        综合判断客户语言
        优先级：消息内容 > 姓名 > 公司名 > 邮箱
        
        Args:
            name: 客户姓名
            email: 客户邮箱
            company: 客户公司
            message: 客户消息
            
        Returns:
            'zh' 中文, 'en' 英文, 'auto' 无法确定
        """
        # 优先检测消息内容
        if message:
            lang = self.detect_text_language(message)
            if lang != 'auto':
                logger.info(f"从消息内容检测到语言: {lang}")
                return lang
        
        # 其次检测姓名
        if name:
            lang = self.detect_from_name(name)
            if lang != 'auto':
                logger.info(f"从姓名检测到语言: {lang}")
                return lang
        
        # 再检测公司名
        if company:
            lang = self.detect_from_company(company)
            if lang != 'auto':
                logger.info(f"从公司名检测到语言: {lang}")
                return lang
        
        # 最后检测邮箱
        if email:
            lang = self.detect_from_email(email)
            if lang != 'auto':
                logger.info(f"从邮箱检测到语言: {lang}")
                return lang
        
        return 'auto'
    
    def get_effective_language(self, stored_language: str, fallback: str = 'zh') -> str:
        """
        获取有效语言（用于实际生成内容时）
        
        Args:
            stored_language: 存储的语言设置
            fallback: 默认语言
            
        Returns:
            'zh' 或 'en'
        """
        if stored_language in ['zh', 'en']:
            return stored_language
        return fallback


# 全局单例
language_detector = LanguageDetector()
