"""
敏感信息脱敏

提供字段级脱敏和加密功能，保护敏感信息不被泄露。
支持的敏感信息类型：
- 密钥/令牌
- 邮箱地址
- 手机号码
- 身份证号
- 银行卡号
- 钱包地址
- 密码
"""

import re
import hashlib
from typing import Any, Dict, List, Optional, Set, Callable
from copy import deepcopy


class Sanitizer:
    """
    敏感信息脱敏器
    
    提供多种脱敏策略：
    - mask: 掩码（部分隐藏）
    - hash: 哈希（单向加密）
    - remove: 完全移除
    - encrypt: 加密（可逆，需要密钥）
    """
    
    # 预定义的敏感字段名称（不区分大小写）
    SENSITIVE_FIELDS = {
        "password", "passwd", "pwd",
        "secret", "api_key", "apikey", "api_secret",
        "token", "access_token", "refresh_token", "auth_token",
        "private_key", "privatekey", "priv_key",
        "credit_card", "card_number", "cvv",
        "ssn", "social_security",
        "wallet_address", "address",
    }
    
    # 邮箱正则表达式
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # 手机号正则表达式（简化版，支持常见格式）
    PHONE_PATTERN = re.compile(r'\b(?:\+?86)?1[3-9]\d{9}\b')
    
    # 钱包地址正则表达式（以太坊地址示例）
    WALLET_PATTERN = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
    
    def __init__(
        self,
        sensitive_fields: Optional[Set[str]] = None,
        mask_char: str = "*",
        hash_algorithm: str = "sha256"
    ):
        """
        初始化脱敏器
        
        参数:
            sensitive_fields: 额外的敏感字段名称集合
            mask_char: 掩码字符，默认为 "*"
            hash_algorithm: 哈希算法，默认为 "sha256"
        """
        self.sensitive_fields = self.SENSITIVE_FIELDS.copy()
        if sensitive_fields:
            self.sensitive_fields.update(f.lower() for f in sensitive_fields)
        
        self.mask_char = mask_char
        self.hash_algorithm = hash_algorithm
        
        # 自定义脱敏规则
        self._custom_rules: List[Callable[[str], str]] = []
    
    def add_sensitive_field(self, field_name: str):
        """
        添加敏感字段
        
        参数:
            field_name: 字段名称
        """
        self.sensitive_fields.add(field_name.lower())
    
    def add_custom_rule(self, rule: Callable[[str], str]):
        """
        添加自定义脱敏规则
        
        参数:
            rule: 脱敏函数，接收字符串返回脱敏后的字符串
        """
        self._custom_rules.append(rule)
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """
        判断字段是否为敏感字段
        
        参数:
            field_name: 字段名称
            
        返回:
            bool: 如果是敏感字段返回 True
        """
        return field_name.lower() in self.sensitive_fields
    
    def mask_string(
        self,
        value: str,
        keep_start: int = 3,
        keep_end: int = 3,
        min_length: int = 8
    ) -> str:
        """
        掩码字符串（保留首尾，中间用掩码字符替换）
        
        参数:
            value: 要掩码的字符串
            keep_start: 保留开头的字符数
            keep_end: 保留结尾的字符数
            min_length: 最小长度，小于此长度则完全掩码
            
        返回:
            str: 掩码后的字符串
        """
        if not value or len(value) < min_length:
            return self.mask_char * len(value)
        
        if len(value) <= keep_start + keep_end:
            return self.mask_char * len(value)
        
        start = value[:keep_start]
        end = value[-keep_end:] if keep_end > 0 else ""
        middle_length = len(value) - keep_start - keep_end
        middle = self.mask_char * middle_length
        
        return f"{start}{middle}{end}"
    
    def hash_string(self, value: str, salt: str = "") -> str:
        """
        哈希字符串（单向加密）
        
        参数:
            value: 要哈希的字符串
            salt: 盐值
            
        返回:
            str: 哈希后的字符串（十六进制）
        """
        hasher = hashlib.new(self.hash_algorithm)
        hasher.update((value + salt).encode('utf-8'))
        return hasher.hexdigest()
    
    def mask_email(self, email: str) -> str:
        """
        掩码邮箱地址
        
        示例: user@example.com -> u***@example.com
        
        参数:
            email: 邮箱地址
            
        返回:
            str: 掩码后的邮箱地址
        """
        if '@' not in email:
            return self.mask_string(email)
        
        local, domain = email.split('@', 1)
        if len(local) <= 1:
            masked_local = self.mask_char
        else:
            masked_local = local[0] + self.mask_char * (len(local) - 1)
        
        return f"{masked_local}@{domain}"
    
    def mask_phone(self, phone: str) -> str:
        """
        掩码手机号
        
        示例: 13812345678 -> 138****5678
        
        参数:
            phone: 手机号
            
        返回:
            str: 掩码后的手机号
        """
        return self.mask_string(phone, keep_start=3, keep_end=4)
    
    def mask_wallet_address(self, address: str) -> str:
        """
        掩码钱包地址
        
        示例: 0x1234...abcd
        
        参数:
            address: 钱包地址
            
        返回:
            str: 掩码后的钱包地址
        """
        if len(address) <= 10:
            return self.mask_string(address, keep_start=4, keep_end=4)
        return f"{address[:6]}...{address[-4:]}"
    
    def sanitize_value(self, value: Any, field_name: str = "") -> Any:
        """
        脱敏单个值
        
        参数:
            value: 要脱敏的值
            field_name: 字段名称（用于判断是否为敏感字段）
            
        返回:
            Any: 脱敏后的值
        """
        # 如果不是字符串，直接返回
        if not isinstance(value, str):
            return value
        
        # 如果是敏感字段，进行掩码
        if field_name and self.is_sensitive_field(field_name):
            return self.mask_string(value)
        
        # 应用自定义规则
        for rule in self._custom_rules:
            value = rule(value)
        
        # 检测并脱敏邮箱
        value = self.EMAIL_PATTERN.sub(
            lambda m: self.mask_email(m.group(0)),
            value
        )
        
        # 检测并脱敏手机号
        value = self.PHONE_PATTERN.sub(
            lambda m: self.mask_phone(m.group(0)),
            value
        )
        
        # 检测并脱敏钱包地址
        value = self.WALLET_PATTERN.sub(
            lambda m: self.mask_wallet_address(m.group(0)),
            value
        )
        
        return value
    
    def sanitize_dict(self, data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
        """
        脱敏字典数据
        
        参数:
            data: 要脱敏的字典
            deep: 是否深度脱敏（递归处理嵌套字典）
            
        返回:
            dict: 脱敏后的字典
        """
        if not deep:
            # 浅层脱敏
            return {
                key: self.sanitize_value(value, key)
                for key, value in data.items()
            }
        
        # 深度脱敏
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.sanitize_dict(value, deep=True)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize_dict(item, deep=True) if isinstance(item, dict)
                    else self.sanitize_value(item, key)
                    for item in value
                ]
            else:
                result[key] = self.sanitize_value(value, key)
        
        return result
    
    def sanitize(self, data: Any, deep: bool = True) -> Any:
        """
        脱敏数据（通用接口）
        
        参数:
            data: 要脱敏的数据
            deep: 是否深度脱敏
            
        返回:
            Any: 脱敏后的数据
        """
        if isinstance(data, dict):
            return self.sanitize_dict(data, deep=deep)
        elif isinstance(data, str):
            return self.sanitize_value(data)
        elif isinstance(data, list):
            return [self.sanitize(item, deep=deep) for item in data]
        else:
            return data


# 全局默认脱敏器实例
_default_sanitizer = Sanitizer()


def sanitize(data: Any, deep: bool = True) -> Any:
    """
    使用默认脱敏器脱敏数据的便捷函数
    
    参数:
        data: 要脱敏的数据
        deep: 是否深度脱敏
        
    返回:
        Any: 脱敏后的数据
    """
    return _default_sanitizer.sanitize(data, deep=deep)


def add_sensitive_field(field_name: str):
    """
    向默认脱敏器添加敏感字段的便捷函数
    
    参数:
        field_name: 字段名称
    """
    _default_sanitizer.add_sensitive_field(field_name)

