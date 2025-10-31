import pytest
from decimal import Decimal
from guillotina_redsys.models import RedsysMerchantParams

pytestmark = pytest.mark.asyncio


async def test_models():
    params = RedsysMerchantParams.from_euros(
        amount_eur=Decimal("12.49"),
        currency_numeric=978,                 # EUR
        merchant_code="123456789",            # FUC
        order="ABCD1234",                     # 4–12 alnum
        terminal="001",
        transaction_type="0",                 # Auth
    )
    payload = params.to_redsys_dict()
    assert payload == {
        'Ds_Merchant_Amount': '1249',
        'Ds_Merchant_Currency': '978',
        'Ds_Merchant_MerchantCode': '123456789',
        'Ds_Merchant_Order': 'ABCD1234',
        'Ds_Merchant_Terminal': '001',
        'Ds_Merchant_TransactionType': '0'
    }
