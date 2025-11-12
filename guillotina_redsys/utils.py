from Crypto.Cipher import AES  # pip install pycryptodome

import base64
import hashlib
import hmac


# ---------- helpers ----------


def _base64url_encode(raw: bytes) -> str:
    """
    BASE64URL without padding, as Redsys expects.
    """
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _aes_cbc_encrypt(key16: bytes, plaintext: bytes) -> bytes:
    """
    AES-CBC with IV=0, PKCS7 padding.
    """
    block_size = 16
    pad_len = block_size - (len(plaintext) % block_size)
    padded = plaintext + bytes([pad_len]) * pad_len
    iv = b"\x00" * block_size
    cipher = AES.new(key16, AES.MODE_CBC, iv)
    return cipher.encrypt(padded)


def compute_redsys_signature(
    terminal_key: str,
    merchant_params_b64: str,
    order: str,
) -> str:
    """
    HMAC_SHA512_V2 signature for Redsys (Ds_Signature).
    - terminal_key: plain text key from Canales (NOT base64).
    - merchant_params_b64: Ds_MerchantParameters already base64-encoded.
    - order: Ds_Merchant_Order (plain string).
    """

    # 1) Preprocess key to exactly 16 chars
    if len(terminal_key) > 16:
        key16_str = terminal_key[:16]
    else:
        key16_str = terminal_key.ljust(16, "0")
    key16 = key16_str.encode("utf-8")

    # 2) Diversified key via AES-CBC(order, key16, iv=0)
    cipher_bytes = _aes_cbc_encrypt(key16, order.encode("utf-8"))

    # 3) Base64 of diversified key
    diversified_key_b64 = base64.b64encode(cipher_bytes)

    # 4) HMAC-SHA512( Ds_MerchantParameters (base64 string), diversified_key )
    mac = hmac.new(
        diversified_key_b64,
        merchant_params_b64.encode("ascii"),
        hashlib.sha512,
    ).digest()

    # 5) BASE64URL of HMAC result -> Ds_Signature
    return _base64url_encode(mac)
