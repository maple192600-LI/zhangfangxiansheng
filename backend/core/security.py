"""API Key 对称加密工具

使用 base64 + FNV hash 做简单对称加密。
V1 本地单机部署，不做复杂密钥管理。
"""
import base64
import hashlib
import os

# 本地固定盐值 — 仅用于本地部署场景
_SALT = b"zhangfang_v1_local_salt_2026"


def encrypt_key(plaintext: str) -> str:
    """加密 API Key，返回可存储的字符串"""
    if not plaintext:
        return ""
    raw = plaintext.encode("utf-8")
    # XOR with salt-derived key stream
    key = _derive_key(len(raw))
    encrypted = bytes(a ^ b for a, b in zip(raw, key))
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_key(ciphertext: str) -> str:
    """解密 API Key，返回明文"""
    if not ciphertext:
        return ""
    encrypted = base64.b64decode(ciphertext)
    key = _derive_key(len(encrypted))
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key))
    return decrypted.decode("utf-8")


def _derive_key(length: int) -> bytes:
    """从盐值派生指定长度的 key stream"""
    full_key = _SALT
    while len(full_key) < length:
        full_key += hashlib.sha256(full_key).digest()
    return full_key[:length]
