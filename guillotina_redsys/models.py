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
from pydantic import Field
import base64
import json
from typing import Optional
from urllib.parse import unquote


# Common string types
MerchantCode = constr(pattern=r"^\d{1,9}$")
OrderId = constr(pattern=r"^[A-Za-z0-9]{4,12}$")
Terminal = constr(pattern=r"^\d{3}$")
TransactionType = constr(pattern=r"^\d$")

Pan = constr(pattern=r"^\d{12,19}$")
ExpiryDate = constr(pattern=r"^\d{4}$")
CVV2 = constr(pattern=r"^\d{3,4}$")
ExcepSCAFlag = constr(pattern=r"^[YN]$")
TerminalResponse = constr(pattern=r"^\d{1,3}$")
ExcepSCA = constr(min_length=1, max_length=255)
CardPSD2Flag = constr(pattern=r"^[YN]$")
ThreeDSCompInd = constr(pattern=r"^[YN]$")


class RedsysEMV3DS(BaseModel):
    # For your example: {"threeDSInfo": "CardData"}
    threeDSInfo: constr(min_length=1, max_length=32)
    cres: Optional[str] = None

    # optional (for iniciaPeticion + authentication)
    protocolVersion: Optional[constr(min_length=1, max_length=16)] = None
    threeDSServerTransID: Optional[constr(min_length=1, max_length=64)] = None
    browserJavascriptEnabled: Optional[constr(pattern=r"^(true|false)$")] = None
    browserAcceptHeader: Optional[constr(min_length=1, max_length=512)] = None
    browserUserAgent: Optional[constr(min_length=1, max_length=512)] = None
    browserJavaEnabled: Optional[constr(pattern=r"^(true|false)$")] = None
    browserLanguage: Optional[constr(min_length=1, max_length=8)] = None
    browserColorDepth: Optional[constr(pattern=r"^\d+$")] = None
    browserScreenHeight: Optional[constr(pattern=r"^\d+$")] = None
    browserScreenWidth: Optional[constr(pattern=r"^\d+$")] = None
    browserTZ: Optional[constr(pattern=r"^-?\d+$")] = None
    threeDSCompInd: Optional[constr(pattern=r"^[YN]$")] = None
    notificationURL: Optional[str] = None  # may be None / omitted

    class Config:
        extra = "allow"


