"""API Key 本地存储工具。

使用 PBKDF2 密钥派生 + salt + HMAC 签名验证的加密方案。
向后兼容：如果解密失败（旧 XOR 或明文数据），直接返回原文。
"""
import base64
import hashlib
import hmac
import os


def _derive_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 100_000, dklen=48)


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_key(plaintext: str) -> str:
    if not plaintext:
        return ""
    salt = os.urandom(16)
    derived = _derive_key(__import__("config").SECRET_KEY, salt)
    enc_key, mac_key = derived[:32], derived[32:]
    xored = _xor_crypt(plaintext.encode("utf-8"), enc_key)
    mac = hmac.new(mac_key, salt + xored, hashlib.sha256).digest()
    return base64.b64encode(salt + mac + xored).decode("ascii")


def decrypt_key(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        raw = base64.b64decode(ciphertext)
        if len(raw) < 49:
            return ciphertext
        salt, mac, xored = raw[:16], raw[16:48], raw[48:]
        derived = _derive_key(__import__("config").SECRET_KEY, salt)
        enc_key, mac_key = derived[:32], derived[32:]
        expected = hmac.new(mac_key, salt + xored, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return ciphertext
        return _xor_crypt(xored, enc_key).decode("utf-8")
    except Exception:
        return ciphertext
