# Python Agent 配置安全管理 - 实现方案

## 完整架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部密钥源层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  KMS/Vault│  │ 环境变量 │  │  加密文件│  │ Keyring  │       │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘       │
└────────┼─────────────┼─────────────┼─────────────┼─────────────┘
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    VaultBackend (统一接口) │
         │  - get_secret()           │
         │  - list_secrets()         │
         │  - set_secret()           │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    配置加载层              │
         │  - 验证与类型检查           │
         │  - 日志脱敏                │
         │  - 访问审计                │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    CryptoManager          │
         │  - AES-256-GCM 加密        │
         │  - PBKDF2 密钥派生         │
         │  - SecureBytes (mlock)    │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    TempCredentialManager  │
         │  - 短期凭证 (JWT)          │
         │  - 自动过期                │
         │  - 作用域限制              │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    SandboxInjector        │
         │  - 环境变量注入            │
         │  - 作用域隔离              │
         │  - 自动清理                │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │    Agent 沙箱              │
         │  - Docker / WASM / VM     │
         │  - seccomp 过滤            │
         │  - 只读文件系统            │
         └───────────────────────────┘
```

---

## 核心模块

### 1. SecureConfigLoader

```python
"""
安全配置加载器

职责：
- 从多个源加载配置
- 验证配置完整性
- 脱敏日志
- 审计访问
"""
from typing import Optional, Any
from pydantic import BaseModel, Field, validator

class ConfigEntry(BaseModel):
    """配置条目"""
    name: str
    value: str
    source: str  # env, file, kms, etc.
    sensitive: bool = False
    accessed_count: int = 0

    def log_value(self) -> str:
        """安全的日志表示（脱敏）"""
        if not self.sensitive:
            return self.value
        if len(self.value) <= 10:
            return "***"
        return f"{self.value[:5]}...{self.value[-5:]}"

