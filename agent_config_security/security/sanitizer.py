"""
日志脱敏模块

功能：
- 自动检测敏感信息
- 多种脱敏策略
- 结构化数据脱敏
- 异常堆栈清理
"""

import re
import os
import hashlib
import logging
from typing import Any, Optional, Pattern
from enum import Enum

logger = logging.getLogger(__name__)


class MaskStrategy(str, Enum):
    """脱敏策略"""
    FULL = "full"  # 完全替换: ***
    PARTIAL = "partial"  # 部分显示: sk-***1234
    HASH = "hash"  # 哈希: a1b2c3d4
    TRUNCATE = "truncate"  # 截断: sk-1234...


class LogSanitizer:
    """
    日志脱敏器

    特性：
    - 自动检测敏感模式
    - 多种脱敏策略
    - 递归处理嵌套结构
    - 异常堆栈清理
    """

    # 敏感信息模式 (正则表达式)
    DEFAULT_PATTERNS = {
        "api_key": re.compile(
            r"(sk-[a-zA-Z0-9]{32,}|"
            r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{20,}['\"]?|"
            r"apikey['\"]?\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{20,}['\"]?)",
            re.IGNORECASE,
        ),
        "bearer_token": re.compile(
            r"(bearer\s+[a-zA-Z0-9_-]{20,}|"
            r"authorization['\"]?\s*[:=]\s*['\"]?(bearer\s+)?[a-zA-Z0-9_-]{20,}['\"]?)",
            re.IGNORECASE,
        ),
        "jwt": re.compile(
            r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
        ),
        "password": re.compile(
            r"(password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{4,}['\"]?|"
            r"passwd['\"]?\s*[:=]\s*['\"]?[^\s'\"]{4,}['\"]?)",
            re.IGNORECASE,
        ),
        "secret": re.compile(
            r"(secret['\"]?\s*[:=]\s*['\"]?[^\s'\"]{10,}['\"]?|"
            r"private[_-]?key['\"]?\s*[:=]\s*['\"]?[^\s'\"]{20,}['\"]?)",
            re.IGNORECASE,
        ),
        "connection_string": re.compile(
            r"(mongodb://|postgresql://|mysql://|redis://)[^\s'\"]+:[^\s'\"]+@[^\s'\"]+",
            re.IGNORECASE,
        ),
        "ip_address": re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        ),
        "email": re.compile(
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        ),
        "credit_card": re.compile(
            r"\b(?:\d[ -]*?){13,16}\b",
        ),
        "aws_key": re.compile(
            r"(AKIA[0-9A-Z]{16}|aws_access_key_id['\"]?\s*[:=]\s*['\"]?[A-Z0-9]{20}['\"]?)",
        ),
        "github_token": re.compile(
            r"ghp_[a-zA-Z0-9]{36,}|gho_[a-zA-Z0-9]{36,}|ghu_[a-zA-Z0-9]{36,}",
        ),
        "slack_token": re.compile(
            r"xox[baprs]-[a-zA-Z0-9-]{10,}",
        ),
    }

    # 敏感字段名
    SENSITIVE_FIELDS = {
        "password", "passwd", "secret", "token", "key", "credential",
        "api_key", "apikey", "private_key", "auth", "bearer",
        "access_token", "refresh_token", "session_id", "csrf_token",
        "cookie", "set_cookie", "authorization", "x-api-key",
        "x-auth-token", "x-secret", "client_secret", "client_id",
    }

    def __init__(
        self,
        strategy: MaskStrategy = MaskStrategy.PARTIAL,
        custom_patterns: Optional[dict[str, Pattern]] = None,
        sensitive_fields: Optional[set[str]] = None,
        hash_salt: Optional[str] = None,
    ):
        """
        Args:
            strategy: 默认脱敏策略
            custom_patterns: 自定义敏感模式
            sensitive_fields: 敏感字段名集合
            hash_salt: 哈希策略的盐值
        """
        self._strategy = strategy
        self._patterns = {**self.DEFAULT_PATTERNS, **(custom_patterns or {})}
        self._sensitive_fields = sensitive_fields or self.SENSITIVE_FIELDS
        self._hash_salt = hash_salt or os.getenv("SANITIZER_SALT", "default")

    def sanitize(self, data: Any) -> Any:
        """
        脱敏任意数据

        Args:
            data: 输入数据

        Returns:
            脱敏后的数据
        """
        if isinstance(data, str):
            return self._sanitize_string(data)
        elif isinstance(data, dict):
            return self._sanitize_dict(data)
        elif isinstance(data, (list, tuple)):
            return type(data)(self.sanitize(item) for item in data)
        else:
            return data

    def sanitize_string(self, text: str) -> str:
        """脱敏字符串"""
        return self._sanitize_string(text)

    def sanitize_dict(self, data: dict) -> dict:
        """脱敏字典"""
        return self._sanitize_dict(data.copy())

    def sanitize_exception(self, exc: Exception) -> str:
        """脱敏异常信息"""
        # 获取异常字符串
        exc_str = str(exc)

        # 获取堆栈跟踪
        import traceback
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        # 脱敏
        sanitized_tb = self._sanitize_string(tb_str)

        return sanitized_tb

    def _sanitize_string(self, text: str) -> str:
        """脱敏字符串"""
        result = text

        # 应用所有模式
        for pattern_name, pattern in self._patterns.items():
            result = pattern.sub(
                lambda m: self._mask_match(m, pattern_name),
                result
            )

        return result

    def _sanitize_dict(self, data: dict) -> dict:
        """递归脱敏字典"""
        result = {}

        for key, value in data.items():
            # 检查键名是否敏感
            is_sensitive = any(
                s in key.lower() for s in self._sensitive_fields
            )

            if is_sensitive:
                # 敏感字段，完全脱敏
                result[key] = self._apply_strategy(value, self._strategy)
            elif isinstance(value, dict):
                result[key] = self._sanitize_dict(value)
            elif isinstance(value, (list, tuple)):
                result[key] = type(data)(
                    self.sanitize(item) for item in value
                )
            elif isinstance(value, str):
                result[key] = self._sanitize_string(value)
            else:
                result[key] = value

        return result

    def _mask_match(self, match: re.Match, pattern_name: str) -> str:
        """对匹配结果应用脱敏"""
        matched = match.group(0)

        # 根据模式类型选择策略
        if pattern_name == "api_key":
            return self._apply_strategy(matched, MaskStrategy.PARTIAL, show_last=4)
        elif pattern_name == "jwt":
            return self._apply_strategy(matched, MaskStrategy.PARTIAL, show_last=16)
        elif pattern_name in ("password", "secret"):
            return self._apply_strategy(matched, MaskStrategy.FULL)
        elif pattern_name == "connection_string":
            # 只保留协议和主机
            parts = matched.split("@")
            if len(parts) == 2:
                protocol_user, host = parts
                protocol = protocol_user.split("://")[0] + "://"
                return f"{protocol}***:***@{host}"
            return self._apply_strategy(matched, MaskStrategy.PARTIAL, show_last=8)
        elif pattern_name == "ip_address":
            return self._apply_strategy(matched, MaskStrategy.PARTIAL, show_last=2)
        elif pattern_name == "email":
            local, domain = matched.rsplit("@", 1)
            return f"{local[0]}***@{domain}"
        else:
            return self._apply_strategy(matched, self._strategy)

    def _apply_strategy(
        self,
        value: Any,
        strategy: MaskStrategy,
        show_last: int = 4,
    ) -> str:
        """应用脱敏策略"""
        value_str = str(value)

        if strategy == MaskStrategy.FULL:
            return "***"

        elif strategy == MaskStrategy.PARTIAL:
            if len(value_str) <= show_last:
                return "***"
            # 显示前几个字符 + *** + 后几个字符
            prefix_len = min(3, len(value_str) - show_last)
            return f"{value_str[:prefix_len]}***{value_str[-show_last:]}" if prefix_len > 0 else f"***{value_str[-show_last:]}"

        elif strategy == MaskStrategy.HASH:
            hash_input = f"{self._hash_salt}:{value_str}"
            return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        elif strategy == MaskStrategy.TRUNCATE:
            if len(value_str) <= show_last + 3:
                return "***"
            return f"{value_str[:show_last]}..."

        return "***"

    def add_pattern(self, name: str, pattern: str | Pattern) -> None:
        """添加自定义模式"""
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        self._patterns[name] = pattern

    def add_sensitive_field(self, field: str) -> None:
        """添加敏感字段名"""
        self._sensitive_fields.add(field.lower())


