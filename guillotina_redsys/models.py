# pydantic v1
from decimal import Decimal
from decimal import ROUND_HALF_UP
from guillotina_redsys.utils import compute_redsys_signature
from pydantic import BaseModel
from pydantic import conint
from pydantic import constr
from pydantic import validator
from typing import Dict
from typing import Literal

import base64
import json


MerchantCode = constr(pattern=r"^\d{1,9}$")
OrderId = constr(pattern=r"^[A-Za-z0-9]{4,12}$")
Terminal = constr(pattern=r"^\d{3}$")
TransactionType = constr(pattern=r"^\d$")


class RedsysMerchantParams(BaseModel):
    Ds_Merchant_Amount: conint(ge=1, le=999_999_999_999)
    Ds_Merchant_Currency: conint(ge=1, le=999)
    Ds_Merchant_MerchantCode: MerchantCode
    Ds_Merchant_Order: OrderId
    Ds_Merchant_Terminal: Terminal
    Ds_Merchant_TransactionType: TransactionType

    class Config:
        anystr_strip_whitespace = True

    # -------- Helpers

    def to_redsys_dict(self) -> Dict[str, str]:
        """
        Export with the exact Redsys keys and values as digit strings.
        """
        return {
            "Ds_Merchant_Amount": str(self.Ds_Merchant_Amount),
            "Ds_Merchant_Currency": f"{int(self.Ds_Merchant_Currency):03d}",
            "Ds_Merchant_MerchantCode": self.Ds_Merchant_MerchantCode,
            "Ds_Merchant_Order": self.Ds_Merchant_Order,
            "Ds_Merchant_Terminal": self.Ds_Merchant_Terminal,
            "Ds_Merchant_TransactionType": self.Ds_Merchant_TransactionType,
        }

    @staticmethod
    def euros_to_minor_units(amount_eur: Decimal) -> int:
        """
        Convert EUR to minor units (cents) with bankers-safe rounding.
        For Redsys you normally *never* send decimals; this enforces it.
        """
        cents = (amount_eur * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(cents)

    @classmethod
    def from_euros(
        cls,
        *,
        amount_eur: Decimal,
        currency_numeric: int = 978,  # EUR by default
        merchant_code: str,
        order: str,
        terminal: str = "001",
        transaction_type: str = "0",
    ) -> "RedsysMerchantParams":
        return cls(
            Ds_Merchant_Amount=cls.euros_to_minor_units(amount_eur),
            Ds_Merchant_Currency=currency_numeric,
            Ds_Merchant_MerchantCode=merchant_code,
            Ds_Merchant_Order=order,
            Ds_Merchant_Terminal=terminal,
            Ds_Merchant_TransactionType=transaction_type,
        )

    # -------- Optional defensive normalizers

    @validator(
        "Ds_Merchant_MerchantCode",
        "Ds_Merchant_Order",
        "Ds_Merchant_Terminal",
        "Ds_Merchant_TransactionType",
    )
    def _strip_spaces(cls, v: str) -> str:
        return v.strip()


class RedsysForm(BaseModel):
    Ds_SignatureVersion: Literal["HMAC_SHA512_V2"] = "HMAC_SHA512_V2"
    Ds_MerchantParameters: constr(min_length=1)
    Ds_Signature: constr(min_length=1)

    @classmethod
    def from_merchant(
        cls,
        merchant: RedsysMerchantParams,
        terminal_key: str,
    ) -> "RedsysForm":
        # Build Ds_MerchantParameters: JSON (all strings) → base64
        merchant_json = json.dumps(merchant.to_redsys_dict(), separators=(",", ":"))
        merchant_b64 = base64.b64encode(merchant_json.encode("utf-8")).decode("ascii")

        # Compute Ds_Signature
        signature = compute_redsys_signature(
            terminal_key=terminal_key,
            merchant_params_b64=merchant_b64,
            order=merchant.Ds_Merchant_Order,
        )

        return cls(
            Ds_SignatureVersion="HMAC_SHA512_V2",
            Ds_MerchantParameters=merchant_b64,
            Ds_Signature=signature,
        )
