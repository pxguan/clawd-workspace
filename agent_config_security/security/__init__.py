"""
安全模块

提供审计、脱敏、内存保护、凭证管理功能
"""

from .audit import AuditLogger, AuditEvent, AuditEventType
from .sanitizer import LogSanitizer, sanitize_dict, sanitize_string
from .memory import MemoryGuard, secure_zero, protect_string
from .credential import CredentialManager as SecurityCredentialManager

__all__ = [
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "LogSanitizer",
    "sanitize_dict",
    "sanitize_string",
    "MemoryGuard",
    "secure_zero",
    "protect_string",
    "SecurityCredentialManager",
]
