"""
审计日志模块

功能：
- 结构化审计日志
- 签名验证
- 可追溯性
- 防篡改
"""

import os
import json
import hmac
import hashlib
import logging
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """审计事件类型"""
    CONFIG_ACCESS = "config_access"
    SECRET_READ = "secret_read"
    CREDENTIAL_CREATED = "credential_created"
    CREDENTIAL_USED = "credential_used"
    CREDENTIAL_REVOKED = "credential_revoked"
    CREDENTIAL_CLEANED = "credential_cleaned"
    CRYPTO_OPERATION = "crypto_operation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SECURITY_VIOLATION = "security_violation"


@dataclass
class AuditEvent:
    """审计事件"""
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor: Optional[str] = None  # 谁执行的操作
    resource: Optional[str] = None  # 操作的资源
    action: Optional[str] = None  # 执行的动作
    result: str = "success"  # success, failure, denied
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    signature: Optional[str] = None  # 防篡改签名

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def sign(self, key: bytes) -> "AuditEvent":
        """签名事件"""
        message = self._signing_payload()
        signature = hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
        self.signature = signature
        return self

    def verify(self, key: bytes) -> bool:
        """验证签名"""
        if not self.signature:
            return False
        message = self._signing_payload()
        expected = hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)

    def _signing_payload(self) -> str:
        """生成签名载荷 (不包含 signature 字段)"""
        data = self.to_dict()
        data.pop("signature", None)
        # 按键排序确保一致性
        return json.dumps(data, sort_keys=True)


