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
    settings["load_utilities"] = {
        "redsys": {
            "provides": "guillotina_redsys.interfaces.IRedsysUtility",
            "factory": "guillotina_redsys.utility.RedsysUtility",
            "settings": {
                "merchant_code": os.environ.get("REDSYS_MERCHANT_CODE", "123456789"),
                "terminal": os.environ.get("REDSYS_TERMINAL", "001"),
                "secret_key": os.environ.get("REDSYS_SECRET_KEY", "DUMMY_KEY_TERMINAL"),
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
