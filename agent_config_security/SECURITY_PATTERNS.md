# Python Agent 配置安全管理 - 安全设计模式

## 一、密钥生命周期管理

### 1.1 密钥生成

**安全原则：**
- 使用加密安全的随机数生成器（CSPRNG）
- 足够的密钥长度（AES-256 = 32 bytes）
- 唯一性保证

**Python 实现：**
```python
import secrets
import os

# ✅ 正确：使用 secrets 模块 (Python 3.6+)
api_key = secrets.token_urlsafe(32)
master_key = secrets.token_bytes(32)  # AES-256

# ✅ 正确：使用 os.urandom (兼容旧版)
salt = os.urandom(16)

# ❌ 错误：不要使用 random 模块
import random
api_key = ''.join(random.choices(...))  # 可预测
```

### 1.2 密钥存储

| 存储方式 | 安全性 | 性能 | 适用场景 |
|----------|--------|------|----------|
| **环境变量** | ⚠️ 中 | ⚡⚡⚡ | 容器化部署 |
| **加密文件** | ✅ 高 | ⚡⚡ | 单机部署 |
| **云 KMS** | ✅✅ 极高 | ⚡ | 生产环境 |
| **HashiCorp Vault** | ✅✅ 极高 | ⚡⚡ | 企业环境 |
| **内存** | ⚠️ 低 | ⚡⚡⚡ | 运行时缓存 |

**推荐架构：**
```
┌─────────────────┐
│   云 KMS/Vault  │ ← 持久化存储（加密 at rest）
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  配置加载层      │ ← 验证、解密、脱敏
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SecureBytes    │ ← mlock + 自动过零
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 沙箱     │ ← 环境变量注入
└─────────────────┘
```

### 1.3 密钥轮换

**自动轮换策略：**
```python
from datetime import datetime, timedelta

class KeyRotationPolicy:
    # 密钥最大有效期
    MAX_AGE = timedelta(days=90)

    # 轮换缓冲期（提前多久生成新密钥）
    BUFFER_PERIOD = timedelta(days=7)

    def should_rotate(self, created_at: datetime) -> bool:
        age = datetime.utcnow() - created_at
        return age >= (self.MAX_AGE - self.BUFFER_PERIOD)

# 轮换流程：
# 1. 生成新密钥
# 2. 双写：新旧密钥都可用
# 3. 验证新密钥工作正常
# 4. 切换到新密钥
# 5. 撤销旧密钥
```

### 1.4 密钥撤销

**泄露响应机制：**
```python
class KeyRevocation:
    def revoke_and_rotate(self, leaked_key_id: str):
        # 1. 立即标记密钥为已撤销
        self.vault.revoke(leaked_key_id)

        # 2. 生成新密钥
        new_key = self.vault.generate()

        # 3. 强制所有连接重新认证
        self.auth_server.invalidate_all()

        # 4. 记录审计事件
        self.audit.log("key_revoked", key_id=leaked_key_id)

        # 5. 发送告警
        self.alert.send("Security incident: key revoked")
```

---

## 二、零信任架构

### 2.1 最小权限原则

**实现方式：**
```python
# ❌ 错误：授予过多权限
credentials = {
    "access_all_buckets": True,
    "delete_anything": True,
}

# ✅ 正确：最小权限
credentials = {
    "allowed_buckets": ["agent-data-prod"],
    "allowed_operations": ["read", "write"],
    "ip_whitelist": ["10.0.0.0/8"],
}
```

### 2.2 运行时动态授权

**临时凭证模式：**
```python
class TempCredentialManager:
    """
    临时凭证管理器

    特性：
    - 短期有效（5-15 分钟）
    - 自动过期
    - 独立作用域
    """
    def create_temp_token(
        self,
        scopes: list[str],
        ttl_seconds: int = 600,
    ) -> str:
        """创建 JWT 临时凭证"""
        payload = {
            "scopes": scopes,
            "exp": time.time() + ttl_seconds,
            "nbf": time.time(),  # Not Before
            "jti": secrets.token_hex(16),  # JWT ID
        }
        return jwt.encode(payload, self.signing_key, algorithm="Ed25519")
```

### 2.3 审计日志

**结构化审计：**
```python
import structlog

audit = structlog.get_logger("audit")

def audit_secret_access(key_name: str, accessor: str, success: bool):
    audit.info(
        "secret_access",
        key_name=key_name,
        accessor=accessor,
        success=success,
        timestamp=datetime.utcnow().isoformat(),
        source_ip=get_request_ip(),
        user_agent=get_request_header("User-Agent"),
    )
```

---

## 三、沙箱配置隔离方案

### 3.1 隔离层级对比

| 隔离方式 | 隔离强度 | 启动时间 | 内存开销 | 适用场景 |
|----------|----------|----------|----------|----------|
| **进程级** (subprocess) | ⭐ | ⚡⚡⚡ | 低 | 简单脚本 |
| **容器级** (Docker) | ⭐⭐⭐ | ⚡⚡ | 中 | Agent 沙箱 |
| **VM 级** (Firecracker) | ⭐⭐⭐⭐⭐ | ⚡ | 高 | 高安全要求 |
| **WASM** | ⭐⭐⭐⭐ | ⚡⚡⚡ | 极低 | 代码执行 |

