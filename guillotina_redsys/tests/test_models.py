from decimal import Decimal
from guillotina.component import get_utility
from guillotina_redsys.interfaces import IRedsysUtility
from guillotina_redsys.models import RedsysForm
from guillotina_redsys.models import RedsysMerchantParams

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


async def test_utility(guillotina_redsys):
    utility = get_utility(IRedsysUtility)
    merchant = utility.build_merchant(amount=Decimal("12.49"), order="ABCD1234")
    payload = merchant.to_redsys_dict()
    assert payload == {
        "Ds_Merchant_Amount": "1249",
        "Ds_Merchant_Currency": "978",
        "Ds_Merchant_MerchantCode": "123456789",
        "Ds_Merchant_Order": "ABCD1234",
        "Ds_Merchant_Terminal": "001",
        "Ds_Merchant_TransactionType": "0",
    }
    form = utility.build_form(merchant)
    assert form == {
        "Ds_MerchantParameters": "eyJEc19NZXJjaGFudF9BbW91bnQiOiIxMjQ5IiwiRHNfTWVyY2hhbnRfQ3VycmVuY3kiOiI5NzgiLCJEc19NZXJjaGFudF9NZXJjaGFudENvZGUiOiIxMjM0NTY3ODkiLCJEc19NZXJjaGFudF9PcmRlciI6IkFCQ0QxMjM0IiwiRHNfTWVyY2hhbnRfVGVybWluYWwiOiIwMDEiLCJEc19NZXJjaGFudF9UcmFuc2FjdGlvblR5cGUiOiIwIn0=",
        "Ds_Signature": "xWRjkaw-EwqkFa4thFiPfv1P5oEDl3mJXk79QnU9KDZtXVjNg0QVJbEVEGfpxRChUg1psFx-OChuFCFNpCBjhQ",
        "Ds_SignatureVersion": "HMAC_SHA512_V2",
    }
