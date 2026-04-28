"""API Key 本地存储工具。

V1 是本地单机部署，不伪装成加密存储。函数名保留用于兼容旧调用点，
实际语义是明确的本地明文保存。
"""


def encrypt_key(plaintext: str) -> str:
    """返回本地可存储的 API Key 明文。"""
    return plaintext or ""


def decrypt_key(ciphertext: str) -> str:
    """返回本地保存的 API Key 明文。"""
    return ciphertext or ""
