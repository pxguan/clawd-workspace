#!/usr/bin/env python3
"""
完整的配置安全使用示例

演示如何使用配置安全管理方案的各个组件。
"""

import os
import sys
import logging

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

from config import (
    SecureConfigLoader,
    CryptoManager,
    SandboxInjector,
)
from security import (
    AuditLogger,
    LogSanitizer,
    setup_logging_with_sanitization,
)
from config.loader import DatabaseConfig, ApiConfig, AgentConfig


def main():
    # ============================================================
    # 1. 设置日志系统 (带脱敏)
    # ============================================================
    setup_logging_with_sanitization(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("🚀 Agent 配置安全系统启动")

    # ============================================================
    # 2. 初始化审计日志
    # ============================================================
    audit_logger = AuditLogger(
        log_file="audit/agent_audit.log",
        signing_key=os.urandom(32),  # 生产环境应从安全位置加载
    )

    logger.info("📋 审计日志已初始化")

    # ============================================================
    # 3. 初始化加密管理器
    # ============================================================
    # 从环境变量获取主密钥 (生产环境应从 KMS 获取)
    master_key_hex = os.getenv("AGENT_MASTER_KEY")
    if master_key_hex:
        master_key = bytes.fromhex(master_key_hex)
    else:
        # 开发环境：生成临时密钥
        master_key = os.urandom(32)
        logger.warning("⚠️  使用临时主密钥，生产环境请设置 AGENT_MASTER_KEY")

    crypto = CryptoManager(master_key=master_key)
    logger.info("🔐 加密管理器已初始化")

    # ============================================================
    # 4. 初始化配置加载器
    # ============================================================
    config = SecureConfigLoader(
        vault_uri="env://AGENT_",
        encryption_key=master_key,
        audit_logger=audit_logger,
        cache_ttl_seconds=300,
    )

    # 添加配置文件
    config.add_config_file(".env")
    config.add_config_file("config/agent.json")

    logger.info("⚙️  配置加载器已初始化")

    # ============================================================
    # 5. 加载配置 (使用 Pydantic 模型)
    # ============================================================
    try:
        # 假设环境变量已设置
        os.environ["AGENT_DATABASE_HOST"] = "localhost"
        os.environ["AGENT_DATABASE_PORT"] = "5432"
        os.environ["AGENT_DATABASE_USERNAME"] = "agent_user"
        os.environ["AGENT_DATABASE_PASSWORD"] = "super_secret_password_123"
        os.environ["AGENT_DATABASE_DATABASE"] = "agent_db"
        os.environ["AGENT_API_BASE_URL"] = "https://api.example.com"
        os.environ["AGENT_API_API_KEY"] = "sk-1234567890abcdefghijklmnopqrstuvwxyz"

        # 加载配置
        agent_config = config.load_model(AgentConfig)

        logger.info("✅ 配置加载成功")
        logger.info(f"数据库: {agent_config.database.host}:{agent_config.database.port}")
        logger.info(f"API: {agent_config.api.base_url}")

    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        return 1

    # ============================================================
    # 6. 使用临时凭证访问敏感数据
    # ============================================================
    injector = SandboxInjector(
        prefix="AGENT_TEMP_",
        default_ttl_seconds=60,
        audit_logger=audit_logger,
    )

    # 创建临时凭证
    cred = injector.create_credential(
        name="db_password",
        value=str(agent_config.database.password),
        ttl_seconds=60,
        max_uses=1,
    )

    logger.info(f"🔑 创建临时凭证: {cred.id}")

    # 使用作用域注入 (自动清理)
    with injector.inject_context(
        name="DATABASE_URL",
        value=f"postgresql://{agent_config.database.username}:{agent_config.database.password}@{agent_config.database.host}/{agent_config.database.database}",
        ttl_seconds=60,
    ) as cred:
        logger.info("📦 临时凭证已注入到环境")

        # 在这里执行需要凭证的操作
        # 例如：连接数据库
        # db.connect(os.environ["AGENT_TEMP_DATABASE_URL"])

        logger.info("🔗 使用凭证执行操作...")

    # 自动清理
    logger.info("🧹 临时凭证已清理")

    # ============================================================
    # 7. 演示日志脱敏
    # ============================================================
    logger.info({
        "message": "测试日志脱敏",
        "api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
        "password": "my_secret_password",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    })
    # 上述敏感字段会被自动脱敏

    # ============================================================
    # 8. 演示加密存储
    # ============================================================
    # 加密敏感数据
    plaintext = "This is a secret message"
    encrypted = crypto.encrypt_string(plaintext)
    logger.info(f"🔒 加密数据: {encrypted[:32]}...")

    # 解密
    decrypted = crypto.decrypt_string(encrypted)
    logger.info(f"🔓 解密数据: {decrypted}")

    # ============================================================
    # 9. 安全退出
    # ============================================================
    # 清理所有临时凭证
    count = injector.cleanup_all()
    logger.info(f"🧹 清理了 {count} 个临时凭证")

    # 刷新审计日志
    audit_logger.flush()

    logger.info("✅ Agent 配置安全系统正常退出")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
