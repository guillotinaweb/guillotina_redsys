from guillotina import configure

import os


app_settings = {
    "load_utilities": {
        "redsys": {
            "provides": "guillotina_redsys.interfaces.IRedsysUtility",
            "factory": "guillotina_redsys.utility.RedsysUtility",
            "settings": {
                "merchant_code": os.environ.get("REDSYS_MERCHANT_CODE"),
                "terminal": os.environ.get("REDSYS_TERMINAL", "001"),
                "secret_key": os.environ.get("REDSYS_SECRET_KEY"),
                "url_redsys": os.environ.get(
                    "REDSYS_URL", "https://sis-t.redsys.es:25443/sis/rest"
                ),
                "threedsnotification_url": os.environ.get(
                    "REDSYS_3DS_NOTIFICATION_URL"
                ),
                "init_trata_peticion_notification_url": os.environ.get(
                    "REDSYS_INIT_TRATA_PETICION_NOTIFICATION_URL",
                    "https://sis-d.redsys.es/sis-simulador-web/SisRESTCreqCres_3DSecureV2.jsp",
                ),
            },
        }
    }
}


def includeme(root, settings):
    configure.scan("guillotina_redsys.utility")
    configure.scan("guillotina_redsys.api")
    configure.scan("guillotina_redsys.interfaces")
    configure.scan("guillotina_redsys.utils")
