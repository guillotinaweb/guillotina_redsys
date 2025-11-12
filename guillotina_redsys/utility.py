from decimal import Decimal
from guillotina_redsys.models import RedsysForm
from guillotina_redsys.models import RedsysMerchantParams


class RedsysUtility:
    def __init__(self, settings=None, loop=None):
        self._settings = settings
        self.terminal = self._settings["terminal"]
        self.secret_key = self._settings["secret_key"]
        self.merchant_code = self._settings["merchant_code"]

    def build_merchant(
        self, amount: Decimal, order: str, transaction_type="0", currency=978
    ):
        return RedsysMerchantParams.from_euros(
            amount_eur=amount,
            currency_numeric=currency,
            merchant_code=self.merchant_code,
            order=order,
            terminal=self.terminal,
            transaction_type=transaction_type,
        )

    def build_form(self, merchant: RedsysMerchantParams) -> dict:
        form = RedsysForm.from_merchant(
            merchant=merchant,
            terminal_key=self.secret_key,
        )
        return form.dict()

    async def initialize(self):
        pass

    async def finalize(self):
        pass
