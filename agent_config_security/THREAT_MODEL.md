# Python Agent 沙箱配置安全 - 威胁模型分析

## 攻击向量与防御措施

### 1. 环境变量嗅探

**攻击方式：**
```bash
# 通过 /proc 文件系统读取环境变量
cat /proc/<PID>/environ
cat /proc/self/environ

# 通过 ps 命令
ps auxe

# 通过 /proc/<PID>/cmdline
```

**防御措施：**
- ✅ 使用 `SecureBytes` 最小化密钥在内存中的生命周期
- ✅ 及时清零使用后的敏感数据（`zero()` 方法）
- ✅ 使用 mlock 防止内存 swap
- ✅ 沙箱进程启动后立即从父进程环境清除敏感变量
- ⚠️ 容器内限制 `/proc` 访问（通过 seccomp 或 AppArmor）

### 2. 日志泄露

**攻击方式：**
```python
# 错误的日志记录
logger.info(f"API Key: {api_key}")  # 直接泄露
logger.error(f"Failed to connect: {e}")  # 异常可能包含凭证
```

**防御措施：**
- ✅ 使用 `LogSanitizer` 自动脱敏
- ✅ 结构化日志（JSON）便于检测敏感模式
- ✅ 正则匹配敏感关键词（api_key, secret, token, password）
- ✅ 指纹替换：`sk-xxxxx...xxxxx`（保留前后各5字符用于调试）
- ✅ 日志写入前验证

### 3. 错误消息暴露

**攻击方式：**
```python
# 数据库连接失败可能暴露凭证
try:
    db.connect(password="secret123")
except Exception as e:
    raise  # e 可能包含 "Access denied for user 'admin'@'host'"
```

**防御措施：**
- ✅ 自定义异常类，脱敏后重新抛出
- ✅ 生产环境禁用详细错误堆栈
- ✅ 使用安全错误码而非消息
- ✅ 敏感操作单独捕获，返回通用错误

### 4. 内存转储

**攻击方式：**
```bash
# Core dump 可能包含密钥
gcore <PID>
# 或
kill -11 <PID>  # SIGSEGV

# Python pickle 序列化可能泄露内存
pickle.dump(obj, file)  # obj.__dict__ 可能包含敏感数据
```

**防御措施：**
- ✅ `SecureBytes` 禁止 pickle 序列化
- ✅ 生产环境禁用 core dump (`ulimit -c 0`)
- ✅ 使用 `__getstate__` 和 `__setstate__` 控制序列化
- ✅ 密钥存储在专用内存区域，不附加到对象

### 5. 供应链攻击

**攻击方式：**
- 恶意 PyPI 包窃取环境变量
- 依赖项中的后门
- CI/CD 流水线注入

**防御措施：**
- ✅ 使用 `pip-audit` 扫描依赖漏洞
- ✅ 固定依赖版本（`requirements.txt` 或 `poetry.lock`）
- ✅ 签名验证（PEP 730 包签名）
- ✅ 私有 PyPI 镜像
- ✅ SBOM（软件物料清单）追踪

### 6. 中间人攻击 (MITM)

**攻击方式：**
- HTTPS 降级
- 自签名证书绕过
- DNS 劫持

**防御措施：**
- ✅ 强制 TLS 1.3
- ✅ 证书固定（Certificate Pinning）
- ✅ mTLS 双向认证
- ✅ HSTS 启用
- ✅ DNS over HTTPS

### 7. 时间攻击 (Timing Attack)

**攻击方式：**
```python
# 错误的密钥比较
if user_input == stored_secret:
    # 执行时间差异可泄露信息
```

**防御措施：**
- ✅ 使用 `hmac.compare_digest()` 进行常量时间比较
- ✅ `CryptoManager.constant_time_compare()` 实现
- ✅ 避免基于比较结果的分支
- ✅ 引入随机延迟（需谨慎）

### 8. 沙箱逃逸

**攻击方式：**
- Docker 容器逃逸（dirty cow, runc 漏洞）
- Python subprocess 注入
- 反序列化漏洞

**防御措施：**
- ✅ 使用 rootless 容器
- ✅ seccomp 过滤系统调用
- ✅ AppArmor/SELinux 强制访问控制
- ✅ 禁用危险模块（`os.system`, `subprocess` 在沙箱内）
- ✅ 使用 WebAssembly 作为二级沙箱
- ✅ Firecracker 微虚拟机隔离

---

## 威胁建模矩阵

| 威胁 | 可能性 | 影响 | 风险等级 | 优先级 |
|------|--------|------|----------|--------|
| 环境变量嗅探 | 高 | 高 | 🔴 严重 | P0 |
| 日志泄露 | 中 | 高 | 🟠 高 | P1 |
| 错误消息暴露 | 中 | 中 | 🟡 中 | P2 |
| 内存转储 | 低 | 高 | 🟠 高 | P1 |
| 供应链攻击 | 低 | 高 | 🟠 高 | P1 |
| 中间人攻击 | 低 | 中 | 🟡 中 | P2 |
| 时间攻击 | 低 | 低 | 🟢 低 | P3 |
| 沙箱逃逸 | 低 | 严重 | 🟠 高 | P1 |

---

## 安全检查清单

### 启动前检查
- [ ] `.env` 文件已加入 `.gitignore`
- [ ] 敏感配置使用环境变量或密钥管理服务
- [ ] 已配置日志脱敏
- [ ] 已禁用 core dump
- [ ] 已验证依赖包完整性

### 运行时检查
- [ ] 密钥通过 `SecureBytes` 加载
- [ ] 环境变量使用后立即清零
- [ ] 错误消息不含敏感信息
- [ ] 审计日志正常记录
- [ ] 沙箱隔离生效

### 应急响应
- [ ] 密钥泄露后轮换流程
- [ ] 异常访问告警配置
- [ ] 备份恢复测试
- [ ] 事件响应预案
