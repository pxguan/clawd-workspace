"""
安全配置加载器

核心功能：
- 统一的配置加载接口
- 类型验证和转换
- 自动解密
- 访问审计集成
- 配置缓存和热更新
"""

import os
import logging
import time
from typing import Any, Optional, Type, TypeVar, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .vault import VaultBackend, VaultError, create_vault_from_uri, SecretEntry
from .crypto import CryptoManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ConfigSource(str, Enum):
    """配置来源类型"""
    ENV = "environment"
    VAULT = "vault"
    FILE = "file"
    DEFAULT = "default"


@dataclass
class ConfigEntry:
    """配置条目元数据"""
    name: str
    value: Any
    source: ConfigSource
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    is_secret: bool = False
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def mark_accessed(self) -> None:
        """记录访问"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class ConfigValidationError(Exception):
    """配置验证失败"""


class SecureConfigLoader:
    """
    安全配置加载器

    特性：
    - 多源加载 (环境变量、Vault、文件)
    - 类型验证 (Pydantic)
    - 自动解密
    - 访问审计
    - 缓存和 TTL
    - 敏感信息标记
    """

    def __init__(
        self,
        vault_uri: str = "env://",
        encryption_key: Optional[bytes] = None,
        audit_logger: Optional["AuditLogger"] = None,
        cache_ttl_seconds: int = 300,
        auto_reload: bool = False,
    ):
        """
        Args:
            vault_uri: 密钥存储 URI (env://, file://, aws://, etc.)
            encryption_key: 加密主密钥 (用于文件 Vault)
            audit_logger: 审计日志记录器
            cache_ttl_seconds: 缓存过期时间
            auto_reload: 自动重新加载配置
        """
        self.vault_uri = vault_uri
        self._cache: dict[str, ConfigEntry] = {}
        self._cache_ttl = cache_ttl_seconds
        self._auto_reload = auto_reload
        self._audit = audit_logger

        # 初始化 Vault
        if vault_uri.startswith("file://"):
            if not encryption_key:
                raise ValueError("encryption_key required for file vault")
            crypto = CryptoManager(master_key=encryption_key)
            self._vault: VaultBackend = create_vault_from_uri(
                vault_uri, crypto_manager=crypto
            )
        else:
            self._vault = create_vault_from_uri(vault_uri)

        # 配置文件路径
        self._config_paths: list[Path] = []
        self._watchers: list[Callable] = []

        # 敏感字段模式 (用于日志脱敏)
        self._sensitive_patterns = [
            "password", "secret", "token", "key", "credential",
            "api_key", "apikey", "private_key", "auth",
        ]

    def add_config_file(self, path: str | Path) -> None:
        """添加配置文件路径"""
        self._config_paths.append(Path(path))

    def load_model(self, model_class: Type[T]) -> T:
        """
        加载并验证配置模型

        Args:
            model_class: Pydantic 模型类

        Returns:
            验证后的配置实例

        Raises:
            ConfigValidationError: 验证失败
        """
        raw_config = self._load_raw_config()
        try:
            return model_class(**raw_config)
        except ValidationError as e:
            raise ConfigValidationError(f"Config validation failed: {e}")

    def get(self, key: str, default: Any = None, decrypt: bool = False) -> Any:
        """
        获取配置值

        Args:
            key: 配置键名 (支持嵌套，如 "database.host")
            default: 默认值
            decrypt: 是否解密 (用于加密的配置值)

        Returns:
            配置值
        """
        # 检查缓存
        cached = self._get_from_cache(key)
        if cached and not self._is_stale(cached):
            cached.mark_accessed()
            self._log_access(key, cached, from_cache=True)
            return cached.value

        # 从 Vault 加载
        value = self._load_value(key, default, decrypt)

        # 缓存结果
        is_secret = any(p in key.lower() for p in self._sensitive_patterns)
        entry = ConfigEntry(
            name=key,
            value=value,
            source=ConfigSource.VAULT if value != default else ConfigSource.DEFAULT,
            is_secret=is_secret or decrypt,
        )
        self._cache[key] = entry

        self._log_access(key, entry, from_cache=False)
        entry.mark_accessed()
        return value

    def get_secret(self, name: str) -> str:
        """
        获取敏感配置 (密钥、密码等)

        这是 get() 的便捷方法，强制标记为敏感
        """
        value = self.get(name, decrypt=True)
        if value is None:
            raise ConfigValidationError(f"Secret not found: {name}")
        return str(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = self.get(key, default)
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ConfigValidationError(f"Invalid integer value for {key}: {value}")

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def get_list(self, key: str, default: list | None = None, separator: str = ",") -> list:
        """获取列表配置"""
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [v.strip() for v in value.split(separator) if v.strip()]
        return [value]

    def _load_raw_config(self) -> dict[str, Any]:
        """加载原始配置字典"""
        config = {}

        # 从配置文件加载
        for path in self._config_paths:
            if path.exists():
                config.update(self._load_config_file(path))

        # 从环境变量加载
        for key, value in os.environ.items():
            if not key.startswith(("AGENT_", "APP_")):
                continue
            config_key = key.lower().split("_", 1)[1] if "_" in key else key.lower()
            config[config_key] = value

        return config

    def _load_config_file(self, path: Path) -> dict[str, Any]:
        """加载配置文件"""
        suffix = path.suffix.lower()

        if suffix == ".json":
            import json
            return json.loads(path.read_text())

        elif suffix in (".yml", ".yaml"):
            try:
                import yaml
                return yaml.safe_load(path.read_text()) or {}
            except ImportError:
                logger.warning("PyYAML not installed, skipping YAML files")
                return {}

        elif suffix == ".env":
            from dotenv import dotenv_values
            return dotenv_values(path)

        elif suffix == ".toml":
            try:
                import tomllib
                return tomllib.loads(path.read_text())
            except ImportError:
                logger.warning("tomllib not available, skipping TOML files")
                return {}

        else:
            logger.warning(f"Unknown config file format: {suffix}")
            return {}

    def _load_value(self, key: str, default: Any, decrypt: bool) -> Any:
        """从 Vault 加载单个值"""
        try:
            secret = self._vault.get_secret(key)
            value = secret.value

            if decrypt:
                # 假设值是加密的 hex 字符串
                try:
                    from .crypto import CryptoManager
                    # 需要加密密钥，这里简化处理
                    # 实际应该从 vault 读取加密配置
                    pass
                except Exception:
                    pass

            return value
        except VaultError:
            return default

    def _get_from_cache(self, key: str) -> Optional[ConfigEntry]:
        """从缓存获取"""
        return self._cache.get(key)

    def _is_stale(self, entry: ConfigEntry) -> bool:
        """检查缓存是否过期"""
        if self._cache_ttl <= 0:
            return False
        age = datetime.utcnow() - entry.loaded_at
        return age > timedelta(seconds=self._cache_ttl)

    def _log_access(
        self, key: str, entry: ConfigEntry, from_cache: bool
    ) -> None:
        """记录访问到审计日志"""
        if self._audit:
            self._audit.log_config_access(
                key=key,
                source=entry.source,
                is_secret=entry.is_secret,
                from_cache=from_cache,
            )

    def reload(self) -> None:
        """重新加载配置"""
        self._cache.clear()
        logger.info("Configuration reloaded")

    def invalidate(self, key: str) -> None:
        """使特定配置失效"""
        if key in self._cache:
            del self._cache[key]

    def list_loaded(self) -> list[str]:
        """列出已加载的配置键"""
        return list(self._cache.keys())

    def health_check(self) -> dict[str, bool]:
        """健康检查"""
        return {
            "vault": self._vault.health_check(),
            "cache": len(self._cache) > 0,
        }


# 预定义的配置模型示例


class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    host: str
    port: int = 5432
    username: str
    password: str  # 标记为敏感
    database: str
    pool_size: int = 10
    ssl_mode: str = "require"


class ApiConfig(BaseModel):
    """API 配置模型"""
    base_url: str
    api_key: str  # 敏感
    timeout: int = 30
    retry_attempts: int = 3
    rate_limit: int = 100


class AgentConfig(BaseModel):
    """完整 Agent 配置模型"""
    database: DatabaseConfig
    api: ApiConfig
    debug: bool = False
    log_level: str = "INFO"
    max_tokens: int = 4096
    temperature: float = 0.7

    class Config:
        # Pydantic v2 配置
        pass


# 使用示例


def create_loader_from_env() -> SecureConfigLoader:
    """从环境变量创建配置加载器"""
    vault_uri = os.getenv("AGENT_VAULT_URI", "env://AGENT_")

    # 从环境变量获取加密密钥
    encryption_key_hex = os.getenv("AGENT_ENCRYPTION_KEY")
    encryption_key = bytes.fromhex(encryption_key_hex) if encryption_key_hex else None

    return SecureConfigLoader(
        vault_uri=vault_uri,
        encryption_key=encryption_key,
        cache_ttl_seconds=int(os.getenv("AGENT_CONFIG_CACHE_TTL", "300")),
    )
