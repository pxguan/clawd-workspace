#!/usr/bin/env python3
"""
配置安全检查脚本

运行此脚本以检查当前环境和配置的安全状态。
"""

import os
import sys
import re
from pathlib import Path


def check_environment_variables():
    """检查环境变量中的敏感信息"""
    issues = []
    passed = []

    sensitive_patterns = [
        "KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL",
        "API_KEY", "PRIVATE_KEY", "AUTH", "ACCESS_KEY"
    ]

    found_sensitive = []
    for key in os.environ:
        if any(p in key.upper() for p in sensitive_patterns):
            # 检查是否使用安全前缀 (表示已管理)
            if not key.startswith("AGENT_TEMP_"):
                found_sensitive.append(key)

    if found_sensitive:
        issues.append(f"发现 {len(found_sensitive)} 个可能敏感的环境变量")
        for key in found_sensitive[:5]:  # 只显示前5个
            issues.append(f"  - {key}")
        if len(found_sensitive) > 5:
            issues.append(f"  - ... 还有 {len(found_sensitive) - 5} 个")
    else:
        passed.append("✅ 环境变量检查通过")

    return issues, passed


def check_file_permissions():
    """检查敏感文件权限"""
    issues = []
    passed = []

    sensitive_extensions = [".enc", ".key", ".pem", ".p12", ".jks"]
    current_dir = Path.cwd()

    for ext in sensitive_extensions:
        for file in current_dir.rglob(f"*{ext}"):
            stat = file.stat()
            mode = oct(stat.st_mode)[-3:]

            # 检查是否可被组或其他用户读取
            if mode[1] != "0" or mode[2] != "0":
                issues.append(f"文件权限不安全: {file} ({mode})")
            else:
                passed.append(f"✅ 文件权限安全: {file}")

    return issues, passed


def check_git_secrets():
    """检查 git 历史中是否有泄露的密钥"""
    issues = []
    passed = []

    if not (Path.cwd() / ".git").exists():
        return issues, passed

    # 检查常见的密钥模式
    patterns = [
        r"sk-[a-zA-Z0-9]{32,}",  # OpenAI API key
        r"AKIA[0-9A-Z]{16}",  # AWS key
        r"password\s*=\s*['\"][^'\"]{8,}['\"]",  # 密码
        r"api[_-]?key\s*=\s*['\"][^'\"]{20,}['\"]",  # API key
    ]

    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", "--all", "--full-history", "-p"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            for pattern in patterns:
                matches = re.findall(pattern, result.stdout, re.IGNORECASE)
                if matches:
                    issues.append(f"Git 历史中可能包含敏感信息 (匹配: {len(matches)})")
                    break
            else:
                passed.append("✅ Git 历史检查通过")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # Git 检查可选

    return issues, passed


def check_dependencies():
    """检查依赖安全性"""
    issues = []
    passed = []

    # 检查是否有 pip-audit
    try:
        import subprocess
        result = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            try:
                import json
                data = json.loads(result.stdout)
                vulns = data.get("dependencies", [])
                if vulns:
                    issues.append(f"发现 {len(vulns)} 个已知漏洞")
                else:
                    passed.append("✅ 依赖漏洞检查通过")
            except (json.JSONDecodeError, KeyError):
                issues.append("无法解析 pip-audit 输出")
        else:
            passed.append("✅ 依赖漏洞检查通过")
    except FileNotFoundError:
        issues.append("pip-audit 未安装，无法检查依赖漏洞")

    return issues, passed


def check_core_dumps():
    """检查 core dump 设置"""
    issues = []
    passed = []

    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_CORE)

        if soft != 0:
            issues.append(f"Core dump 未禁用 (soft limit: {soft})")
        else:
            passed.append("✅ Core dump 已禁用")
    except Exception:
        pass Unix systems only

    return issues, passed


def check_swappiness():
    """检查 swap 设置 (Unix)"""
    issues = []
    passed = []

    try:
        with open("/proc/sys/vm/swappiness", "r") as f:
            swappiness = int(f.read().strip())

        if swappiness > 10:
            issues.append(f"Swappiness 较高 ({swappiness})，可能影响内存安全")
        else:
            passed.append("✅ Swappiness 设置合理")
    except (FileNotFoundError, ValueError, PermissionError):
        pass

    return issues, passed


def main():
    print("🔒 Agent 配置安全检查")
    print("=" * 50)

    all_issues = []
    all_passed = []

    checks = [
        ("环境变量", check_environment_variables),
        ("文件权限", check_file_permissions),
        ("Git 历史", check_git_secrets),
        ("依赖漏洞", check_dependencies),
        ("Core Dump", check_core_dumps),
        ("Swap 设置", check_swappiness),
    ]

    for name, check_func in checks:
        issues, passed = check_func()
        all_issues.extend(issues)
        all_passed.extend(passed)

        if issues:
            print(f"\n❌ {name}:")
            for issue in issues:
                print(f"   {issue}")

    if all_passed:
        print(f"\n通过:")
        for item in all_passed[:5]:  # 只显示前5个
            print(f"   {item}")
        if len(all_passed) > 5:
            print(f"   ... 还有 {len(all_passed) - 5} 项通过")

    print("\n" + "=" * 50)

    if all_issues:
        print(f"⚠️  发现 {len(all_issues)} 个问题需要处理")
        return 1
    else:
        print("✅ 所有检查通过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
