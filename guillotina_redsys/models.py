# pydantic v1
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
from pydantic import BaseModel, conint, constr, validator


class RedsysMerchantParams(BaseModel):
    # NOTE: Redsys expects *strings of digits* in the final payload.
    # We keep some as int for sanity, then export them as strings.

    # 12 digits max, integer minor units (e.g., EUR cents). Must be >= 1
    Ds_Merchant_Amount: conint(ge=1, le=999_999_999_999)

    # ISO-4217 numeric currency code, exactly 3 digits (e.g., EUR=978)
    Ds_Merchant_Currency: conint(ge=1, le=999)

    # FUC (merchant code) — numeric up to 9 digits, kept as string to preserve leading zeros
    Ds_Merchant_MerchantCode: constr(pattern=r"^\d{1,9}$")

    # Order id — alphanumeric, 4–12 chars (Redsys recommends >4)
    Ds_Merchant_Order: constr(pattern=r"^[A-Za-z0-9]{4,12}$")

    # Terminal — exactly 3 digits (often "001")
    Ds_Merchant_Terminal: constr(pattern=r"^\d{3}$")

    # Transaction type — 1 digit (e.g., "0" authorization)
    Ds_Merchant_TransactionType: constr(pattern=r"^\d$")

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
        cents = (amount_eur * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(cents)

    @classmethod
    def from_euros(
        cls,
        *,
        amount_eur: Decimal,
        currency_numeric: int = 978,   # EUR by default
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

    @validator("Ds_Merchant_MerchantCode", "Ds_Merchant_Order", "Ds_Merchant_Terminal", "Ds_Merchant_TransactionType")
    def _strip_spaces(cls, v: str) -> str:
        return v.strip()