class SecureConfigLoader:
    def __init__(
        self,
        vault_uri: str = "env://",
        encryption_key: Optional[bytes] = None,
        audit_logger=None,
    ):
        from .vault import create_vault_from_uri
        from .crypto import CryptoManager

        # 初始化 Vault 后端
        self.vault = create_vault_from_uri(
            vault_uri,
            crypto_manager=CryptoManager(encryption_key) if encryption_key else None
        )

        # 审计日志
        self.audit = audit_logger

        # 配置缓存
        self._cache: dict[str, ConfigEntry] = {}

    def get_secret(
        self,
        name: str,
        default: Optional[str] = None,
        cache: bool = True,
    ) -> str:
        """
        获取敏感配置

        Args:
            name: 配置名称
            default: 默认值（如果不存在）
            cache: 是否缓存结果

        Returns:
            配置值
        """
        # 检查缓存
        if cache and name in self._cache:
            entry = self._cache[name]
            entry.accessed_count += 1
            self._audit_access(name, "cache")
            return entry.value

        # 从 Vault 获取
        try:
            secret = self.vault.get_secret(name)
            entry = ConfigEntry(
                name=name,
                value=secret.value,
                source=self.vault.__class__.__name__,
                sensitive=True,
            )
            if cache:
                self._cache[name] = entry

            self._audit_access(name, "vault", success=True)
            return entry.value

        except Exception as e:
            self._audit_access(name, "vault", success=False, error=str(e))
            if default is not None:
                return default
            raise ValueError(f"Secret not found: {name}") from e

    def get_config(
        self,
        name: str,
        validator: Optional[callable] = None,
    ) -> Any:
        """
        获取非敏感配置

        Args:
            name: 配置名称
            validator: 验证函数

        Returns:
            配置值（转换后）
        """
        value = os.environ.get(name)
        if value is None:
            raise ValueError(f"Config not found: {name}")

        if validator:
            value = validator(value)

        return value

    def _audit_access(
        self,
        name: str,
        source: str,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """记录访问审计"""
        if self.audit:
            self.audit.info(
                "config_access",
                name=name,
                source=source,
                success=success,
                error=error,
                timestamp=datetime.utcnow().isoformat(),
            )
```

### 2. SandboxInjector

```python
"""
沙箱配置注入器

职责：
- 安全地向子进程注入环境变量
- 作用域隔离
- 自动清理
"""
import subprocess
import tempfile
import shutil
from pathlib import Path

class SandboxInjector:
    """
    沙箱配置注入器

    特性：
    - 只注入必要的配置
    - 临时文件自动清理
    - 作用域隔离
    """
    def __init__(self, config_loader: SecureConfigLoader):
        self.config = config_loader
        self._temp_dirs: list[Path] = []

    def prepare_env(
        self,
        secret_names: list[str],
        extra_vars: dict[str, str] = None,
    ) -> dict[str, str]:
        """
        准备沙箱环境变量

        Args:
            secret_names: 需要注入的密钥名称
            extra_vars: 额外的环境变量

        Returns:
            清理后的环境变量字典
        """
        # 最小化环境
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": "/tmp/agent",
            "TMPDIR": "/tmp/agent/tmp",
            "PYTHONPATH": "/app",
        }

        # 注入敏感配置
        for name in secret_names:
            try:
                value = self.config.get_secret(name)
                env[name.upper()] = value
            except Exception as e:
                logger.warning(f"Failed to load secret {name}: {e}")

        # 额外变量
        if extra_vars:
            env.update(extra_vars)

        return env

    def run_in_sandbox(
        self,
        command: list[str],
        secrets: list[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """
        在沙箱中运行命令

        Args:
            command: 命令和参数
            secrets: 需要注入的密钥名称
            cwd: 工作目录
            timeout: 超时时间（秒）

        Returns:
            进程结果
        """
        # 准备环境
        env = self.prepare_env(secrets)

        # 创建临时工作目录
        work_dir = cwd or Path(tempfile.mkdtemp(prefix="agent_sandbox_"))
        self._temp_dirs.append(work_dir)

        try:
            # 运行进程
            result = subprocess.run(
                command,
                env=env,
                cwd=work_dir,
                timeout=timeout,
                # 安全选项
                preexec_fn=lambda: os.setpgrp(),  # 新进程组
                # 不使用 shell
                shell=False,
                # 捕获输出
                capture_output=True,
                text=True,
            )

            return result

        finally:
            # 清理临时目录
            self._cleanup(work_dir)

    def _cleanup(self, path: Path):
        """安全清理临时目录"""
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")
```

### 3. TempCredentialManager

```python
"""
临时凭证管理器

职责：
- 生成短期 JWT 凭证
- 自动过期
- 作用域限制
"""
import time
import jwt
import secrets
from typing import Optional

class TempCredentialManager:
    """
    临时凭证管理器

    特性：
    - JWT Ed25519 签名
    - 短期有效（5-15分钟）
    - 作用域限制
    - 审计日志
    """
    def __init__(
        self,
        signing_key: Optional[bytes] = None,
        default_ttl: int = 600,  # 10 分钟
        audit_logger=None,
    ):
        # 生成或使用提供的签名密钥
        self.signing_key = signing_key or secrets.token_bytes(32)
        self.default_ttl = default_ttl
        self.audit = audit_logger

        # 撤销列表（内存中，生产环境应使用 Redis）
        self._revoked: set[str] = set()

    def create_credential(
        self,
        scopes: list[str],
        subject: str,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        创建临时凭证

        Args:
            scopes: 权限作用域
            subject: 主体标识
            ttl_seconds: 有效期（秒）

        Returns:
            JWT token
        """
        now = time.time()
        ttl = ttl_seconds or self.default_ttl

        payload = {
            "sub": subject,  # 主体
            "scopes": scopes,  # 权限
            "iat": now,  # 签发时间
            "exp": now + ttl,  # 过期时间
            "nbf": now,  # 生效时间
            "jti": secrets.token_hex(16),  # JWT ID（用于撤销）
        }

        token = jwt.encode(
            payload,
            self.signing_key,
            algorithm="HS256",
        )

        # 记录审计
        if self.audit:
            self.audit.info(
                "credential_created",
                subject=subject,
                scopes=scopes,
                ttl=ttl_seconds,
                jti=payload["jti"],
            )

        return token

    def verify_credential(self, token: str) -> Optional[dict]:
        """
        验证临时凭证

        Args:
            token: JWT token

        Returns:
            解码后的 payload，验证失败返回 None
        """
        try:
            payload = jwt.decode(
                token,
                self.signing_key,
                algorithms=["HS256"],
            )

            # 检查撤销列表
            jti = payload.get("jti")
            if jti in self._revoked:
                return None

            return payload

        except jwt.InvalidTokenError:
            return None

    def revoke_credential(self, token: str):
        """撤销凭证"""
        try:
            payload = jwt.decode(
                token,
                self.signing_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            self._revoked.add(payload["jti"])

            if self.audit:
                self.audit.warning(
                    "credential_revoked",
                    jti=payload["jti"],
                )

        except jwt.InvalidTokenError:
            pass
```

### 4. LogSanitizer

```python
"""
日志脱敏器

职责：
- 自动检测敏感信息
- 替换为占位符
- 保留调试信息
"""
import re
from typing import Callable

class LogSanitizer:
    """
    日志脱敏器

    特性：
- 正则匹配敏感模式
- 保留前后片段用于调试
- 可自定义规则
    """
    # 默认敏感模式
    DEFAULT_PATTERNS = [
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)[\w-]+', r'\1***'),
        (r'(secret["\']?\s*[:=]\s*["\']?)[\w-]+', r'\1***'),
        (r'(token["\']?\s*[:=]\s*["\']?)[\w.-]+', r'\1***'),
        (r'(password["\']?\s*[:=]\s*["\']?)[^\s"\']+', r'\1***'),
        (r'(sk-[a-zA-Z0-9]{20,})[a-zA-Z0-9]*', r'\1***'),
        (r'(Bearer\s+)[\w.-]+', r'\1***'),
        (r'(\d{4})\d{6}(\d{4})', r'\1******\2'),  # 银行卡
        (r'(\w[\w.-]{3})[\w.-]+@([\w.-]{3}\w)', r'\1***@\2'),  # 邮箱
    ]

    def __init__(self, custom_patterns: list[tuple[str, str]] = None):
        patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            patterns.extend(custom_patterns)

        self.regexes = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in patterns
        ]

    def sanitize(self, message: str) -> str:
        """
        脱敏日志消息

        Args:
            message: 原始消息

        Returns:
            脱敏后的消息
        """
        result = message
        for regex, replacement in self.regexes:
            result = regex.sub(replacement, result)
        return result

    def sanitize_dict(self, data: dict) -> dict:
        """脱敏字典中的敏感值"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.sanitize(value)
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict(value)
            else:
                result[key] = value
        return result


# 使用示例
if __name__ == "__main__":
    # 初始化
    config = SecureConfigLoader(vault_uri="env://AGENT_")
    injector = SandboxInjector(config)
    credentials = TempCredentialManager()
    sanitizer = LogSanitizer()

    # 运行沙箱
    result = injector.run_in_sandbox(
        command=["python", "agent.py"],
        secrets=["openai_api_key", "database_url"],
        timeout=30,
    )

    # 创建临时凭证
    token = credentials.create_credential(
        scopes=["read:database", "write:cache"],
        subject="agent-123",
    )

    # 脱敏日志
    safe_message = sanitizer.sanitize(
        "Connected with api_key=sk-abc123... and token=xyz789..."
    )
    logger.info(safe_message)
```

---

## 安全检查清单

### 部署前检查

- [ ] `.env` 文件已加入 `.gitignore`
- [ ] 生产环境使用云 KMS 或 Vault
- [ ] 已配置 TLS/mTLS
- [ ] 日志脱敏已启用
- [ ] 审计日志已配置
- [ ] core dump 已禁用
- [ ] 依赖漏洞扫描通过
- [ ] 沙箱隔离已测试

### 运行时检查

- [ ] 密钥通过 SecureBytes 加载
- [ ] 环境变量使用后立即清零
- [ ] 临时凭证已设置 TTL
- [ ] 沙箱进程已限制权限
- [ ] 审计日志正常记录
- [ ] 异常访问告警已配置

### 应急响应

- [ ] 密钥轮换流程已制定
- [ ] 撤销机制已测试
- [ ] 事件响应预案已演练
- [ ] 备份恢复已验证
