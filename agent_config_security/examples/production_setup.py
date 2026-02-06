#!/usr/bin/env python3
"""
生产环境配置设置脚本

用于初始化和配置生产环境的密钥管理。
"""

import os
import sys
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.crypto import generate_master_key, generate_password, CryptoManager
from config.vault import FileVault


def setup_file_vault():
    """设置文件加密存储"""
    print("=" * 50)
    print("设置文件加密存储")
    print("=" * 50)

    # 生成主密钥
    print("\n🔑 生成主密钥...")
    master_key = generate_master_key()

    print("⚠️  主密钥已生成！请妥善保管：")
    print(f"   {master_key.hex()}")
    print("\n请将此密钥设置为环境变量 AGENT_MASTER_KEY")
    print("或存储在安全的密钥管理服务中 (如 AWS Secrets Manager)")

    # 保存到文件 (仅用于初始化，之后应删除)
    vault_path = Path("secrets/vault.enc")
    vault_path.parent.mkdir(exist_ok=True)

    print(f"\n📁 创建加密存储: {vault_path}")

    # 初始化 CryptoManager
    crypto = CryptoManager(master_key=master_key)

    # 创建 FileVault
    vault = FileVault(vault_path, crypto)

    # 添加示例密钥
    print("\n📝 添加密钥到存储:")

    secrets_to_add = [
        ("openai_api_key", input("OpenAI API Key (可选): ") or "sk-placeholder"),
        ("database_password", getpass.getpass("Database Password: ") or generate_password(32)),
        ("redis_password", getpass.getpass("Redis Password: ") or generate_password(32)),
    ]

    for name, value in secrets_to_add:
        if value:
            vault.set_secret(name, value)
            print(f"   ✅ {name}")

    print(f"\n✅ 密钥已保存到加密存储: {vault_path}")
    print(f"   请设置环境变量: AGENT_VAULT_URI=file://{vault_path.absolute()}")


def setup_aws_secrets_manager():
    """设置 AWS Secrets Manager"""
    print("\n" + "=" * 50)
    print("设置 AWS Secrets Manager")
    print("=" * 50)

    try:
        import boto3
    except ImportError:
        print("❌ boto3 未安装，请运行: pip install boto3")
        return

    print("\n📝 需要存储的密钥:")

    secrets = {
        "agent/openai_api_key": input("OpenAI API Key: "),
        "agent/database_password": getpass.getpass("Database Password: "),
        "agent/redis_password": getpass.getpass("Redis Password: "),
    }

    region = input("AWS Region (default: us-east-1): ") or "us-east-1"

    client = boto3.client("secretsmanager", region_name=region)

    for name, value in secrets.items():
        if value:
            try:
                client.create_secret(
                    Name=name,
                    SecretString=value,
                    Description=f"Agent secret: {name}",
                )
                print(f"   ✅ {name}")
            except client.exceptions.ResourceExistsException:
                client.put_secret_value(SecretId=name, SecretString=value)
                print(f"   ♻️  更新 {name}")
            except Exception as e:
                print(f"   ❌ {name}: {e}")

    print(f"\n✅ 密钥已保存到 AWS Secrets Manager")
    print(f"   请设置环境变量: AGENT_VAULT_URI=aws://{region}")


def setup_audit_key():
    """生成审计签名密钥"""
    print("\n" + "=" * 50)
    print("设置审计签名密钥")
    print("=" * 50)

    import os

    key = os.urandom(32)
    print("\n🔑 审计签名密钥:")
    print(f"   {key.hex()}")
    print("\n请设置为环境变量: AUDIT_SIGNING_KEY")


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Agent 配置安全管理 - 生产环境设置向导               ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)

    print("请选择配置方式:")
    print("  1. 文件加密存储 (适合单机部署)")
    print("  2. AWS Secrets Manager (适合云部署)")
    print("  3. 仅生成密钥")
    print("  4. 全部设置")

    choice = input("\n选择 (1-4): ").strip()

    if choice in ("1", "4"):
        setup_file_vault()

    if choice in ("2", "4"):
        setup_aws_secrets_manager()

    if choice in ("3", "4"):
        setup_audit_key()

    print("\n" + "=" * 50)
    print("✅ 设置完成！")
    print("=" * 50)

    print("\n📝 下一步:")
    print("  1. 设置环境变量 (见上)")
    print("  2. 运行安全检查: python security_check.py")
    print("  3. 启动 Agent: python agent.py")


if __name__ == "__main__":
    main()
