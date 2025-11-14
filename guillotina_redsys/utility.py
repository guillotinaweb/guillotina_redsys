from decimal import Decimal
from guillotina.utils import get_current_request
from guillotina_redsys.models import CVV2
from guillotina_redsys.models import ExpiryDate
from guillotina_redsys.models import OrderId
from guillotina_redsys.models import Pan
from guillotina_redsys.models import Redsys3DSMethodResponse
from guillotina_redsys.models import RedsysAuthResult
from guillotina_redsys.models import RedsysEMV3DS
from guillotina_redsys.models import RedsysEMV3DSResponse
from guillotina_redsys.models import RedsysErrorResponse
from guillotina_redsys.models import RedsysForm
from guillotina_redsys.models import RedsysIniciaPeticionResponse
from guillotina_redsys.models import RedsysMerchantParams
from guillotina_redsys.utils import decode_redsys_merchant_parameters
from guillotina_redsys.utils import RestAPI

import asyncio
import base64
import json


class RedsysUtility:
    def __init__(self, settings=None, loop=None):
        self._settings = settings
        self.terminal = self._settings["terminal"]
        self.secret_key = self._settings["secret_key"]
        self.merchant_code = self._settings["merchant_code"]
        self.url_redsys = self._settings["url_redsys"]
        self.container_url = self._settings["container_url"]
        self.redsys_api = RestAPI(self.url_redsys)
        self.api = RestAPI()

    def _build_form(self, merchant: RedsysMerchantParams) -> dict:
        form = RedsysForm.from_merchant(
            merchant=merchant,
            terminal_key=self.secret_key,
        )
        return form.dict()

    async def init_transaction(
        self,
        amount: Decimal,
        card: Pan,
        cvv: CVV2,
        expiry_date: ExpiryDate,
        order: OrderId,
        currency=978,
        transaction_type="0",
    ):
        merchant = RedsysMerchantParams.from_euros(
            amount_eur=amount,
            currency_numeric=currency,
            merchant_code=self.merchant_code,
            order=order,
            terminal=self.terminal,
            transaction_type=transaction_type,
            cvv2=cvv,
            emv3ds={"threeDSInfo": "CardData"},
            excep_sca="Y",
            expiry_date=expiry_date,
            pan=card,
        )
        form = RedsysForm.from_merchant(
            merchant=merchant,
            terminal_key=self.secret_key,
        )
        response = await self.redsys_api.post("/iniciaPeticionREST", json=form.dict())
        response = json.loads(response)
        if "errorCode" in response:
            return RedsysErrorResponse(**response)
        decoded = decode_redsys_merchant_parameters(response["Ds_MerchantParameters"])
        result = RedsysIniciaPeticionResponse(**decoded)
        notification_url = f"{self.container_url}/@notificationRedsys3DS/{result.Ds_Order}/{result.Ds_EMV3DS.threeDSServerTransID}"
        payload = {
            "threeDSServerTransID": result.Ds_EMV3DS.threeDSServerTransID,
            "threeDSMethodNotificationURL": notification_url,
        }
        payload = (
            base64.urlsafe_b64encode(json.dumps(payload).encode())
            .decode("ascii")
            .rstrip("=")
        )

        result.payload_3DS = payload
        return result

    # TODO the frontend needs to do the wait for. The backend needs to
    # log/persist the callback response. Use redis maybe?
    async def init_threeds_method(self, transaction_id, three_method_url):
        payload = {
            "threeDSServerTransID": transaction_id,
            "threeDSMethodNotificationURL": self.container_url,
        }
        if three_method_url:
            payload = (
                base64.urlsafe_b64encode(json.dumps(payload).encode())
                .decode("ascii")
                .rstrip("=")
            )
            try:
                result = await asyncio.wait_for(
                    self.api.post(
                        three_method_url, json={"threeDSMethodData": payload}
                    ),
                    timeout=10,
                )
                result = json.loads(result)
                return Redsys3DSMethodResponse(
                    threeDSCompInd=result.get("threeDSCompInd", "N")
                )
            except asyncio.TimeoutError:
                return Redsys3DSMethodResponse(threeDSCompInd="N")
        return Redsys3DSMethodResponse(threeDSCompInd="N")

    async def init_trata_peticion(
        self,
        amount: Decimal,
        card: Pan,
        cvv: CVV2,
        expiry_date: ExpiryDate,
        order: OrderId,
        protocol_version: str,
        transaction_id: str,
        three_ds_comp_ind: str,
        currency=978,
        transaction_type="0",
    ):
        request = get_current_request()
        notification_url = f"{self.container_url}/@notificationRedsysChallenge/{order}/{transaction_id}"
        emv3ds_auth = RedsysEMV3DS(
            threeDSInfo="AuthenticationData",
            protocolVersion=protocol_version,
            browserJavascriptEnabled="true",
            browserAcceptHeader=request.headers.get("Accept", ""),
            browserUserAgent=request.headers.get("User-Agent", ""),
            threeDSServerTransID=transaction_id,
            browserJavaEnabled="false",
            browserLanguage="es-ES",
            browserColorDepth="24",
            browserScreenHeight="1250",
            browserScreenWidth="1320",
            browserTZ="52",
            threeDSCompInd=three_ds_comp_ind,
            notificationURL=notification_url,
        )
        merchant = RedsysMerchantParams.from_euros(
            amount_eur=amount,
            currency_numeric=currency,
            merchant_code=self.merchant_code,
            order=order,
            terminal=self.terminal,
            transaction_type="0",
            pan=card,
            cvv2=cvv,
            expiry_date=expiry_date,
            emv3ds=emv3ds_auth,
        )
        form = RedsysForm.from_merchant(
            merchant=merchant,
            terminal_key=self.secret_key,
        )
        response = await self.redsys_api.post("/trataPeticionREST", json=form.dict())
        response = json.loads(response)
        if "errorCode" in response:
            return RedsysErrorResponse(**response)
        decoded = decode_redsys_merchant_parameters(response["Ds_MerchantParameters"])
        if "Ds_EMV3DS" in decoded:
            return RedsysEMV3DSResponse(**decoded["Ds_EMV3DS"])
        if "Ds_Response" in decoded:
            return RedsysAuthResult(**decoded)

    async def authenticate_cres(
        self,
        amount: Decimal,
        card: Pan,
        cvv: CVV2,
        expiry_date: ExpiryDate,
        order: OrderId,
        protocol_version: str,
        cres: str,
        currency=978,
        transaction_type="0",
    ):
        emv3ds_auth = RedsysEMV3DS(
            threeDSInfo="ChallengeResponse",
            protocolVersion=protocol_version,
            cres=cres,
        )
        merchant = RedsysMerchantParams.from_euros(
            amount_eur=amount,
            currency_numeric=currency,
            merchant_code=self.merchant_code,
            order=order,
            terminal=self.terminal,
            transaction_type="0",
            pan=card,
            cvv2=cvv,
            expiry_date=expiry_date,
            emv3ds=emv3ds_auth,
        )
        form = RedsysForm.from_merchant(
            merchant=merchant,
            terminal_key=self.secret_key,
        )
        response = await self.redsys_api.post("/trataPeticionREST", json=form.dict())
        response = json.loads(response)
        if "errorCode" in response:
            return RedsysErrorResponse(**response)
        decoded = decode_redsys_merchant_parameters(response["Ds_MerchantParameters"])
        if "Ds_Response" in decoded:
            return RedsysAuthResult(**decoded)

    async def initialize(self):
        pass

    async def finalize(self):
        pass
