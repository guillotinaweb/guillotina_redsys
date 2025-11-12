from guillotina import configure
from guillotina.api.service import Service
from guillotina.interfaces import IContainer


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.ViewContent",
    name="@defaultGet",
    summary="Get",
    responses={"200": {"description": "Get", "schema": {"properties": {}}}},
)
class RedsysGET(Service):
    async def __call__(self):
        pass
