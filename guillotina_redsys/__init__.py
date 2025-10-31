from guillotina import configure


app_settings = {
    "load_utilities": {
        "redsys": {
            "provides": "guillotina_redsys.interfaces.IRedsysUtility",
            "factory": "guillotina_redsys.utility.RedsysUtility"
        }
    }
}


def includeme(root, settings):
    configure.scan("guillotina_redsys.utility")
    configure.scan("guillotina_redsys.api")
    configure.scan("guillotina_redsys.interfaces")