class RedsysMerchantParams(BaseModel):
    Ds_Merchant_Amount: conint(ge=1, le=999_999_999_999)
    Ds_Merchant_Currency: conint(ge=1, le=999)
    Ds_Merchant_MerchantCode: MerchantCode
    Ds_Merchant_Order: OrderId
    Ds_Merchant_Terminal: Terminal
    Ds_Merchant_TransactionType: TransactionType

    # --- REST card fields (optional) ---
    Ds_Merchant_Pan: Optional[Pan] = None
    Ds_Merchant_ExpiryDate: Optional[ExpiryDate] = None  # MMyy
    Ds_Merchant_CVV2: Optional[CVV2] = None

    # --- 3DS + SCA ---
    Ds_Merchant_EMV3DS: Optional[RedsysEMV3DS] = None
    Ds_Merchant_Excep_SCA: Optional[ExcepSCAFlag] = None

    class Config:
        anystr_strip_whitespace = True

    # -------- Helpers

    def to_redsys_dict(self) -> Dict[str, object]:
        """
        Export with the exact Redsys keys and values as digit / JSON strings.
        Only include REST-only fields if present.
        """
        data: Dict[str, object] = {
            "Ds_Merchant_Amount": str(self.Ds_Merchant_Amount),
            "Ds_Merchant_Currency": f"{int(self.Ds_Merchant_Currency):03d}",
            "Ds_Merchant_MerchantCode": self.Ds_Merchant_MerchantCode,
            "Ds_Merchant_Order": self.Ds_Merchant_Order,
            "Ds_Merchant_Terminal": self.Ds_Merchant_Terminal,
            "Ds_Merchant_TransactionType": self.Ds_Merchant_TransactionType,
        }

        if self.Ds_Merchant_Pan is not None:
            data["Ds_Merchant_Pan"] = self.Ds_Merchant_Pan
        if self.Ds_Merchant_ExpiryDate is not None:
            data["Ds_Merchant_ExpiryDate"] = self.Ds_Merchant_ExpiryDate
        if self.Ds_Merchant_CVV2 is not None:
            data["Ds_Merchant_CVV2"] = self.Ds_Merchant_CVV2
        if self.Ds_Merchant_EMV3DS is not None:
            data["Ds_Merchant_EMV3DS"] = self.Ds_Merchant_EMV3DS.dict()
        if self.Ds_Merchant_Excep_SCA is not None:
            data["Ds_Merchant_Excep_SCA"] = self.Ds_Merchant_Excep_SCA

        return data

    @staticmethod
    def euros_to_minor_units(amount_eur: Decimal) -> int:
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
        pan: Optional[str] = None,
        expiry_date: Optional[str] = None,
        cvv2: Optional[str] = None,
        emv3ds: Optional[RedsysEMV3DS] = None,
        excep_sca: Optional[str] = None,
    ) -> "RedsysMerchantParams":
        return cls(
            Ds_Merchant_Amount=cls.euros_to_minor_units(amount_eur),
            Ds_Merchant_Currency=currency_numeric,
            Ds_Merchant_MerchantCode=merchant_code,
            Ds_Merchant_Order=order,
            Ds_Merchant_Terminal=terminal,
            Ds_Merchant_TransactionType=transaction_type,
            Ds_Merchant_Pan=pan,
            Ds_Merchant_ExpiryDate=expiry_date,
            Ds_Merchant_CVV2=cvv2,
            Ds_Merchant_EMV3DS=emv3ds,
            Ds_Merchant_Excep_SCA=excep_sca,
        )

    # -------- Optional defensive normalizers

    @validator(
        "Ds_Merchant_MerchantCode",
        "Ds_Merchant_Order",
        "Ds_Merchant_Terminal",
        "Ds_Merchant_TransactionType",
        "Ds_Merchant_Pan",
        "Ds_Merchant_ExpiryDate",
        "Ds_Merchant_CVV2",
        "Ds_Merchant_Excep_SCA",
    )
    def _strip_spaces(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class RedsysForm(BaseModel):
    Ds_SignatureVersion: Literal["HMAC_SHA512_V2"]
    Ds_MerchantParameters: str
    Ds_Signature: str

    @classmethod
    def from_merchant(
        cls, merchant: RedsysMerchantParams, terminal_key: str
    ) -> "RedsysForm":
        merchant_json = json.dumps(merchant.to_redsys_dict()).encode("utf-8")
        merchant_b64url = (
            base64.urlsafe_b64encode(merchant_json).decode("ascii").rstrip("=")
        )

        signature = compute_redsys_signature(
            merchant_params_b64=merchant_b64url,
            terminal_key=terminal_key,
            order=merchant.Ds_Merchant_Order,
        )

        return cls(
            Ds_SignatureVersion="HMAC_SHA512_V2",
            Ds_MerchantParameters=merchant_b64url,
            Ds_Signature=signature,
        )


class RedsysEMV3DSResponse(BaseModel):
    # always present
    threeDSInfo: constr(min_length=1, max_length=32)

    # sometimes present
    protocolVersion: Optional[constr(min_length=1, max_length=16)] = None
    threeDSServerTransID: Optional[constr(min_length=1, max_length=64)] = None
    threeDSMethodURL: Optional[str] = None

    # challenge fields
    acsURL: Optional[str] = None
    creq: Optional[str] = None

    class Config:
        extra = "allow"


class Redsys3DSMethodResponse(BaseModel):
    """
    Response/decision after running 3DSMethod.

    threeDSCompInd:
      - "Y" -> método ejecutado y notificado < 10s
      - "N" -> no se recibió respuesta en 10s
    """

    threeDSCompInd: ThreeDSCompInd


class RedsysIniciaPeticionResponse(BaseModel):
    Ds_Order: OrderId
    Ds_MerchantCode: MerchantCode
    Ds_Terminal: TerminalResponse
    Ds_TransactionType: TransactionType
    Ds_EMV3DS: RedsysEMV3DSResponse
    Ds_Excep_SCA: Optional[ExcepSCA] = None
    Ds_Card_PSD2: Optional[CardPSD2Flag] = None


RepeatOrderStatus = Literal["Y", "N"]


class RedsysErrorResponse(BaseModel):
    errorCode: constr(min_length=1, max_length=8)
    repeatOrderStatus: Optional[RepeatOrderStatus] = None
    errorCodeDescription: Optional[str] = None


class RedsysAPIError(Exception):
    def __init__(self, error: RedsysErrorResponse):
        self.error = error
        super().__init__(
            f"Redsys error {error.errorCode}: {error.errorCodeDescription}"
        )


# --- new: frictionless / final authorization shape ---
class RedsysAuthResult(BaseModel):
    Ds_Date: Optional[str] = None  # may come URL-encoded
    Ds_Hour: Optional[str] = None  # may come URL-encoded
    Ds_SecurePayment: Optional[constr(pattern=r"^[0-2]$")] = None
    Ds_Amount: constr(pattern=r"^\d+$")
    Ds_Currency: constr(pattern=r"^\d{3}$")
    Ds_Order: constr(pattern=r"^[A-Za-z0-9]{4,12}$")
    Ds_MerchantCode: constr(pattern=r"^\d{1,9}$")
    Ds_Terminal: constr(pattern=r"^\d{1,3}$")
    Ds_Response: constr(pattern=r"^\d{4}$")  # "0000" = OK
    Ds_TransactionType: constr(pattern=r"^\d$")
    Ds_AuthorisationCode: Optional[constr(min_length=1, max_length=12)] = None
    Ds_ConsumerLanguage: Optional[str] = None
    Ds_Card_Country: Optional[str] = None
    Ds_Card_Brand: Optional[str] = None
    Ds_ProcessedPayMethod: Optional[str] = None
    # field name variants Redsys uses
    Ds_Card_Number: Optional[str] = Field(default=None, alias="Ds_Card_Number")
    Ds_CardNumber: Optional[str] = Field(default=None, alias="Ds_CardNumber")

    # Handy helpers
    @property
    def is_authorized(self) -> bool:
        return self.Ds_Response == "0000"

    def decoded_datetime(self) -> tuple[Optional[str], Optional[str]]:
        # Redsys often URL-encodes date/hour in this response
        return (
            unquote(self.Ds_Date) if self.Ds_Date else None,
            unquote(self.Ds_Hour) if self.Ds_Hour else None,
        )
