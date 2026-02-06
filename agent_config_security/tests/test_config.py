"""
配置安全管理测试套件
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.crypto import (
    CryptoManager,
    SecureBytes,
    generate_master_key,
    EncryptionError,
)
from config.vault import (
    EnvVault,
    FileVault,
    SecretEntry,
    VaultError,
)
from config.loader import (
    SecureConfigLoader,
    ConfigSource,
    ConfigEntry,
    ConfigValidationError,
)
from config.injector import (
    SandboxInjector,
    TemporaryCredential,
    InjectionScope,
)
from security.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
)
from security.sanitizer import (
    LogSanitizer,
    MaskStrategy,
    sanitize_dict,
    sanitize_string,
)
from security.memory import (
    ProtectedString,
    MemoryGuard,
    secure_zero,
)
from security.credential import (
    SecurityCredentialManager,
    CredentialStatus,
)


class TestCryptoManager:
    """测试加密管理器"""

    def test_generate_master_key(self):
        """测试主密钥生成"""
        key = generate_master_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_encrypt_decrypt_string(self):
        """测试字符串加密解密"""
        crypto = CryptoManager(master_key=generate_master_key())

        plaintext = "This is a secret message"
        encrypted = crypto.encrypt_string(plaintext)
        decrypted = crypto.decrypt_string(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_with_associated_data(self):
        """测试带附加数据的加密"""
        crypto = CryptoManager(master_key=generate_master_key())

        plaintext = b"secret data"
        ad = b"additional authenticated data"

        encrypted = crypto.encrypt(plaintext, ad)
        decrypted = crypto.decrypt(encrypted, ad)

        assert decrypted == plaintext

    def test_decrypt_with_wrong_ad_fails(self):
        """测试错误的附加数据会导致解密失败"""
        crypto = CryptoManager(master_key=generate_master_key())

        plaintext = b"secret data"
        ad = b"correct data"

        encrypted = crypto.encrypt(plaintext, ad)

        with pytest.raises(EncryptionError):
            crypto.decrypt(encrypted, b"wrong data")

    def test_constant_time_compare(self):
        """测试常量时间比较"""
        crypto = CryptoManager(master_key=generate_master_key())

        a = b"same_value"
        b = b"same_value"
        c = b"different_value"

        assert crypto.constant_time_compare(a, b) is True
        assert crypto.constant_time_compare(a, c) is False


class TestSecureBytes:
    """测试安全字节容器"""

    def test_secure_bytes_creation(self):
        """测试创建安全字节"""
        data = os.urandom(16)
        secure = SecureBytes(data)

        assert secure.bytes == data
        assert len(secure) == 16

    def test_secure_bytes_zero(self):
        """测试安全清零"""
        data = b"secret data here"
        secure = SecureBytes(data)

        secure.zero()
        assert secure.bytes == b"\x00" * len(data)

    def test_secure_bytes_not_picklable(self):
        """测试安全字节不可序列化"""
        import pickle

        secure = SecureBytes(b"secret")

        with pytest.raises(TypeError):
            pickle.dumps(secure)


class TestEnvVault:
    """测试环境变量 Vault"""

    def test_get_secret(self):
        """测试获取密钥"""
        os.environ["TEST_API_KEY"] = "sk-test123"

        vault = EnvVault(prefix="TEST_")
        secret = vault.get_secret("api_key")

        assert secret.name == "api_key"
        assert secret.value == "sk-test123"

        del os.environ["TEST_API_KEY"]

    def test_get_missing_secret_raises(self):
        """测试获取不存在的密钥会抛出异常"""
        vault = EnvVault()

        with pytest.raises(VaultError):
            vault.get_secret("nonexistent")


class TestFileVault:
    """测试文件 Vault"""

    def test_save_and_load_secret(self):
        """测试保存和加载密钥"""
        with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as f:
            vault_path = f.name

        try:
            crypto = CryptoManager(master_key=generate_master_key())
            vault = FileVault(vault_path, crypto)

            # 保存密钥
            vault.set_secret("test_key", "test_value")

            # 加载密钥
            secret = vault.get_secret("test_key")

            assert secret.value == "test_value"

        finally:
            Path(vault_path).unlink(missing_ok=True)


class TestSandboxInjector:
    """测试沙箱注入器"""

    def test_create_credential(self):
        """测试创建临时凭证"""
        injector = SandboxInjector()

        cred = injector.create_credential(
            name="test_credential",
            value="secret_value",
            ttl_seconds=60,
        )

        assert cred.name == "test_credential"
        assert cred.value == "secret_value"
        assert cred.is_valid is True

    def test_inject_to_environment(self):
        """测试注入到环境变量"""
        injector = SandboxInjector()

        cred = injector.create_credential(
            name="test_key",
            value="secret_value",
            ttl_seconds=60,
        )

        result = injector.inject(cred.id)

        assert result.success is True
        assert result.environment_key in os.environ
        assert os.environ[result.environment_key] == "secret_value"

        # 清理
        injector.cleanup(result.environment_key)

    def test_context_manager_cleanup(self):
        """测试上下文管理器自动清理"""
        injector = SandboxInjector()
        env_key = "AGENT_TEMP_TEST_KEY"

        with injector.inject_context(
            name="TEST_KEY",
            value="secret_value",
            env_key=env_key,
        ):
            assert env_key in os.environ
            assert os.environ[env_key] == "secret_value"

        # 退出后应自动清理
        assert env_key not in os.environ

    def test_expired_credential_invalid(self):
        """测试过期凭证无效"""
        injector = SandboxInjector()

        cred = injector.create_credential(
            name="test",
            value="value",
            ttl_seconds=-1,  # 已过期
        )

        assert cred.is_valid is False
        assert cred.is_expired is True


class TestAuditLogger:
    """测试审计日志"""

    def test_log_event(self):
        """测试记录事件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_file = f.name

        try:
            audit = AuditLogger(log_file=log_file)

            audit.log(
                event_type=AuditEventType.SECRET_READ,
                resource="test_secret",
                action="read",
            )

            audit.flush()

            # 读取日志
            events = audit.query(
                event_type=AuditEventType.SECRET_READ,
                limit=10,
            )

            assert len(events) == 1
            assert events[0].resource == "test_secret"

        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_event_signature(self):
        """测试事件签名"""
        key = b"test_signing_key_32_bytes_long!!!!"

        event = AuditEvent(
            event_type=AuditEventType.SECRET_READ,
            resource="test",
        )

        event.sign(key)

        assert event.signature is not None
        assert event.verify(key) is True
        assert event.verify(b"wrong_key") is False


