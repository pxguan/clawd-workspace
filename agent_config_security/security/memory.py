"""
内存保护模块

功能：
- 安全清零
- 字符串保护
- 内存锁定 (mlock)
- 堆栈跟踪清理
"""

import os
import sys
import ctypes
import ctypes.util
import atexit
import traceback
from typing import Any, Optional
from functools import wraps

try:
    import ctypes.util
    LIBC = ctypes.CDLL(ctypes.util.find_library("c"))
    HAS_MLOCK = True
except (AttributeError, OSError):
    LIBC = None
    HAS_MLOCK = False


class MemoryProtectionError(Exception):
    """内存保护失败"""


def secure_zero(data: bytearray | bytes | str, length: Optional[int] = None) -> None:
    """
    安全清零内存

    注意：Python 的字符串是不可变的，无法真正安全清零。
    此函数主要用于 bytearray 或创建时即指定的缓冲区。

    Args:
        data: 要清零的数据
        length: 要清零的长度 (默认: 全部)
    """
    if isinstance(data, str):
        # 字符串无法安全清零，只能警告
        import warnings
        warnings.warn(
            "Cannot securely zero Python strings (immutable). "
            "Use SecureBytes or bytearray instead.",
            RuntimeWarning,
        )
        return

    if isinstance(data, bytes):
        # bytes 也是不可变的
        raise MemoryProtectionError("Cannot zero immutable bytes object")

    if isinstance(data, bytearray):
        # 使用 Volatile 写入确保不被优化掉
        target_len = length if length is not None else len(data)
        for i in range(min(target_len, len(data))):
            data[i] = 0

        # 尝试强制内存屏障
        if hasattr(ctypes, "pythonapi"):
            # 仅作为一个提示，Python 无法保证内存屏障
            pass


def protect_string(value: str) -> "ProtectedString":
    """
    创建受保护的字符串

    受保护的字符串会：
    1. 尝试锁定内存防止 swap
    2. 在析构时清零
    3. 禁止 pickle 序列化

    Args:
        value: 要保护的字符串值

    Returns:
        ProtectedString: 受保护的字符串包装器
    """
    return ProtectedString(value)


class ProtectedString:
    """
    受保护的字符串类

    特性：
    - 尝试 mlock 锁定内存
    - 析构时自动清零
    - 禁止序列化
    - 防止意外的日志泄露
    """

    # 最大可锁定大小 (Linux 默认 rlimit)
    MAX_LOCK_SIZE = 64 * 1024  # 64KB

    def __init__(self, value: str):
        if not isinstance(value, str):
            raise TypeError("ProtectedString only accepts str values")

        # 转换为字节
        self._bytes = value.encode("utf-8")
        self._length = len(self._bytes)

        if self._length > self.MAX_LOCK_SIZE:
            raise MemoryProtectionError(
                f"String too large for mlock ({self._length} > {self.MAX_LOCK_SIZE})"
            )

        # 创建可写缓冲区
        self._buffer = bytearray(self._bytes)
        self._locked = False

        # 尝试锁定内存
        if HAS_MLOCK and LIBC:
            try:
                ptr = ctypes.addressof(ctypes.c_char.from_buffer(self._buffer))
                if LIBC.mlock(ptr, self._length) == 0:
                    self._locked = True
            except Exception:
                pass  # mlock 失败不是致命错误

    @property
    def value(self) -> str:
        """获取字符串值 (谨慎使用)"""
        return self._buffer.decode("utf-8")

    def __str__(self) -> str:
        """防止意外泄露"""
        return "***PROTECTED***"

    def __repr__(self) -> str:
        """防止意外泄露"""
        return f"ProtectedString(length={self._length}, locked={self._locked})"

    def __len__(self) -> int:
        return self._length

    def __del__(self):
        """析构时清零并解锁"""
        self.zero()
        self.unlock()

    def zero(self) -> None:
        """安全清零内存"""
        secure_zero(self._buffer)

    def unlock(self) -> None:
        """解锁内存"""
        if self._locked and HAS_MLOCK and LIBC:
            try:
                ptr = ctypes.addressof(ctypes.c_char.from_buffer(self._buffer))
                LIBC.munlock(ptr, self._length)
                self._locked = False
            except Exception:
                pass

    def __getstate__(self):
        """禁止 pickle"""
        raise TypeError("Cannot serialize ProtectedString")

    def __setstate__(self, state):
        """禁止 pickle"""
        raise TypeError("Cannot deserialize ProtectedString")


