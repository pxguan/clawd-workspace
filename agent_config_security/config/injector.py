"""
沙箱配置注入模块

功能：
- 安全的环境变量注入
- 临时凭证生成和注入
- 作用域限制
- 自动清理
"""

import os
import uuid
import time
import hashlib
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from enum import Enum

from .crypto import CryptoManager, generate_password
from .vault import VaultBackend

logger = logging.getLogger(__name__)


class InjectionScope(str, Enum):
    """注入作用域"""
    PROCESS = "process"  # 当前进程环境变量
    THREAD = "thread"  # 线程本地存储
    REQUEST = "request"  # 请求级别


@dataclass
class TemporaryCredential:
    """临时凭证"""
    id: str
    name: str
    value: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    max_uses: int = 1
    use_count: int = 0
    scope: InjectionScope = InjectionScope.PROCESS
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_depleted(self) -> bool:
        return self.use_count >= self.max_uses

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_depleted

    def mark_used(self) -> None:
        self.use_count += 1


@dataclass
class InjectionResult:
    """注入结果"""
    success: bool
    credential_id: str
    injected_value: Optional[str] = None
    environment_key: Optional[str] = None
    error: Optional[str] = None


class SandboxInjector:
    """
    沙箱配置注入器

    特性：
    - 临时凭证生成
    - 安全的环境变量注入
    - 作用域限制
    - 自动过期清理
    - 使用次数限制
    """

    def __init__(
        self,
        prefix: str = "AGENT_TEMP_",
        default_ttl_seconds: int = 300,
        default_max_uses: int = 1,
        audit_logger: Optional["AuditLogger"] = None,
    ):
        """
        Args:
            prefix: 临时环境变量前缀
            default_ttl_seconds: 默认凭证有效期
            default_max_uses: 默认最大使用次数
            audit_logger: 审计日志记录器
        """
        self.prefix = prefix.upper()
        self._default_ttl = default_ttl_seconds
        self._default_max_uses = default_max_uses
        self._audit = audit_logger

        # 凭证存储
        self._credentials: Dict[str, TemporaryCredential] = {}

        # 线程本地存储
        self._thread_local: Dict[int, Dict[str, str]] = {}

        # 环境变量追踪 (用于清理)
        self._injected_env_keys: Dict[str, str] = {}

    def create_credential(
        self,
        name: str,
        value: str,
        ttl_seconds: Optional[int] = None,
        max_uses: Optional[int] = None,
        scope: InjectionScope = InjectionScope.PROCESS,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TemporaryCredential:
        """
        创建临时凭证

        Args:
            name: 凭证名称
            value: 凭证值
            ttl_seconds: 有效期 (秒)
            max_uses: 最大使用次数
            scope: 作用域
            metadata: 元数据

        Returns:
            TemporaryCredential: 创建的凭证
        """
        cred_id = self._generate_id(name, value)

        expires_at = None
        if ttl_seconds or self._default_ttl:
            ttl = ttl_seconds or self._default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        credential = TemporaryCredential(
            id=cred_id,
            name=name,
            value=value,
            expires_at=expires_at,
            max_uses=max_uses or self._default_max_uses,
            scope=scope,
            metadata=metadata or {},
        )

        self._credentials[cred_id] = credential

        if self._audit:
            self._audit.log_credential_created(credential)

        logger.debug(f"Created temporary credential: {name} (id={cred_id})")
        return credential

    def inject(
        self,
        credential_id: str,
        env_key: Optional[str] = None,
    ) -> InjectionResult:
        """
        注入凭证到环境

        Args:
            credential_id: 凭证 ID
            env_key: 环境变量键名 (默认: PREFIX_NAME)

        Returns:
            InjectionResult: 注入结果
        """
        credential = self._credentials.get(credential_id)

        if not credential:
            return InjectionResult(
                success=False,
                credential_id=credential_id,
                error="Credential not found",
            )

        if not credential.is_valid:
            reason = "expired" if credential.is_expired else "depleted"
            return InjectionResult(
                success=False,
                credential_id=credential_id,
                error=f"Credential {reason}",
            )

        # 生成环境变量键名
        if not env_key:
            env_key = f"{self.prefix}{credential.name.upper()}"

        try:
            if credential.scope == InjectionScope.PROCESS:
                # 注入到进程环境变量
                os.environ[env_key] = credential.value
                self._injected_env_keys[env_key] = credential_id

            elif credential.scope == InjectionScope.THREAD:
                # 注入到线程本地存储
                thread_id = id(__import__("threading").current_thread())
                if thread_id not in self._thread_local:
                    self._thread_local[thread_id] = {}
                self._thread_local[thread_id][env_key] = credential.value

            elif credential.scope == InjectionScope.REQUEST:
                # 请求级别，返回值供调用者管理
                pass

            credential.mark_used()

            if self._audit:
                self._audit.log_credential_used(credential, env_key)

            logger.debug(f"Injected credential {credential.name} as {env_key}")

            return InjectionResult(
                success=True,
                credential_id=credential_id,
                injected_value=credential.value,
                environment_key=env_key,
            )

        except Exception as e:
            logger.error(f"Failed to inject credential: {e}")
            return InjectionResult(
                success=False,
                credential_id=credential_id,
                error=str(e),
            )

    @contextmanager
    def inject_context(
        self,
        name: str,
        value: str,
        ttl_seconds: Optional[int] = None,
        env_key: Optional[str] = None,
    ):
        """
        上下文管理器：自动注入和清理

        用法:
            with injector.inject_context("API_KEY", "secret"):
                # API_KEY 已注入到环境
                call_api()
            # 自动清理
        """
        credential = self.create_credential(
            name=name,
            value=value,
            ttl_seconds=ttl_seconds,
        )

        result = self.inject(credential.id, env_key)

        if not result.success:
            raise RuntimeError(f"Failed to inject credential: {result.error}")

        injected_key = result.environment_key

        try:
            yield credential
        finally:
            self.cleanup(injected_key)

    def cleanup(self, env_key: str) -> bool:
        """清理注入的环境变量"""
        # 从进程环境变量清理
        if env_key in os.environ:
            del os.environ[env_key]

        # 从追踪记录清理
        if env_key in self._injected_env_keys:
            cred_id = self._injected_env_keys[env_key]
            del self._injected_env_keys[env_key]

            # 检查凭证是否还有其他注入
            if not any(k == env_key for k in self._injected_env_keys.values()):
                credential = self._credentials.get(cred_id)
                if credential and self._audit:
                    self._audit.log_credential_cleaned(credential, env_key)

        return True

    def cleanup_all(self) -> int:
        """清理所有注入的凭证"""
        count = 0
        for env_key in list(self._injected_env_keys.keys()):
            if self.cleanup(env_key):
                count += 1
        return count

    def revoke(self, credential_id: str) -> bool:
        """撤销凭证"""
        if credential_id in self._credentials:
            credential = self._credentials[credential_id]

            # 清理所有相关的环境变量
            keys_to_clean = [
                k for k, v in self._injected_env_keys.items()
                if v == credential_id
            ]
            for key in keys_to_clean:
                self.cleanup(key)

            del self._credentials[credential_id]

            if self._audit:
                self._audit.log_credential_revoked(credential)

            logger.info(f"Revoked credential: {credential.name}")
            return True
        return False

    def get_credential(self, credential_id: str) -> Optional[TemporaryCredential]:
        """获取凭证 (不返回值，仅元数据)"""
        cred = self._credentials.get(credential_id)
        if cred:
            # 返回副本，隐藏实际值
            return TemporaryCredential(
                id=cred.id,
                name=cred.name,
                value="***HIDDEN***",
                created_at=cred.created_at,
                expires_at=cred.expires_at,
                max_uses=cred.max_uses,
                use_count=cred.use_count,
                scope=cred.scope,
                metadata=cred.metadata,
            )
        return None

    def list_credentials(self) -> list[TemporaryCredential]:
        """列出所有凭证 (隐藏值)"""
        return [self.get_credential(cid) for cid in self._credentials]

    def cleanup_expired(self) -> int:
        """清理过期凭证"""
        expired = [
            cid for cid, cred in self._credentials.items()
            if cred.is_expired or cred.is_depleted
        ]

        for cid in expired:
            self.revoke(cid)

        return len(expired)

    def _generate_id(self, name: str, value: str) -> str:
        """生成唯一凭证 ID"""
        unique = f"{name}:{value}:{time.time()}:{uuid.uuid4()}"
        return hashlib.sha256(unique.encode()).hexdigest()[:16]


class CredentialManager:
    """
    凭证管理器 - 高层接口

    结合 Vault 和临时凭证管理
    """

    def __init__(
        self,
        vault: VaultBackend,
        injector: Optional[SandboxInjector] = None,
        audit_logger: Optional["AuditLogger"] = None,
    ):
        """
        Args:
            vault: 密钥存储后端
            injector: 注入器 (默认创建新实例)
            audit_logger: 审计日志
        """
        self._vault = vault
        self._injector = injector or SandboxInjector(audit_logger=audit_logger)
        self._audit = audit_logger

    def create_temp_credential(
        self,
        name: str,
        ttl_seconds: int = 300,
        max_uses: int = 1,
    ) -> TemporaryCredential:
        """
        从 Vault 创建临时凭证

        用法:
            cred = manager.create_temp_credential("openai_api_key", ttl_seconds=300)
            result = injector.inject(cred.id)
        """
        # 从 Vault 获取原始密钥
        secret = self._vault.get_secret(name)

        # 生成临时凭证
        credential = self._injector.create_credential(
            name=name,
            value=secret.value,
            ttl_seconds=ttl_seconds,
            max_uses=max_uses,
        )

        return credential

    @contextmanager
    def scoped_access(self, name: str, ttl_seconds: int = 300):
        """
        作用域访问：自动创建和清理临时凭证

        用法:
            with manager.scoped_access("database_password") as injector:
                # 在此作用域内可访问密钥
                conn = connect_db()
        """
        credential = self.create_temp_credential(name, ttl_seconds)
        env_key = f"{self._injector.prefix}{name.upper()}"

        result = self._injector.inject(credential.id, env_key)

        if not result.success:
            raise RuntimeError(f"Failed to inject {name}: {result.error}")

        try:
            yield self._injector
        finally:
            self._injector.cleanup(env_key)

    def revoke_all(self) -> int:
        """撤销所有临时凭证"""
        # 清理过期
        self._injector.cleanup_expired()

        # 撤销所有
        count = 0
        for cid in list(self._injector._credentials.keys()):
            if self._injector.revoke(cid):
                count += 1

        return count


# 预定义的注入器实例


def create_default_injector(**kwargs) -> SandboxInjector:
    """创建默认注入器"""
    return SandboxInjector(
        prefix=kwargs.get("prefix", "AGENT_TEMP_"),
        default_ttl_seconds=kwargs.get("ttl", 300),
        default_max_uses=kwargs.get("max_uses", 1),
    )
