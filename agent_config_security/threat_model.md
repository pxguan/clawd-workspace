# 威胁模型分析

## 攻击向量分析

### 1. 环境变量嗅探

**攻击描述：**
攻击者通过读取 `/proc/<pid>/environ` 或使用 `ps aux` 命令获取进程的环境变量，从而窃取敏感配置。

**影响等级：** HIGH

**防御措施：**
- ✅ 使用临时凭证而非永久环境变量
- ✅ 通过作用域限制最小化环境变量生命周期
- ✅ 敏感配置只在使用时注入，用完立即清理
- ✅ 使用内存锁定 (mlock) 防止 swap 泄露

**实现位置：**
- `config/injector.py` - `SandboxInjector.inject_context()`
- `security/memory.py` - `ProtectedString`, `MemoryGuard`

---

### 2. 日志泄露

**攻击描述：**
敏感信息被意外记录到日志文件中，攻击者通过访问日志文件获取凭证。

**影响等级：** HIGH

**防御措施：**
- ✅ 自动日志脱敏 (`LogSanitizer`)
- ✅ 敏感字段检测 (password, secret, token, key 等)
- ✅ 正则模式匹配检测常见凭证格式
- ✅ 异常堆栈清理

**实现位置：**
- `security/sanitizer.py` - `LogSanitizer`, `SanitizingFilter`

**示例：**
```python
setup_logging_with_sanitization()
logger.info({"api_key": "sk-1234567890"})  # 自动脱敏为: sk-***1234
```

---

### 3. 错误消息暴露

**攻击描述：**
错误消息中包含敏感信息，攻击者通过触发错误获取配置。

**影响等级：** MEDIUM

**防御措施：**
- ✅ 自定义异常类，不包含敏感信息
- ✅ 错误消息脱敏
- ✅ 生产环境禁用详细错误堆栈
- ✅ 审计日志记录但隐藏敏感值

**实现位置：**
- `security/sanitizer.py` - `sanitize_exception()`
- `config/crypto.py` - `EncryptionError`, `MemoryError`

---

### 4. 内存转储

**攻击描述：**
攻击者通过 core dump 或内存分析工具提取进程内存中的敏感数据。

**影响等级：** MEDIUM

**防御措施：**
- ✅ 使用 `SecureBytes` 自动过零
- ✅ mlock 锁定内存防止 swap
- ✅ 最小化敏感数据生命周期
- ✅ 禁用 core dump (生产环境)

**实现位置：**
- `config/crypto.py` - `SecureBytes`
- `security/memory.py` - `ProtectedString`, `secure_zero()`

**示例：**
```python
# 禁用 core dump
import resource
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
```

---

### 5. 供应链攻击

**攻击描述：**
恶意依赖包被植入，窃取或篡改配置。

**影响等级：** CRITICAL

**防御措施：**
- ✅ 固定依赖版本 (`requirements.txt`)
- ✅ 使用 `pip-audit` 扫描已知漏洞
- ✅ 签名验证 (审计日志)
- ✅ 最小化依赖

**实现位置：**
- `requirements.txt` - 固定版本
- `security/audit.py` - `AuditEvent.sign()`, `verify()`

**检查命令：**
```bash
pip-audit
pip install pip-audit
```

---

### 6. 中间人攻击

**攻击描述：**
攻击者拦截配置传输过程，窃取或篡改配置。

**影响等级：** HIGH

**防御措施：**
- ✅ 端到端加密 (AES-256-GCM)
- ✅ TLS/mTLS 用于远程 KMS
- ✅ HMAC 签名验证
- ✅ 证书固定

**实现位置：**
- `config/crypto.py` - `CryptoManager` (AES-256-GCM)
- `config/vault.py` - `KmsVault` (TLS)

---

### 7. 时间攻击

**攻击描述：**
攻击者通过测量密钥比较的时间差异推断密钥信息。

**影响等级：** LOW

**防御措施：**
- ✅ 常量时间字符串比较
- ✅ 使用 `hmac.compare_digest()`

**实现位置：**
- `config/crypto.py` - `CryptoManager.constant_time_compare()`

---

## 攻击树概览

```
[配置泄露]
├── [静态存储攻击]
│   ├── 文件系统访问 → AES-256-GCM 加密
│   ├── 数据库访问 → 加密 + 访问控制
│   └── 备份泄露 → 备份加密
│
├── [传输拦截]
│   ├── 网络嗅探 → TLS 1.3
│   ├── 中间人 → mTLS + 证书固定
│   └── 重放攻击 → nonce + 时间戳
│
├── [运行时攻击]
│   ├── 内存转储 → mlock + 过零
│   ├── 环境变量嗅探 → 临时凭证 + 清理
│   ├── 日志分析 → 自动脱敏
│   └── 调试器 attach → 禁用 ptrace (生产)
│
└── [供应链攻击]
    ├── 恶意依赖 → 固定版本 + 审计
    ├── 篡改的镜像 → 镜像签名验证
    └── CI/CD 入侵 → 构建时验证
```

## 防御深度矩阵

| 攻击阶段 | 防御层 | 实现模块 |
|---------|--------|----------|
| 密钥存储 | 文件系统加密 (AES-256-GCM) | `config/crypto.py` |
| 密钥传输 | TLS 1.3 + mTLS | `config/vault.py` |
| 密钥加载 | 访问控制 + 审计 | `config/loader.py` |
| 内存使用 | mlock + 过零 | `config/crypto.py`, `security/memory.py` |
| 环境变量 | 临时凭证 + 自动清理 | `config/injector.py` |
| 日志输出 | 自动脱敏 | `security/sanitizer.py` |
| 异常处理 | 堆栈清理 | `security/memory.py` |
| 访问追踪 | 审计日志 + 签名 | `security/audit.py` |
| 泄露检测 | 模式扫描 + 异常检测 | `security/credential.py` |
| 轮换策略 | 自动过期 + 轮换 | `security/credential.py` |