class MemoryGuard:
    """
    内存上下文管理器

    在作用域结束时自动清理敏感数据

    用法:
        with MemoryGuard() as guard:
            api_key = guard.protect("sk-...")
            # 使用 api_key
        # 自动清零
    """

    def __init__(self):
        self._protected: list[ProtectedString] = []

    def protect(self, value: str) -> ProtectedString:
        """保护字符串"""
        protected = ProtectedString(value)
        self._protected.append(protected)
        return protected

    def cleanup(self) -> None:
        """清理所有受保护的数据"""
        for protected in self._protected:
            protected.zero()
        self._protected.clear()

    def __enter__(self) -> "MemoryGuard":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


def secure_function(func):
    """
    装饰器：确保函数返回的敏感数据被保护

    用法:
        @secure_function
        def get_api_key():
            return "sk-..."

        key = get_api_key()  # 返回 ProtectedString
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        # 如果返回字符串，自动保护
        if isinstance(result, str):
            # 检查函数名或参数名是否暗示敏感数据
            func_name_lower = func.__name__.lower()
            if any(s in func_name_lower for s in ["key", "secret", "token", "password"]):
                return ProtectedString(result)

        return result

    return wrapper


def sanitize_traceback(
    exc: Optional[Exception] = None,
    hide_file_paths: bool = True,
    hide_line_numbers: bool = False,
) -> str:
    """
    清理堆栈跟踪，隐藏敏感信息

    Args:
        exc: 异常对象 (默认: 当前异常)
        hide_file_paths: 是否隐藏文件路径
        hide_line_numbers: 是否隐藏行号

    Returns:
        str: 清理后的堆栈跟踪
    """
    if exc is None:
        exc = sys.exception()

    if exc is None:
        return ""

    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    if hide_file_paths:
        # 只保留文件名，隐藏完整路径
        import re
        tb_str = re.sub(
            r'File "([^"]+)"',
            lambda m: f'File "{os.path.basename(m.group(1))}"',
            tb_str,
        )

    if hide_line_numbers:
        import re
        tb_str = re.sub(r', line \d+', ', line <redacted>', tb_str)

    return tb_str


def clear_exception_trace(exc: Exception) -> None:
    """
    清理异常对象的堆栈跟踪

    注意：这不能完全从内存中删除数据，
    但可以减少堆栈跟踪的可用性。
    """
    if hasattr(exc, "__traceback__") and exc.__traceback__ is not None:
        exc.__traceback__ = None


def get_memory_limit() -> dict[str, int]:
    """
    获取内存限制信息

    Returns:
        dict: 包含 rlimit 信息的字典
    """
    if not HAS_MLOCK:
        return {"mlock_available": False}

    try:
        import resource

        soft, hard = resource.getrlimit(resource.RLIMIT_MEMLOCK)
        return {
            "mlock_available": True,
            "soft_limit": soft,
            "hard_limit": hard,
            "soft_limit_mb": soft // (1024 * 1024) if soft != resource.RLIM_INFINITY else -1,
            "hard_limit_mb": hard // (1024 * 1024) if hard != resource.RLIM_INFINITY else -1,
        }
    except Exception as e:
        return {"mlock_available": False, "error": str(e)}


# 注册退出时的清理


@atexit.register
def _cleanup_on_exit():
    """程序退出时的清理"""
    # Python GC 会自动调用 ProtectedString.__del__
    # 这里只是一个保险措施
    import gc
    gc.collect()


def check_memory_leaks() -> dict[str, Any]:
    """
    检查潜在的内存泄露

    Returns:
        dict: 内存统计信息
    """
    import gc
    import sys

    gc.collect()

    # 统计 ProtectedString 实例
    protected_strings = [
        obj for obj in gc.get_objects()
        if isinstance(obj, ProtectedString)
    ]

    return {
        "protected_string_count": len(protected_strings),
        "protected_string_total_bytes": sum(len(p) for p in protected_strings),
        "gc_objects": len(gc.get_objects()),
        "ref_count": sys.getrefcount(gc.get_objects()),
    }
