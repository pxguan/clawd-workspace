"""
安全配置管理模块

提供完整的配置安全管理方案：
- 外部密钥源集成 (KMS/Vault/环境变量)
- 加密存储和传输
- 内存保护
- 访问控制和审计
"""

from .loader import SecureConfigLoader, ConfigEntry
from .vault import VaultBackend, EnvVault, FileVault, KmsVault
from .crypto import CryptoManager, SecureBytes
from .injector import SandboxInjector

__all__ = [
    "SecureConfigLoader",
    "ConfigEntry",
    "VaultBackend",
    "EnvVault",
    "FileVault",
    "KmsVault",
    "CryptoManager",
    "SecureBytes",
    "SandboxInjector",
]

__version__ = "1.0.0"