class TestLogSanitizer:
    """测试日志脱敏器"""

    def test_sanitize_api_key(self):
        """测试 API Key 脱敏"""
        sanitizer = LogSanitizer()

        text = "API key: sk-abcdefghijklmnopqrstuvwxyz123456"
        result = sanitizer.sanitize_string(text)

        assert "sk-" in result
        assert "abcdefghijklmnopqrstuvwxyz" not in result
        assert "***" in result

    def test_sanitize_dict(self):
        """测试字典脱敏"""
        sanitizer = LogSanitizer()

        data = {
            "username": "alice",
            "password": "secret123",
            "api_key": "sk-test123456",
        }

        result = sanitizer.sanitize_dict(data)

        assert result["username"] == "alice"
        assert result["password"] == "***"
        assert "***" in result["api_key"]

    def test_sanitize_jwt(self):
        """测试 JWT 脱敏"""
        sanitizer = LogSanitizer()

        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature"
        result = sanitizer.sanitize_string(jwt)

        # JWT 应该被部分隐藏
        assert "***" in result or result != jwt


class TestProtectedString:
    """测试受保护字符串"""

    def test_protected_string_repr(self):
        """测试字符串表示不泄露内容"""
        protected = ProtectedString("secret_value")

        assert "secret_value" not in repr(protected)
        assert "***PROTECTED***" in str(protected)

    def test_protected_string_value_access(self):
        """测试可以访问实际值"""
        protected = ProtectedString("secret_value")

        assert protected.value == "secret_value"

    def test_protected_string_zero(self):
        """测试清零"""
        protected = ProtectedString("secret_value")
        protected.zero()

        # 值应被清空
        assert protected.value == "\x00" * len("secret_value")


class TestMemoryGuard:
    """测试内存保护"""

    def test_context_manager_cleanup(self):
        """测试上下文管理器"""
        guard = MemoryGuard()

        with guard:
            secret = guard.protect("my_secret")
            assert secret.value == "my_secret"

        # 退出后应被清零
        assert secret.value == "\x00" * len("my_secret")


class TestSecurityCredentialManager:
    """测试凭证安全管理器"""

    def test_register_and_verify(self):
        """测试注册和验证凭证"""
        manager = SecurityCredentialManager()

        cred_id = manager.register_credential(
            name="test_api_key",
            value="sk-test123",
        )

        assert manager.verify_credential(cred_id, "sk-test123") is True
        assert manager.verify_credential(cred_id, "wrong") is False

    def test_revoke_credential(self):
        """测试撤销凭证"""
        manager = SecurityCredentialManager()

        cred_id = manager.register_credential(
            name="test",
            value="secret",
        )

        manager.revoke_credential(cred_id)

        # 撤销后应无效
        assert manager.verify_credential(cred_id, "secret") is False

    def test_expired_credential(self):
        """测试过期凭证"""
        manager = SecurityCredentialManager()

        cred_id = manager.register_credential(
            name="test",
            value="secret",
            expires_in=1,  # 1 秒后过期
        )

        assert manager.verify_credential(cred_id, "secret") is True

        import time
        time.sleep(1.1)

        # 过期后应无效
        assert manager.verify_credential(cred_id, "secret") is False


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
