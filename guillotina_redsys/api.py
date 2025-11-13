from guillotina import configure
from guillotina.api.service import Service
from guillotina.interfaces import IResource, IContainer
from guillotina.component import get_utility
from guillotina_redsys.interfaces import IRedsysUtility
from decimal import Decimal


@configure.service(
    context=IResource,
    method="POST",
    permission="redsys.PerformTransaction",
    name="@initTransactionRedsys",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class initTransactionRedsys(Service):
    async def __call__(self):
        utility = get_utility(IRedsysUtility)
        payload = await self.request.json()
        amount = Decimal(payload["amount"])
        card = payload["card"]
        expiry_date = payload["expiry_date"]
        cvv = payload["cvv"]
        order = payload["order_id"]
        res = await utility.init_transaction(
            amount=amount,
            card=card,
            expiry_date=expiry_date,
            cvv=cvv,
            order=order,
        )
        return res.dict()


@configure.service(
    context=IResource,
    method="POST",
    permission="redsys.PerformTransaction",
    name="@initThreeDS",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class initThreeDS(Service):
    async def __call__(self):
        utility = get_utility(IRedsysUtility)
        payload = await self.request.json()
        transaction_id = payload["transaction_id"]
        three_method_url = payload["three_method_url"]
        res_3ds = await utility.init_threeds_method(
            transaction_id=transaction_id, three_method_url=three_method_url
        )
        return res_3ds.dict()


@configure.service(
    context=IResource,
    method="POST",
    permission="redsys.PerformTransaction",
    name="@initTrataPeticion",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class initTrataPeticion(Service):
    async def __call__(self):
        utility = get_utility(IRedsysUtility)
        payload = await self.request.json()
        transaction_id = payload["transaction_id"]
        amount = payload["amount"]
        card = payload["card"]
        expiry_date = payload["expiry_date"]
        cvv = payload["cvv"]
        order = payload["order_id"]
        protocol = payload["protocol_version"]
        three_ds_comp_ind = payload["three_ds_comp_ind"]

        res_3ds_trata = await utility.init_trata_peticion(
            amount=Decimal(amount),
            card=card,
            expiry_date=expiry_date,
            cvv=cvv,
            order=order,
            protocol_version=protocol,
            transaction_id=transaction_id,
            three_ds_comp_ind=three_ds_comp_ind,
        )
        return res_3ds_trata.dict()


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.Anonymous",
    name="@notificationRedsys",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class RedsysNotification(Service):
    async def __call__(self):
        utility = get_utility(IRedsysUtility)
        payload = await self.request.json()
        three_ds_comp_ind = payload.get("threeDSCompInd")
        transaction_id = payload["transaction_id"]
        amount = payload["amount"]
