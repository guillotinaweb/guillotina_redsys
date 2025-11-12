from decimal import Decimal
from guillotina.component import get_utility
from guillotina_redsys.interfaces import IRedsysUtility
from guillotina_redsys.models import RedsysForm
from guillotina_redsys.models import RedsysMerchantParams
from guillotina_redsys.utils import compute_redsys_signature
from guillotina import task_vars
from guillotina.tests.utils import make_mocked_request
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from zope.interface import alsoProvides

import json
import pytest


pytestmark = pytest.mark.asyncio


async def test_models():
    params = RedsysMerchantParams.from_euros(
        amount_eur=Decimal("12.49"),
        currency_numeric=978,
        merchant_code="123456789",
        order="ABCD1234",
        terminal="001",
        transaction_type="0",
    )
    payload = params.to_redsys_dict()
    assert payload == {
        "Ds_Merchant_Amount": "1249",
        "Ds_Merchant_Currency": "978",
        "Ds_Merchant_MerchantCode": "123456789",
        "Ds_Merchant_Order": "ABCD1234",
        "Ds_Merchant_Terminal": "001",
        "Ds_Merchant_TransactionType": "0",
    }

    terminal_key = "DUMMY_KEY_TERMINAL"
    form = RedsysForm.from_merchant(params, terminal_key)
    payload = form.dict()
    assert payload["Ds_SignatureVersion"] == "HMAC_SHA512_V2"
    assert (
        payload["Ds_MerchantParameters"]
        == "eyJEc19NZXJjaGFudF9BbW91bnQiOiIxMjQ5IiwiRHNfTWVyY2hhbnRfQ3VycmVuY3kiOiI5NzgiLCJEc19NZXJjaGFudF9NZXJjaGFudENvZGUiOiIxMjM0NTY3ODkiLCJEc19NZXJjaGFudF9PcmRlciI6IkFCQ0QxMjM0IiwiRHNfTWVyY2hhbnRfVGVybWluYWwiOiIwMDEiLCJEc19NZXJjaGFudF9UcmFuc2FjdGlvblR5cGUiOiIwIn0="
    )
    assert (
        payload["Ds_Signature"]
        == "xWRjkaw-EwqkFa4thFiPfv1P5oEDl3mJXk79QnU9KDZtXVjNg0QVJbEVEGfpxRChUg1psFx-OChuFCFNpCBjhQ"
    )
    params = RedsysMerchantParams.from_euros(
        amount_eur=Decimal("12.49"),
        currency_numeric=978,
        merchant_code="123456789",
        order="ABCD1234",
        terminal="001",
        transaction_type="0",
        pan="4548810000000003",
        expiry_date="4912",
        cvv2="123",
        excep_sca="Y",
        emv3ds={"threeDSInfo": "CardData"},
    )
    payload = params.to_redsys_dict()
    assert payload == {
        "Ds_Merchant_Amount": "1249",
        "Ds_Merchant_CVV2": "123",
        "Ds_Merchant_Currency": "978",
        "Ds_Merchant_EMV3DS": {"threeDSInfo": "CardData"},
        "Ds_Merchant_Excep_SCA": "Y",
        "Ds_Merchant_ExpiryDate": "4912",
        "Ds_Merchant_MerchantCode": "123456789",
        "Ds_Merchant_Order": "ABCD1234",
        "Ds_Merchant_Pan": "4548810000000003",
        "Ds_Merchant_Terminal": "001",
        "Ds_Merchant_TransactionType": "0",
    }
    form = RedsysForm.from_merchant(params, terminal_key)
    payload = form.dict()
    assert payload == {
        "Ds_MerchantParameters": "eyJEc19NZXJjaGFudF9BbW91bnQiOiIxMjQ5IiwiRHNfTWVyY2hhbnRfQ3VycmVuY3kiOiI5NzgiLCJEc19NZXJjaGFudF9NZXJjaGFudENvZGUiOiIxMjM0NTY3ODkiLCJEc19NZXJjaGFudF9PcmRlciI6IkFCQ0QxMjM0IiwiRHNfTWVyY2hhbnRfVGVybWluYWwiOiIwMDEiLCJEc19NZXJjaGFudF9UcmFuc2FjdGlvblR5cGUiOiIwIiwiRHNfTWVyY2hhbnRfUGFuIjoiNDU0ODgxMDAwMDAwMDAwMyIsIkRzX01lcmNoYW50X0V4cGlyeURhdGUiOiI0OTEyIiwiRHNfTWVyY2hhbnRfQ1ZWMiI6IjEyMyIsIkRzX01lcmNoYW50X0VNVjNEUyI6eyJ0aHJlZURTSW5mbyI6IkNhcmREYXRhIn0sIkRzX01lcmNoYW50X0V4Y2VwX1NDQSI6IlkifQ==",
        "Ds_Signature": "fYwsIx0pJphZ1uF4O4rVftO2MrJyBB4E9w3yr6aD1y_GHM9CMYgiCABHDh8S1imWV3D942MHn4S4OK9twaiN5w",
        "Ds_SignatureVersion": "HMAC_SHA512_V2",
    }


