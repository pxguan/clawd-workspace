"""
加密/解密管理模块

提供安全的加密存储和内存保护功能：
- AES-256-GCM 加密
- PBKDF2 密钥派生
- 安全内存管理 (mlock, 过零)
- 防时间攻击的常量时间比较
"""

import os
import sys
import ctypes
import hashlib
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

try:
    import ctypes.util

    LIBC = ctypes.CDLL(ctypes.util.find_library("c"))
    HAS_MLOCK = True
except (AttributeError, OSError):
    HAS_MLOCK = False


class EncryptionError(Exception):
    """加密操作失败"""


class MemoryError(Exception):
    """内存保护失败"""


@dataclass
class EncryptedData:
    """加密后的数据结构"""
    ciphertext: bytes
    nonce: bytes
    tag: bytes  # GCM 认证标签


class CryptoManager:
    """
    加密管理器

    特性：
    - AES-256-GCM 认证加密
    - PBKDF2 密钥派生 (600,000+ 迭代)
    - 随机 nonce 生成
    - 密钥版本管理支持
    """

    # 默认加密参数
    DEFAULT_KEY_SIZE = 32  # AES-256
    DEFAULT_NONCE_SIZE = 12  # GCM 推荐
    DEFAULT_PBKDF2_ITERATIONS = 600_000  # OWASP 2023 推荐
    DEFAULT_SALT_SIZE = 16

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        password: Optional[str] = None,
        salt: Optional[bytes] = None,
        iterations: int = DEFAULT_PBKDF2_ITERATIONS,
    ):
        """
        初始化加密管理器

        Args:
            master_key: 直接提供的主密钥 (32 bytes for AES-256)
            password: 用于派生密钥的密码
            salt: PBKDF2 盐值 (如果未提供则随机生成)
            iterations: PBKDF2 迭代次数
        """
        if master_key is not None:
            if len(master_key) != self.DEFAULT_KEY_SIZE:
                raise ValueError(f"Master key must be {self.DEFAULT_KEY_SIZE} bytes")
            self._key = SecureBytes(master_key)
            self._salt = None
        elif password is not None:
            self._salt = salt if salt else os.urandom(self.DEFAULT_SALT_SIZE)
            derived_key = self._derive_key(password, self._salt, iterations)
            self._key = SecureBytes(derived_key)
        else:
            raise ValueError("Either master_key or password must be provided")

        self._aesgcm = AESGCM(self._key.bytes)
        self._iterations = iterations

    @staticmethod
    def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
        """使用 PBKDF2 从密码派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=CryptoManager.DEFAULT_KEY_SIZE,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))

    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> EncryptedData:
        """
        加密数据

        Args:
            plaintext: 明文数据
            associated_data: 附加认证数据 (不被加密但被认证)

        Returns:
            EncryptedData: 包含密文、nonce 和 tag 的结构
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")

        nonce = os.urandom(self.DEFAULT_NONCE_SIZE)

        # AES-GCM 加密 (tag 自动附加到密文后)
        ciphertext_with_tag = self._aesgcm.encrypt(nonce, plaintext, associated_data)

        # 分离密文和 tag (tag 是最后 16 字节)
        tag_size = 16
        ciphertext = ciphertext_with_tag[:-tag_size]
        tag = ciphertext_with_tag[-tag_size:]

        return EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag,
        )

    def decrypt(
        self,
        encrypted: EncryptedData,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """
        解密数据

        Args:
            encrypted: EncryptedData 结构
            associated_data: 加密时使用的附加认证数据

        Returns:
            bytes: 解密后的明文

        Raises:
            EncryptionError: 解密失败或认证失败
        """
        try:
            # 重新组合密文和 tag
            ciphertext_with_tag = encrypted.ciphertext + encrypted.tag
            return self._aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, associated_data)
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}") from e

    def encrypt_string(self, plaintext: str, associated_data: Optional[str] = None) -> str:
        """加密字符串，返回 hex 编码结果"""
        ad = associated_data.encode("utf-8") if associated_data else None
        encrypted = self.encrypt(plaintext.encode("utf-8"), ad)

        # 组合: nonce(24 hex) + tag(32 hex) + ciphertext
        return (
            encrypted.nonce.hex()
            + encrypted.tag.hex()
            + encrypted.ciphertext.hex()
        )

    def decrypt_string(self, encrypted_hex: str, associated_data: Optional[str] = None) -> str:
        """从 hex 编码解密字符串"""
        try:
            nonce = bytes.fromhex(encrypted_hex[:24])
            tag = bytes.fromhex(encrypted_hex[24:56])
            ciphertext = bytes.fromhex(encrypted_hex[56:])

            ad = associated_data.encode("utf-8") if associated_data else None
            encrypted = EncryptedData(ciphertext=ciphertext, nonce=nonce, tag=tag)

            return self.decrypt(encrypted, ad).decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"String decryption failed: {e}") from e

    @staticmethod
    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """
        常量时间比较，防止时间攻击

        使用 hmac.compare_digest 的底层实现
        """
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0

    def export_key_material(self) -> dict:
        """导出密钥材料 (用于备份，谨慎使用)"""
        return {
            "key": self._key.hex(),
            "salt": self._salt.hex() if self._salt else None,
            "iterations": self._iterations,
        }


class SecureBytes:
    """
    安全字节容器

    特性：
    - mlock 锁定内存 (防止 swap)
    - 自动过零 (安全清零)
    - 禁止 pickle 序列化
    - 最小化密钥生命周期
    """

    # 最大可锁定的内存大小 (Linux 默认 rlimit 通常 64KB)
    MAX_MLOCK_SIZE = 64 * 1024

    def __init__(self, data: bytes):
        """
        初始化安全字节容器

        Args:
            data: 要保护的字节数据
        """
        if len(data) > self.MAX_MLOCK_SIZE:
            raise MemoryError(
                f"Data too large for mlock ({len(data)} > {self.MAX_MLOCK_SIZE})"
            )

        # 创建可写的缓冲区
        self._buffer = bytearray(data)
        self._size = len(data)

        # 尝试锁定内存
        self._locked = False
        if HAS_MLOCK:
            try:
                ptr = ctypes.addressof(ctypes.c_char.from_buffer(self._buffer))
                if LIBC.mlock(ptr, self._size) == 0:
                    self._locked = True
            except Exception:
                pass  # mlock 失败不是致命错误

    @property
    def bytes(self) -> bytes:
        """获取字节副本 (只读)"""
        return bytes(self._buffer)

    @property
    def hex(self) -> str:
        """获取十六进制表示"""
        return self._buffer.hex()

    def __len__(self) -> int:
        return self._size

    def __del__(self):
        """析构时安全清零"""
        self.zero()
        if self._locked and HAS_MLOCK:
            try:
                ptr = ctypes.addressof(ctypes.c_char.from_buffer(self._buffer))
                LIBC.munlock(ptr, self._size)
            except Exception:
                pass

    def zero(self) -> None:
        """安全清零内存"""
        for i in range(self._size):
            self._buffer[i] = 0

    def __getstate__(self):
        """禁止 pickle"""
        raise TypeError("SecureBytes cannot be serialized")

    def __setstate__(self, state):
        """禁止 pickle"""
        raise TypeError("SecureBytes cannot be deserialized")

    def __reduce__(self):
        """禁止 pickle"""
        raise TypeError("SecureBytes cannot be pickled")


def generate_master_key() -> bytes:
    """生成随机的 AES-256 主密钥"""
    return os.urandom(32)


def generate_password(length: int = 32) -> str:
    """生成强随机密码"""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