### 3.2 进程级隔离

```python
import subprocess
import os

def run_in_sandboxed_process(command: str, env_vars: dict):
    """
    在隔离进程中运行命令

    安全措施：
    - 清除继承的环境变量
    - 只注入必要的配置
    - 使用新进程组
    """
    # 创建最小化环境
    clean_env = {
        "PATH": "/usr/bin:/bin",
        **env_vars,  # 只注入必要变量
    }

    result = subprocess.run(
        command,
        env=clean_env,
        # 安全选项
        preexec_fn=lambda: os.setpgrp(),  # 新进程组
        # 不使用 shell=True 防止注入
        shell=False,
    )
    return result
```

### 3.3 容器级隔离

```dockerfile
# 安全的 Agent 容器
FROM python:3.11-slim

# 非 root 用户运行
RUN useradd -m -u 1000 agent
USER agent

# 最小化安装
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 只读根文件系统
# --read-only --tmpfs /tmp --tmpfs /run

# 禁用 privileged 模式
# --security-opt=no-new-privileges

# seccomp 过滤
# --security-opt seccomp=default.json
```

### 3.4 WebAssembly 沙箱

```python
# WASM 作为二级沙箱
import wasmer

def run_untrusted_code(wasm_file: str, config: dict):
    """
    在 WASM 沙箱中执行代码

    特性：
    - 内存隔离
    - 无系统调用
    - 资源限制
    """
    store = wasmer.Store()
    module = wasmer.Module(store, open(wasm_file, "rb").read())

    # 限制内存
    engine = wasmer.Engine(
        wasmer.CompilerConfig(
            features=[],  # 禁用危险特性
        )
    )

    import_object = {
        "env": {
            "memory": wasmer.Memory(store, max_pages=1),  # 64KB 限制
        }
    }

    instance = wasmer.Instance(store, module, import_object)
    return instance.exports.main()
```

---

## 四、Python 特定实现

### 4.1 secrets 模块

```python
import secrets

# ✅ 生成密码
password = secrets.token_urlsafe(32)

# ✅ 生成安全随机数
random_int = secrets.randbelow(100)

# ✅ 安全的选择
choice = secrets.choice(["a", "b", "c"])

# ✅ 令牌重置（用于密码重置等）
reset_token = secrets.token_hex(32)
```

### 4.2 keyring 库

```python
import keyring

# ✅ 使用系统密钥环存储
def store_api_key(service: str, username: str, key: str):
    keyring.set_password(service, username, key)

def get_api_key(service: str, username: str) -> str:
    return keyring.get_password(service, username)

# 使用示例
store_api_key("openai", "agent", "sk-...")
key = get_api_key("openai", "agent")

# 优势：
# - 与操作系统集成
# - 用户登录后自动解锁
# - 支持多种后端（Windows Credential Manager, macOS Keychain, Linux Secret Service）
```

### 4.3 环境变量安全加载

```python
from pydantic import Field, validator
from pydantic_settings import BaseSettings

class SecureSettings(BaseSettings):
    # 敏感配置
    openai_api_key: str = Field(..., min_length=20)
    database_url: str

    # 非敏感配置
    debug: bool = False
    log_level: str = "INFO"

    @validator('openai_api_key')
    def validate_api_key(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('Invalid API key format')
        return v

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False

# 生产环境：从环境变量加载
# settings = SecureSettings()
```

### 4.4 内存加密 (cryptography)

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class InMemoryEncryption:
    """
    内存数据加密

    使用场景：
    - 缓存敏感数据
    - 进程间通信
    - 临时存储
    """
    def __init__(self, key: bytes):
        self.aesgcm = AESGCM(key)

    def encrypt(self, data: bytes) -> bytes:
        nonce = os.urandom(12)
        return nonce + self.aesgcm.encrypt(nonce, data, None)

    def decrypt(self, encrypted: bytes) -> bytes:
        nonce, ciphertext = encrypted[:12], encrypted[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)
```

---

## 五、NIST 零信任原则对照

| NIST SP 800-207 原则 | 实现 |
|----------------------|------|
| **永不信任，始终验证** | 每次请求验证 JWT，无隐式信任 |
| **最小权限访问** | 临时凭证 + 作用域限制 |
| **假设已被攻破** | 深度防御，多层加密 |
| **显式验证** | mTLS 双向认证 |
| **持续监控** | 审计日志 + 异常检测 |

---

## 参考资料

- NIST SP 800-207: Zero Trust Architecture
- OWASP Secrets Management Cheat Sheet
- OWASP Key Management Cheat Sheet
- CIS Controls v8
- Python secrets 模块文档
- HashiCorp Vault Best Practices
- Kubernetes Pod Security Standards
