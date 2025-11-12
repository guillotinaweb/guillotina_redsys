import pytest


pytestmark = pytest.mark.asyncio


async def test_container(guillotina_redsys):
    resp, status = await guillotina_redsys("GET", "/db/guillotina/")
    assert status == 200
