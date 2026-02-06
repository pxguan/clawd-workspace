"""
凭证安全管理模块

功能：
- 凭证生命周期管理
- 轮换策略
- 泄露检测
- 自动撤销
"""

import os
import time
import hashlib
import logging
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class CredentialStatus(str, Enum):
    """凭证状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    COMPROMISED = "compromised"
    PENDING_ROTATION = "pending_rotation"


@dataclass
class CredentialLeak:
    """凭证泄露事件"""
    credential_id: str
    detected_at: datetime
    leak_source: str  # "log", "git", "environment", "memory_dump"
    evidence: str
    severity: str = "high"  # "critical", "high", "medium", "low"


@dataclass
class CredentialRecord:
    """凭证记录"""
    id: str
    name: str
    value_hash: str  # 只存储哈希，不存储明文
    status: CredentialStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_rotated: Optional[datetime]
    rotation_interval: Optional[timedelta]
    metadata: Dict[str, any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def needs_rotation(self) -> bool:
        if self.rotation_interval is None or self.last_rotated is None:
            return False
        return datetime.utcnow() > self.last_rotated + self.rotation_interval


class SecurityCredentialManager:
    """
    凭证安全管理器

    特性：
    - 凭证生命周期管理
    - 自动轮换
    - 泄露检测
    - 紧急撤销
    """

    def __init__(
        self,
        rotation_check_interval: int = 3600,  # 1 hour
        leak_detection_enabled: bool = True,
        audit_logger: Optional["AuditLogger"] = None,
    ):
        """
        Args:
            rotation_check_interval: 轮换检查间隔 (秒)
            leak_detection_enabled: 是否启用泄露检测
            audit_logger: 审计日志记录器
        """
        self._records: Dict[str, CredentialRecord] = {}
        self._leaks: List[CredentialLeak] = []
        self._rotation_check_interval = rotation_check_interval
        self._leak_detection_enabled = leak_detection_enabled
        self._audit = audit_logger

        # 泄露检测回调
        self._leak_callbacks: List[Callable[[CredentialLeak], None]] = []

        # 访问历史 (用于异常检测)
        self._access_history: Dict[str, deque] = {}

    def register_credential(
        self,
        name: str,
        value: str,
        expires_in: Optional[int] = None,
        rotation_interval_days: Optional[int] = None,
        metadata: Optional[Dict[str, any]] = None,
    ) -> str:
        """
        注册凭证

        Args:
            name: 凭证名称
            value: 凭证值 (只存储哈希)
            expires_in: 过期时间 (秒)
            rotation_interval_days: 轮换间隔 (天)
            metadata: 元数据

        Returns:
            str: 凭证 ID
        """
        cred_id = self._generate_id(name, value)

        # 只存储哈希值
        value_hash = self._hash_value(value)

        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        rotation_interval = None
        if rotation_interval_days:
            rotation_interval = timedelta(days=rotation_interval_days)

        record = CredentialRecord(
            id=cred_id,
            name=name,
            value_hash=value_hash,
            status=CredentialStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_rotated=datetime.utcnow(),
            rotation_interval=rotation_interval,
            metadata=metadata or {},
        )

        self._records[cred_id] = record
        self._access_history[cred_id] = deque(maxlen=1000)

        if self._audit:
            self._audit.log(
                event_type=AuditEventType.CREDENTIAL_CREATED,
                resource=name,
                details={"id": cred_id},
            )

        logger.info(f"Registered credential: {name} (id={cred_id})")
        return cred_id

    def verify_credential(self, cred_id: str, value: str) -> bool:
        """
        验证凭证值

        Args:
            cred_id: 凭证 ID
            value: 要验证的值

        Returns:
            bool: 是否有效
        """
        record = self._records.get(cred_id)
        if not record:
            return False

        if record.status != CredentialStatus.ACTIVE:
            return False

        if record.is_expired:
            record.status = CredentialStatus.EXPIRED
            return False

        # 验证哈希
        value_hash = self._hash_value(value)
        valid = value_hash == record.value_hash

        # 记录访问
        self._record_access(cred_id, valid)

        return valid

    def revoke_credential(
        self,
        cred_id: str,
        reason: str = "manual",
    ) -> bool:
        """
        撤销凭证

        Args:
            cred_id: 凭证 ID
            reason: 撤销原因

        Returns:
            bool: 是否成功
        """
        record = self._records.get(cred_id)
        if not record:
            return False

        record.status = CredentialStatus.REVOKED

        if self._audit:
            self._audit.log(
                event_type=AuditEventType.CREDENTIAL_REVOKED,
                resource=record.name,
                details={"id": cred_id, "reason": reason},
            )

        logger.warning(f"Revoked credential: {record.name} (reason={reason})")
        return True

    def report_leak(
        self,
        cred_id: str,
        leak_source: str,
        evidence: str,
        severity: str = "high",
    ) -> None:
        """
        报告凭证泄露

        Args:
            cred_id: 凭证 ID
            leak_source: 泄露来源
            evidence: 证据
            severity: 严重程度
        """
        record = self._records.get(cred_id)
        if not record:
            logger.error(f"Cannot report leak for unknown credential: {cred_id}")
            return

        # 创建泄露记录
        leak = CredentialLeak(
            credential_id=cred_id,
            detected_at=datetime.utcnow(),
            leak_source=leak_source,
            evidence=evidence,
            severity=severity,
        )

        self._leaks.append(leak)

        # 标记为已泄露
        record.status = CredentialStatus.COMPROMISED

        # 自动撤销
        self.revoke_credential(cred_id, reason=f"leak detected: {leak_source}")

        # 触发回调
        for callback in self._leak_callbacks:
            try:
                callback(leak)
            except Exception as e:
                logger.error(f"Leak callback error: {e}")

        if self._audit:
            self._audit.log_security_violation(
                violation_type="credential_leak",
                details={
                    "credential_id": cred_id,
                    "leak_source": leak_source,
                    "severity": severity,
                },
            )

        logger.critical(f"Credential leak detected: {record.name} from {leak_source}")

    def rotate_credential(
        self,
        cred_id: str,
        new_value: str,
    ) -> bool:
        """
        轮换凭证

        Args:
            cred_id: 凭证 ID
            new_value: 新值

        Returns:
            bool: 是否成功
        """
        record = self._records.get(cred_id)
        if not record:
            return False

        # 更新哈希
        record.value_hash = self._hash_value(new_value)
        record.last_rotated = datetime.utcnow()

        # 如果之前已过期或被撤销，重新激活
        if record.status in (CredentialStatus.EXPIRED, CredentialStatus.REVOKED):
            record.status = CredentialStatus.ACTIVE

        if self._audit:
            self._audit.log(
                event_type=AuditEventType.CREDENTIAL_CREATED,  # 复用事件类型
                resource=record.name,
                action="rotate",
                details={"id": cred_id},
            )

        logger.info(f"Rotated credential: {record.name}")
        return True

    def check_rotation_needed(self) -> List[str]:
        """
        检查需要轮换的凭证

        Returns:
            List[str]: 需要轮换的凭证 ID 列表
        """
        needs_rotation = []

        for cred_id, record in self._records.items():
            if record.status == CredentialStatus.ACTIVE and record.needs_rotation:
                needs_rotation.append(cred_id)
                record.status = CredentialStatus.PENDING_ROTATION

        return needs_rotation

    def scan_for_leaks(
        self,
        log_file: Optional[str] = None,
        git_history: bool = False,
        environment: bool = True,
    ) -> List[CredentialLeak]:
        """
        扫描潜在泄露

        Args:
            log_file: 日志文件路径
            git_history: 是否扫描 git 历史
            environment: 是否扫描环境变量

        Returns:
            List[CredentialLeak]: 发现的泄露
        """
        if not self._leak_detection_enabled:
            return []

        leaks = []

        # 扫描环境变量
        if environment:
            for key, value in os.environ.items():
                for cred_id, record in self._records.items():
                    # 检查是否包含凭证值的部分哈希
                    # (这里简化处理，实际应该检查完整值)
                    if any(
                        s in key.lower()
                        for s in ["key", "secret", "token", "password"]
                    ):
                        # 发现可疑的环境变量
                        if record.name.lower() in key.lower():
                            leaks.append(CredentialLeak(
                                credential_id=cred_id,
                                detected_at=datetime.utcnow(),
                                leak_source="environment",
                                evidence=f"Found in environment variable: {key}",
                            ))

        # 扫描日志文件
        if log_file:
            try:
                from pathlib import Path
                content = Path(log_file).read_text()

                for cred_id, record in self._records.items():
                    # 检查日志中是否包含凭证名称的模式
                    if record.name.lower() in content.lower():
                        # 进一步检查是否有可疑模式
                        import re
                        # 检查是否有 "= 后跟长字符串" 的模式
                        pattern = rf'{record.name}\s*=\s*["\']?([a-zA-Z0-9_-]{{20,}})'
                        if re.search(pattern, content, re.IGNORECASE):
                            leaks.append(CredentialLeak(
                                credential_id=cred_id,
                                detected_at=datetime.utcnow(),
                                leak_source="log",
                                evidence=f"Found pattern in log file: {log_file}",
                            ))
            except Exception as e:
                logger.error(f"Failed to scan log file: {e}")

        # 报告发现的泄露
        for leak in leaks:
            self.report_leak(
                leak.credential_id,
                leak.leak_source,
                leak.evidence,
                leak.severity,
            )

        return leaks

    def add_leak_callback(self, callback: Callable[[CredentialLeak], None]) -> None:
        """添加泄露回调"""
        self._leak_callbacks.append(callback)

    def get_status(self, cred_id: str) -> Optional[CredentialRecord]:
        """获取凭证状态"""
        return self._records.get(cred_id)

    def list_credentials(self) -> List[CredentialRecord]:
        """列出所有凭证"""
        return list(self._records.values())

    def cleanup_expired(self) -> int:
        """清理过期凭证"""
        count = 0
        for cred_id, record in list(self._records.items()):
            if record.is_expired:
                del self._records[cred_id]
                count += 1
        return count

    def _generate_id(self, name: str, value: str) -> str:
        """生成唯一 ID"""
        unique = f"{name}:{value}:{time.time()}:{os.urandom(8).hex()}"
        return hashlib.sha256(unique.encode()).hexdigest()[:16]

    def _hash_value(self, value: str) -> str:
        """计算凭证值的哈希"""
        return hashlib.sha256(value.encode()).hexdigest()

    def _record_access(self, cred_id: str, success: bool) -> None:
        """记录访问用于异常检测"""
        if cred_id not in self._access_history:
            return

        self._access_history[cred_id].append({
            "time": datetime.utcnow(),
            "success": success,
        })

        # 检测异常模式
        if len(self._access_history[cred_id]) > 10:
            recent = list(self._access_history[cred_id])[-10:]
            failures = sum(1 for a in recent if not a["success"])

            # 如果最近 10 次访问失败超过 5 次
            if failures > 5:
                logger.warning(
                    f"Unusual access pattern detected for credential {cred_id}: "
                    f"{failures}/10 recent attempts failed"
                )

                # 可选：自动锁定
                # self.revoke_credential(cred_id, reason="too many failures")


# 导入 AuditEventType (延迟导入避免循环依赖)


from .audit import AuditEventType
