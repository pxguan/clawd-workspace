# 安全检查清单

## 部署前检查

### 密钥管理
- [ ] 主密钥已从安全渠道获取并安全存储
- [ ] 主密钥没有硬编码在代码中
- [ ] 主密钥未提交到版本控制系统
- [ ] 使用强随机密钥 (AES-256: 32 bytes)
- [ ] 密钥轮换策略已配置
- [ ] 备份密钥已加密存储

### 配置来源
- [ ] 环境变量来源可信
- [ ] 文件权限正确设置 (600 或更严格)
- [ ] 远程 KMS 使用 TLS/mTLS
- [ ] 证书固定已启用 (如适用)
- [ ] 连接超时已配置

### 加密配置
- [ ] 使用 AES-256-GCM 或更强加密算法
- [ ] PBKDF2 迭代次数 >= 600,000
- [ ] 每次加密使用唯一 nonce
- [ ] 附加认证数据 (AAD) 已正确使用
- [ ] 密钥派生使用唯一盐值

---

## 运行时检查

### 内存保护
- [ ] 敏感数据使用 `SecureBytes` 或 `ProtectedString`
- [ ] mlock 已启用且有效
- [ ] 敏感数据生命周期最小化
- [ ] 不再需要时立即清零
- [ ] core dump 已禁用 (生产环境)
- [ ] swap 已禁用或加密

### 环境变量
- [ ] 临时凭证 TTL 已设置 (推荐 <= 300s)
- [ ] 使用次数限制已配置
- [ ] 作用域限制正确设置
- [ ] 使用后立即清理
- [ ] 没有永久敏感环境变量

### 日志安全
- [ ] 日志脱敏已启用
- [ ] 敏感字段模式已配置
- [ ] 异常堆栈已清理
- [ ] 日志文件权限正确 (600)
- [ ] 日志轮转已配置
- [ ] 敏感操作记录到审计日志

### 审计追踪
- [ ] 所有密钥访问已记录
- [ ] 审计日志已签名
- [ ] 审计日志写入只读存储
- [ ] 日志保留策略已配置
- [ ] 异常访问模式告警已启用

---

## 代码安全

### 依赖管理
- [ ] 依赖版本已固定
- [ ] 定期运行 `pip-audit`
- [ ] 已知漏洞已修复
- [ ] 最小化依赖原则

### 代码审查
- [ ] 没有 "TODO: 加密这里" 标记
- [ ] 没有调试 print 语句输出敏感数据
- [ ] 错误消息不包含敏感信息
- [ ] 密钥比较使用常量时间

### 测试覆盖
- [ ] 单元测试覆盖关键路径
- [ ] 安全测试包含负面用例
- [ ] 渗透测试已执行
- [ ] 混沌测试已考虑

---

## 基础设施

### 网络安全
- [ ] 传输使用 TLS 1.3
- [ ] 弱密码套件已禁用
- [ ] 防火墙规则已配置
- [ ] 限流已启用

### 访问控制
- [ ] 最小权限原则
- [ ] 多因素认证已启用
- [ ] 访问列表已维护
- [ ] 定期审查访问权限

### 监控告警
- [ ] 异常登录告警
- [ ] 密钥访问告警
- [ ] 失败认证告警
- [ ] 泄露检测告警

---

## 合规性

### 数据保护
- [ ] 符合 GDPR (如适用)
- [ ] 符合 CCPA (如适用)
- [ ] 符合 SOC 2 (如适用)
- [ ] 符合 PCI DSS (如适用)

### 审计就绪
- [ ] 审计日志完整保留
- [ ] 日志格式标准化
- [ ] 日志不可篡改 (签名/WORM)
- [ ] 审计报告可生成

---

## 快速检查脚本

```python
#!/usr/bin/env python3
"""
安全检查快速脚本
"""

import os
import sys
import resource
from pathlib import Path

def check_environment():
    """检查环境配置"""
    issues = []

    # 检查敏感环境变量
    sensitive_patterns = ["KEY", "SECRET", "TOKEN", "PASSWORD"]
    for key in os.environ:
        if any(p in key.upper() for p in sensitive_patterns):
            issues.append(f"发现可能敏感的环境变量: {key}")

    # 检查 core limit
    soft, hard = resource.getrlimit(resource.RLIMIT_CORE)
    if soft != 0:
        issues.append(f"Core dump 未禁用 (soft={soft})")

    # 检查文件权限
    vault_files = list(Path(".").glob("*.enc"))
    for f in vault_files:
        stat = f.stat()
        mode = oct(stat.st_mode)[-3:]
        if mode != "600":
            issues.append(f"密钥文件权限不安全: {f} ({mode})")

    return issues


def check_dependencies():
    """检查依赖安全"""
    issues = []

    # 检查是否有 pip-audit
    try:
        import subprocess
        result = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            issues.append("存在已知漏洞，请运行 pip-audit 查看详情")
    except FileNotFoundError:
        issues.append("pip-audit 未安装，无法检查漏洞")

    return issues


def main():
    print("🔒 Agent 配置安全检查\n")

    env_issues = check_environment()
    if env_issues:
        print("❌ 环境配置问题:")
        for issue in env_issues:
            print(f"   - {issue}")
    else:
        print("✅ 环境配置正常")

    dep_issues = check_dependencies()
    if dep_issues:
        print("\n❌ 依赖问题:")
        for issue in dep_issues:
            print(f"   - {issue}")
    else:
        print("✅ 依赖检查正常")

    if not env_issues and not dep_issues:
        print("\n✅ 所有检查通过")
        return 0
    else:
        print(f"\n⚠️  发现 {len(env_issues) + len(dep_issues)} 个问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## 持续监控

### 每日检查
```bash
# 运行安全检查
python security_check.py

# 扫描漏洞
pip-audit

# 检查日志中的敏感信息
grep -i -E "(password|secret|token|key)" /var/log/agent/*.log | audit_leak.py
```

### 每周检查
- 审查审计日志异常
- 检查访问权限变化
- 更新依赖版本

### 每月检查
- 轮换主密钥
- 审查和更新威胁模型
- 渗透测试
