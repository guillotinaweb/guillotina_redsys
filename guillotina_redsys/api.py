from decimal import Decimal
from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import get_utility
from guillotina.contrib.redis import get_driver
from guillotina.interfaces import IContainer
from guillotina.interfaces import IResource
from guillotina_redsys.interfaces import IRedsysUtility


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


EXPIRATION_15_MIN = 60 * 15
EXPIRATION_30_MIN = 60 * 30


@configure.service(
    context=IContainer,
    method="POST",
    permission="redsys.Public",
    name="@notificationRedsys3DS/{order_id}/{three_dss_trans_id}",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class RedsysNotification3DS(Service):
    async def __call__(self):
        # Save the result of the 3DS notification taking into account
        # order_id, and transaction_id
        order_id = self.request.matchdict["order_id"]
        trans_id = self.request.matchdict["three_dss_trans_id"]
        payload = await self.request.json()
        result = payload.get("threeDSCompInd", "N")
        redis_driver = await get_driver()
        key_redis = f"notification_3DS:{order_id}:{trans_id}"
        await redis_driver.set(
            key=key_redis, data=result.encode("utf-8"), expire=EXPIRATION_15_MIN
        )


@configure.service(
    context=IContainer,
    method="GET",
    permission="redsys.Public",
    name="@getnotificationRedsys3DS/{order_id}/{three_dss_trans_id}",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class GetRedsysNotification3DS(Service):
    async def __call__(self):
        # get the result of the 3DS notification via redis
        order_id = self.request.matchdict["order_id"]
        trans_id = self.request.matchdict["three_dss_trans_id"]
        redis_driver = await get_driver()
        key_redis = f"notification_3DS:{order_id}:{trans_id}"
        result = await redis_driver.get(key_redis) or "N".encode("utf-8")
        return {"threeDSCompInd": result.decode("utf-8")}


@configure.service(
    context=IContainer,
    method="POST",
    permission="redsys.Public",
    name="@notificationRedsysChallenge/{order_id}/{three_dss_trans_id}",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class RedsysNotificationChallenge(Service):
    async def __call__(self):
        # Save the result of the 3DS notification taking into account
        # order_id, and transaction_id
        order_id = self.request.matchdict["order_id"]
        trans_id = self.request.matchdict["three_dss_trans_id"]
        payload = await self.request.json()
        result = payload.get("CRES", "")
        redis_driver = await get_driver()
        key_redis = f"notification_CRES:{order_id}:{trans_id}"
        await redis_driver.set(
            key=key_redis, data=result.encode("utf-8"), expire=EXPIRATION_30_MIN
        )


@configure.service(
    context=IContainer,
    method="POST",
    permission="redsys.Public",
    name="@performNotificationRedsysChallenge/{order_id}/{three_dss_trans_id}",
    summary="Starts a transaction",
    responses={"200": {"description": "Post", "schema": {"properties": {}}}},
)
class GetRedsysNotificationChallenge(Service):
    async def __call__(self):
        payload = await self.request.json()
        amount = payload["amount"]
        card = payload["card"]
        expiry_date = payload["expiry_date"]
        cvv = payload["cvv"]
        protocol = payload["protocol_version"]
        currency = payload.get("currency", 978)
        order_id = self.request.matchdict["order_id"]
        trans_id = self.request.matchdict["three_dss_trans_id"]
        redis_driver = await get_driver()
        key_redis = f"notification_CRES:{order_id}:{trans_id}"
        result = await redis_driver.get(key=key_redis)
        if result is None:
            return None
        utility = get_utility(IRedsysUtility)
        res = await utility.authenticate_cres(
            amount=Decimal(amount),
            card=card,
            cvv=cvv,
            expiry_date=expiry_date,
            protocol_version=protocol,
            order=order_id,
            currency=currency,
            cres=result.decode("utf-8"),
        )
        return res.dict()
