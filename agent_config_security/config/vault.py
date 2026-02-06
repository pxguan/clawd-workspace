"""
密钥存储后端模块

支持多种密钥源：
- 环境变量 (最基础，适合本地开发)
- 加密文件 (适合简单部署)
- 云 KMS (AWS Secrets Manager, Azure Key Vault)
- HashiCorp Vault
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SecretEntry:
    """密钥条目"""
    name: str
    value: str
    version: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class VaultError(Exception):
    """Vault 操作失败"""


class VaultBackend(ABC):
    """密钥存储后端抽象基类"""

    @abstractmethod
    def get_secret(self, name: str, version: Optional[int] = None) -> SecretEntry:
        """获取密钥"""

    @abstractmethod
    def list_secrets(self) -> list[str]:
        """列出所有密钥名称"""

    @abstractmethod
    def set_secret(self, name: str, value: str, **kwargs) -> SecretEntry:
        """存储密钥"""

    @abstractmethod
    def delete_secret(self, name: str) -> bool:
        """删除密钥"""

    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.list_secrets()
            return True
        except Exception:
            return False


class EnvVault(VaultBackend):
    """
    环境变量密钥后端

    特性：
    - 简单、无依赖
    - 自动前缀支持
    - 适合容器化部署
    """

    def __init__(self, prefix: str = ""):
        """
        Args:
            prefix: 环境变量前缀，如 "AGENT_" 则读取 AGENT_API_KEY
        """
        self.prefix = prefix.upper()
        self._case_sensitive = False

    def get_secret(self, name: str, version: Optional[int] = None) -> SecretEntry:
        env_key = self._make_key(name)
        value = os.environ.get(env_key)

        if value is None:
            raise VaultError(f"Secret not found: {name} (env: {env_key})")

        return SecretEntry(
            name=name,
            value=value,
            version=version or 1,
        )

    def list_secrets(self) -> list[str]:
        prefix_len = len(self.prefix)
        return [
            key[prefix_len:].lower()
            for key in os.environ.keys()
            if key.upper().startswith(self.prefix)
        ]

    def set_secret(self, name: str, value: str, **kwargs) -> SecretEntry:
        """环境变量是只读的，此方法仅用于测试"""
        env_key = self._make_key(name)
        os.environ[env_key] = value
        return SecretEntry(name=name, value=value)

    def delete_secret(self, name: str) -> bool:
        """环境变量是只读的"""
        env_key = self._make_key(name)
        if env_key in os.environ:
            del os.environ[env_key]
            return True
        return False

    def _make_key(self, name: str) -> str:
        """构造环境变量键名"""
        if self._case_sensitive:
            return f"{self.prefix}{name}"
        return f"{self.prefix}{name}".upper()


class FileVault(VaultBackend):
    """
    加密文件密钥后端

    特性：
    - 文件级加密 (需要 CryptoManager)
    - JSON 格式存储
    - 版本控制支持
    """

    def __init__(self, file_path: str | Path, crypto_manager):
        """
        Args:
            file_path: 密钥文件路径
            crypto_manager: CryptoManager 实例用于加密/解密
        """
        self.file_path = Path(file_path)
        self.crypto = crypto_manager
        self._cache: Optional[Dict[str, Any]] = None

        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        """加载并解密密钥文件"""
        if self._cache is not None:
            return self._cache

        if not self.file_path.exists():
            self._cache = {}
            return self._cache

        try:
            encrypted_data = self.file_path.read_bytes()
            decrypted_json = self.crypto.decrypt(
                type("Encrypted", (), {
                    "ciphertext": bytes.fromhex(encrypted_data.decode().split(":")[1]),
                    "nonce": bytes.fromhex(encrypted_data.decode().split(":")[0][:24]),
                    "tag": bytes.fromhex(encrypted_data.decode().split(":")[0][24:56])
                })()
            )
            self._cache = json.loads(decrypted_json.decode())
            return self._cache
        except Exception as e:
            raise VaultError(f"Failed to load vault: {e}")

    def _save(self, data: Dict[str, Any]) -> None:
        """加密并保存密钥文件"""
        try:
            json_data = json.dumps(data, indent=2, default=str).encode()
            encrypted = self.crypto.encrypt(json_data)

            # 格式: nonce:tag:ciphertext
            output = f"{encrypted.nonce.hex()}:{encrypted.tag.hex()}:{encrypted.ciphertext.hex()}"
            self.file_path.write_text(output)
            self._cache = data
        except Exception as e:
            raise VaultError(f"Failed to save vault: {e}")

    def get_secret(self, name: str, version: Optional[int] = None) -> SecretEntry:
        data = self._load()
        if name not in data:
            raise VaultError(f"Secret not found: {name}")

        entry = data[name]
        if isinstance(entry, list):
            # 版本化存储
            idx = (version or len(entry)) - 1
            if idx < 0 or idx >= len(entry):
                raise VaultError(f"Version {version} not found for {name}")
            entry = entry[idx]

        return SecretEntry(
            name=name,
            value=entry["value"],
            version=entry.get("version"),
            created_at=datetime.fromisoformat(entry["created_at"]) if entry.get("created_at") else None,
        )

    def list_secrets(self) -> list[str]:
        return list(self._load().keys())

    def set_secret(self, name: str, value: str, **kwargs) -> SecretEntry:
        data = self._load()

        entry = {
            "value": value,
            "created_at": datetime.utcnow().isoformat(),
            "version": kwargs.get("version", 1),
        }

        if kwargs.get("versioned", False):
            if name not in data:
                data[name] = []
            data[name].append(entry)
        else:
            data[name] = entry

        self._save(data)
        return SecretEntry(name=name, value=value)

    def delete_secret(self, name: str) -> bool:
        data = self._load()
        if name in data:
            del data[name]
            self._save(data)
            return True
        return False


class KmsVault(VaultBackend):
    """
    云 KMS 后端

    支持：
    - AWS Secrets Manager
    - Azure Key Vault
    - Google Secret Manager (通过统一接口)
    """

    def __init__(
        self,
        provider: str,
        region: Optional[str] = None,
        credential_path: Optional[str] = None,
    ):
        """
        Args:
            provider: "aws", "azure", "gcp"
            region: 云区域
            credential_path: 凭证文件路径
        """
        self.provider = provider.lower()
        self.region = region
        self.credential_path = credential_path
        self._client = None

        self._init_client()

    def _init_client(self) -> None:
        """初始化云 SDK 客户端"""
        if self.provider == "aws":
            try:
                import boto3

                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self.region or os.getenv("AWS_REGION", "us-east-1"),
                )
            except ImportError:
                raise VaultError("boto3 required for AWS KMS")
        elif self.provider == "azure":
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient

                credential = DefaultAzureCredential()
                vault_url = os.getenv("AZURE_KEYVAULT_URL")
                if not vault_url:
                    raise VaultError("AZURE_KEYVAULT_URL required")

                self._client = SecretClient(
                    vault_url=vault_url,
                    credential=credential,
                )
            except ImportError:
                raise VaultError("azure-identity and azure-keyvault-secrets required")
        elif self.provider == "gcp":
            try:
                from google.cloud import secretmanager

                self._client = secretmanager.SecretManagerServiceClient()
            except ImportError:
                raise VaultError("google-cloud-secret-manager required")
        else:
            raise VaultError(f"Unsupported provider: {self.provider}")

    def get_secret(self, name: str, version: Optional[int] = None) -> SecretEntry:
        if self.provider == "aws":
            response = self._client.get_secret_value(SecretId=name)
            value = response.get("SecretString") or response.get("SecretBinary")
            return SecretEntry(name=name, value=value)

        elif self.provider == "azure":
            secret = self._client.get_secret(name, version=version or "")
            return SecretEntry(name=name, value=secret.value)

        elif self.provider == "gcp":
            # GCP 格式: projects/*/secrets/*/versions/*
            if not name.startswith("projects/"):
                name = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/secrets/{name}/versions/{version or 'latest'}"
            response = self._client.access_secret_version(name=name)
            return SecretEntry(name=name, value=response.payload.data.decode())

        raise VaultError(f"Get secret not implemented for {self.provider}")

    def list_secrets(self) -> list[str]:
        if self.provider == "aws":
            response = self._client.list_secrets()
            return [s["Name"] for s in response.get("SecretList", [])]

        elif self.provider == "azure":
            secrets = self._client.list_properties_of_secrets()
            return [s.name for s in secrets]

        elif self.provider == "gcp":
            parent = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}"
            response = self._client.list_secrets(parent=parent)
            return [s.name.split("/")[-1] for s in response]

        return []

    def set_secret(self, name: str, value: str, **kwargs) -> SecretEntry:
        if self.provider == "aws":
            self._client.create_secret(
                Name=name,
                SecretString=value,
                Description=kwargs.get("description", ""),
            )
            return SecretEntry(name=name, value=value)

        elif self.provider == "azure":
            self._client.set_secret(name, value)
            return SecretEntry(name=name, value=value)

        elif self.provider == "gcp":
            parent = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}"
            self._client.create_secret(
                parent=parent,
                secret_id=name,
                secret={"replication": {"automatic": {}}},
            )
            return SecretEntry(name=name, value=value)

        raise VaultError(f"Set secret not implemented for {self.provider}")

    def delete_secret(self, name: str) -> bool:
        if self.provider == "aws":
            self._client.delete_secret(SecretId=name, ForceDeleteWithoutRecovery=True)
            return True
        elif self.provider == "azure":
            self._client.begin_delete_secret(name)
            return True
        elif self.provider == "gcp":
            self._client.delete_secret(name=name)
            return True
        return False


def create_vault_from_uri(uri: str, **kwargs) -> VaultBackend:
    """
    从 URI 创建 Vault 后端

    URI 格式:
    - env://[prefix]
    - file://path/to/vault.enc
    - aws://region/name
    - azure://vault-name
    - gcp://project-id
    """
    if uri.startswith("env://"):
        prefix = uri[6:] or "AGENT_"
        return EnvVault(prefix=prefix)

    elif uri.startswith("file://"):
        from .crypto import CryptoManager

        crypto = kwargs.get("crypto_manager")
        if not crypto:
            raise VaultError("crypto_manager required for file vault")
        return FileVault(uri[7:], crypto)

    elif uri.startswith("aws://"):
        parts = uri[6:].split("/")
        region = parts[0] if parts else None
        return KmsVault("aws", region=region, **kwargs)

    elif uri.startswith("azure://"):
        return KmsVault("azure", **kwargs)

    elif uri.startswith("gcp://"):
        return KmsVault("gcp", region=uri[6:], **kwargs)

    else:
        raise VaultError(f"Unknown vault URI scheme: {uri}")