# Using sandbox from fixtures
# https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/


async def test_utility_3ds_2_2(guillotina_redsys):
    utility = get_utility(IRedsysUtility)
    # Visa EMV3DS 2.2
    order = "ABCD1240"
    res = await utility.init_transaction(
        amount=Decimal("12.49"),
        card="4548810000000003",
        expiry_date="4912",
        cvv="123",
        order=order,
    )
    assert isinstance(res.Ds_EMV3DS.threeDSServerTransID, str)
    res_3ds = await utility.init_threeds_method(payload=res)
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8,application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
    }
    request = make_mocked_request("POST", "/", headers=headers, payload={})
    request.interaction = None
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    task_vars.request.set(request)

    res = await utility.init_trata_peticion(
        amount=Decimal("12.49"),
        card="4548810000000003",
        expiry_date="4912",
        cvv="123",
        order=order,
        inicia_peticion_payload=res,
        three_ds_method_response=res_3ds,
    )


async def test_utility_3ds_2_1(guillotina_redsys):
    utility = get_utility(IRedsysUtility)
    # Mastercard EMV3DS 2.1
    res = await utility.init_transaction(
        amount=Decimal("12.49"),
        card="5576441563045037",
        expiry_date="4912",
        cvv="123",
        order="ABCD1234",
    )
    assert isinstance(res.Ds_EMV3DS.threeDSServerTransID, str)


async def test_utility_safekey(guillotina_redsys):
    utility = get_utility(IRedsysUtility)
    # American Express SafeKey 1.0.2
    res = await utility.init_transaction(
        amount=Decimal("12.49"),
        card="376674000000008",
        expiry_date="4912",
        cvv="123",
        order="ABCD1234",
    )
    assert isinstance(res.Ds_EMV3DS.threeDSServerTransID, str)


async def test_utility_club_international(guillotina_redsys):
    utility = get_utility(IRedsysUtility)
    # Diners Club International 1.0.2
    res = await utility.init_transaction(
        amount=Decimal("12.49"),
        card="36849800000018",
        expiry_date="4912",
        cvv="123",
        order="ABCD1234",
    )
    assert res["Ds_EMV3DS"]["protocolVersion"] == "NO_3DS_v2"
    res = await utility.threeds_method(payload=res)


async def test_utility_jcb_secure(guillotina_redsys):
    utility = get_utility(IRedsysUtility)
    # JCB JCB JSecure 1.0.2
    res = await utility.init_transaction(
        amount=Decimal("12.49"),
        card="3587870000000001",
        expiry_date="4912",
        cvv="123",
        order="ABCD1234",
    )
    assert res["Ds_EMV3DS"]["protocolVersion"] == "NO_3DS_v2"


def test_compute_signature():
    test_key = "sq7HjrUOBfKmC576ILgskD5srU870gJ7"
    order = "1234567890"
    merchant_example = "eyJEU19NRVJDSEFOVF9BTU9VTlQiOiI5OTkiLCJEU19NRVJDSEFOVF9PUkRFUiI6IjEyMzQ1Njc4OTAiLCJEU19NRVJDSEFOVF9NRVJDSEFOVENPREUiOiI5OTkwMDg4ODEiLCJEU19NRVJDSEFOVF9DVVJSRU5DWSI6Ijk3OCIsIkRTX01FUkNIQU5UX1RSQU5TQUNUSU9OVFlQRSI6IjAiLCJEU19NRVJDSEFOVF9URVJNSU5BTCI6IjEiLCJEU19NRVJDSEFOVF9NRVJDSEFOVFVSTCI6Imh0dHA6XC9cL3d3dy5wcnVlYmEuY29tXC91cmxOb3RpZmljYWNpb24ucGhwIiwiRFNfTUVSQ0hBTlRfVVJMT0siOiJodHRwOlwvXC93d3cucHJ1ZWJhLmNvbVwvdXJsT0sucGhwIiwiRFNfTUVSQ0hBTlRfVVJMS08iOiJodHRwOlwvXC93d3cucHJ1ZWJhLmNvbVwvdXJsS08ucGhwIn0"
    result = compute_redsys_signature(
        terminal_key=test_key, order=order, merchant_params_b64=merchant_example
    )
    # https://pagosonline.redsys.es/desarrolladores-inicio/documentacion-operativa/firmar-una-operacion/
    assert (
        result
        == "Vjo02eSWq249IeZZp3R-ArFnGLhKY0OuzDDlx1BuVtZDC2yhczA7_11uZhsYzLZBCMFAz8u8uzGDX3AErHKmmw"
    )