# 全局默认实例
_default_sanitizer = LogSanitizer()


def sanitize(data: Any) -> Any:
    """便捷函数：使用默认实例脱敏"""
    return _default_sanitizer.sanitize(data)


def sanitize_dict(data: dict) -> dict:
    """便捷函数：脱敏字典"""
    return _default_sanitizer.sanitize_dict(data)


def sanitize_string(text: str) -> str:
    """便捷函数：脱敏字符串"""
    return _default_sanitizer.sanitize_string(text)


# 日志记录器过滤器


class SanitizingFilter(logging.Filter):
    """日志过滤器：自动脱敏日志记录"""

    def __init__(self, sanitizer: Optional[LogSanitizer] = None):
        super().__init__()
        self._sanitizer = sanitizer or _default_sanitizer

    def filter(self, record: logging.LogRecord) -> bool:
        # 脱敏消息
        if isinstance(record.msg, str):
            record.msg = self._sanitizer.sanitize_string(record.msg)

        # 脱敏参数
        if record.args:
            record.args = tuple(
                self._sanitizer.sanitize(arg) for arg in record.args
            )

        # 脱敏额外字段
        for key in list(record.__dict__.keys()):
            if key not in {"name", "msg", "args", "levelname", "levelno",
                           "pathname", "filename", "module", "exc_info",
                           "exc_text", "stack_info", "lineno", "funcName",
                           "created", "msecs", "relativeCreated", "thread",
                           "threadName", "processName", "process"}:
                value = getattr(record, key, None)
                if isinstance(value, (str, dict, list)):
                    setattr(record, key, self._sanitizer.sanitize(value))

        return True


def setup_logging_with_sanitization(
    level: int = logging.INFO,
    sanitizer: Optional[LogSanitizer] = None,
) -> None:
    """
    设置带脱敏的日志系统

    用法:
        setup_logging_with_sanitization()
        logger = logging.getLogger(__name__)
        logger.info({"api_key": "sk-1234567890abcdef"})  # 自动脱敏
    """
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # 添加脱敏过滤器
    handler.addFilter(SanitizingFilter(sanitizer))

    root.addHandler(handler)