class AuditLogger:
    """
    审计日志记录器

    特性：
- 结构化 JSON 日志
- HMAC 签名防篡改
- 文件轮转支持
- 异步写入优化
- 敏感信息过滤
    """

    def __init__(
        self,
        log_file: Optional[str | Path] = None,
        signing_key: Optional[bytes] = None,
        filter_sensitive: bool = True,
        buffer_size: int = 100,
        auto_flush: bool = True,
    ):
        """
        Args:
            log_file: 日志文件路径
            signing_key: HMAC 签名密钥
            filter_sensitive: 是否过滤敏感信息
            buffer_size: 缓冲区大小
            auto_flush: 是否自动刷新
        """
        self.log_file = Path(log_file) if log_file else None
        self._signing_key = signing_key
        self._filter = filter_sensitive
        self._buffer: list[AuditEvent] = []
        self._buffer_size = buffer_size
        self._auto_flush = auto_flush

        # 敏感字段模式
        self._sensitive_fields = {
            "password", "secret", "token", "key", "credential",
            "api_key", "private_key", "auth", "value", "payload",
        }

        # 确保目录存在
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: AuditEventType,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[dict[str, Any]] = None,
        actor: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        记录审计事件

        Args:
            event_type: 事件类型
            resource: 操作的资源
            action: 执行的动作
            result: 操作结果
            details: 详细信息
            actor: 执行者
            **kwargs: 其他字段
        """
        event = AuditEvent(
            event_type=event_type,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            actor=actor or self._get_actor(),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
            session_id=kwargs.get("session_id"),
        )

        self._add_event(event)

    def log_config_access(
        self,
        key: str,
        source: str,
        is_secret: bool,
        from_cache: bool,
    ) -> None:
        """记录配置访问"""
        self.log(
            event_type=AuditEventType.SECRET_READ if is_secret else AuditEventType.CONFIG_ACCESS,
            resource=key,
            action="read",
            details={
                "source": source,
                "from_cache": from_cache,
                "is_secret": is_secret,
            },
        )

    def log_credential_created(self, credential) -> None:
        """记录凭证创建"""
        self.log(
            event_type=AuditEventType.CREDENTIAL_CREATED,
            resource=credential.name,
            action="create",
            details={
                "id": credential.id,
                "scope": credential.scope,
                "ttl_seconds": (
                    int((credential.expires_at - credential.created_at).total_seconds())
                    if credential.expires_at else None
                ),
                "max_uses": credential.max_uses,
            },
        )

    def log_credential_used(self, credential, env_key: str) -> None:
        """记录凭证使用"""
        self.log(
            event_type=AuditEventType.CREDENTIAL_USED,
            resource=credential.name,
            action="use",
            details={
                "env_key": env_key,
                "use_count": credential.use_count,
                "remaining": credential.max_uses - credential.use_count,
            },
        )

    def log_credential_revoked(self, credential) -> None:
        """记录凭证撤销"""
        self.log(
            event_type=AuditEventType.CREDENTIAL_REVOKED,
            resource=credential.name,
            action="revoke",
            details={"id": credential.id},
        )

    def log_credential_cleaned(self, credential, env_key: str) -> None:
        """记录凭证清理"""
        self.log(
            event_type=AuditEventType.CREDENTIAL_CLEANED,
            resource=credential.name,
            action="cleanup",
            details={"env_key": env_key},
        )

    def log_security_violation(
        self,
        violation_type: str,
        details: dict[str, Any],
    ) -> None:
        """记录安全违规"""
        self.log(
            event_type=AuditEventType.SECURITY_VIOLATION,
            action="violation",
            result="denied",
            details={"type": violation_type, **details},
        )

    def _add_event(self, event: AuditEvent) -> None:
        """添加事件到缓冲区"""
        # 过滤敏感信息
        if self._filter:
            event.details = self._filter_sensitive(event.details)

        # 签名
        if self._signing_key:
            event.sign(self._signing_key)

        self._buffer.append(event)

        # 自动刷新
        if self._auto_flush and len(self._buffer) >= self._buffer_size:
            self.flush()

    def flush(self) -> None:
        """刷新缓冲区到存储"""
        if not self._buffer:
            return

        if self.log_file:
            with open(self.log_file, "a") as f:
                for event in self._buffer:
                    f.write(event.to_json() + "\n")

        self._buffer.clear()

    def query(
        self,
        event_type: Optional[AuditEventType] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """
        查询审计日志

        Args:
            event_type: 事件类型过滤
            resource: 资源过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量

        Returns:
            list[AuditEvent]: 匹配的事件列表
        """
        if not self.log_file or not self.log_file.exists():
            return []

        results = []

        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    event = AuditEvent(
                        event_type=AuditEventType(data["event_type"]),
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        actor=data.get("actor"),
                        resource=data.get("resource"),
                        action=data.get("action"),
                        result=data.get("result", "success"),
                        details=data.get("details", {}),
                        ip_address=data.get("ip_address"),
                        user_agent=data.get("user_agent"),
                        session_id=data.get("session_id"),
                        signature=data.get("signature"),
                    )

                    # 验证签名
                    if self._signing_key and not event.verify(self._signing_key):
                        logger.warning(f"Invalid signature for event at {event.timestamp}")
                        continue

                    # 过滤
                    if event_type and event.event_type != event_type:
                        continue
                    if resource and event.resource != resource:
                        continue
                    if start_time and event.timestamp < start_time:
                        continue
                    if end_time and event.timestamp > end_time:
                        continue

                    results.append(event)
                    if len(results) >= limit:
                        break

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.debug(f"Failed to parse audit log line: {e}")
                    continue

        return results

    def _filter_sensitive(self, data: dict[str, Any]) -> dict[str, Any]:
        """过滤敏感字段"""
        filtered = {}
        for key, value in data.items():
            if any(s in key.lower() for s in self._sensitive_fields):
                filtered[key] = "***REDACTED***"
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive(value)
            else:
                filtered[key] = value
        return filtered

    def _get_actor(self) -> str:
        """获取当前操作者"""
        # 尝试获取进程用户
        try:
            import getpass
            return getpass.getuser()
        except Exception:
            return "system"


def create_audit_logger(log_file: str, signing_key: Optional[bytes] = None) -> AuditLogger:
    """创建审计日志记录器"""
    # 如果没有提供签名密钥，从环境变量获取或生成
    if signing_key is None:
        key_hex = os.getenv("AUDIT_SIGNING_KEY")
        if key_hex:
            signing_key = bytes.fromhex(key_hex)
        else:
            # 生成并保存密钥
            signing_key = os.urandom(32)
            logger.warning("Generated new audit signing key. Set AUDIT_SIGNING_KEY to persist.")

    return AuditLogger(log_file=log_file, signing_key=signing_key)
