from guillotina import testing
from guillotina.tests.fixtures import _update_from_pytest_markers

import json
import os
import pytest


def base_settings_configurator(settings):
    if "applications" not in settings:
        settings["applications"] = []
    settings["applications"].append("guillotina")
    settings["applications"].append("guillotina_redsys")
    # testing sandbox:
    # https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/
    settings["load_utilities"] = {
        "redsys": {
            "provides": "guillotina_redsys.interfaces.IRedsysUtility",
            "factory": "guillotina_redsys.utility.RedsysUtility",
            "settings": {
                "merchant_code": os.environ.get("REDSYS_MERCHANT_CODE", "999008881"),
                "terminal": os.environ.get("REDSYS_TERMINAL", "001"),
                "secret_key": os.environ.get(
                    "REDSYS_SECRET_KEY", "sq7HjrUOBfKmC576ILgskD5srU870gJ7"
                ),
                "url_redsys": os.environ.get(
                    "REDSYS_URL", "https://sis-t.redsys.es:25443/sis/rest"
                ),
                "container_url": os.environ.get(
                    "REDSYS_CONTAINER_URL", "https://foo-url.cat/db/container"
                ),
            },
        }
    }


testing.configure_with(base_settings_configurator)


@pytest.fixture(scope="function")
async def guillotina_redsys(guillotina):
    settings = testing.get_settings()
    settings = _update_from_pytest_markers(settings, None)
    testing.configure_with(base_settings_configurator)
    response, status = await guillotina(
        "POST", "/db/", data=json.dumps({"@type": "Container", "id": "guillotina"})
    )
    yield guillotina
