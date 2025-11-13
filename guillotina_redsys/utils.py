from Crypto.Cipher import AES  # pip install pycryptodome

import base64
import hashlib
import hmac
import json
from typing import Any, Dict, Optional, Union

import aiohttp
from aiohttp import ClientConnectorError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# ---------- helpers ----------


def _base64url_encode(raw: bytes) -> str:
    """
    BASE64URL without padding, as Redsys expects.
    """
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_redsys_merchant_parameters(encoded: str) -> Dict[str, Any]:
    """
    Decode Redsys Ds_MerchantParameters (Base64URL without padding) into a dict.
    """
    # restore padding for base64
    padding = "=" * (-len(encoded) % 4)
    raw = base64.urlsafe_b64decode(encoded + padding)
    return json.loads(raw.decode("utf-8"))


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


class HTTPServerError(Exception):
    """Raised for 5xx responses so tenacity can retry."""


class RestAPI:
    """
    Minimal async REST client with retry logic.
    Good fit for Redsys REST calls.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = 10,
    ) -> None:
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = None
        self._external_session = session is not None
        self.session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        )

    async def close(self) -> None:
        if not self._external_session:
            await self.session.close()

    @retry(
        retry=retry_if_exception_type((ClientConnectorError, HTTPServerError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=0.5, max=5),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], str]:
        if self.base_url:
            url = f"{self.base_url}/{path.lstrip('/')}"
        else:
            url = path
        async with self.session.request(
            method.upper(),
            url,
            json=json,
            data=data,
            params=params,
            headers=headers,
        ) as resp:
            # Retry only on 5xx
            if 500 <= resp.status < 600:
                text = await resp.text()
                raise HTTPServerError(f"{resp.status} Server Error: {text}")

            # For Redsys you usually get JSON
            try:
                return await resp.json()
            except Exception:
                return await resp.text()

    # ---- public coroutines ----

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], str]:
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        *,
        data: Optional[str] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], str]:
        return await self._request(
            "POST", path, json=json, params=params, data=data, headers=headers
        )

    async def patch(
        self,
        path: str,
        *,
        data: Optional[str] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], str]:
        return await self._request(
            "PATCH", path, json=json, params=params, data=data, headers=headers
        )

    async def delete(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], str]:
        return await self._request("DELETE", path, params=params, headers=headers)
