from guillotina import configure


configure.permissions("redsys.PerformTransaction", "Allow to perform a transaction")
configure.grant(role="guillotina.Member", permission="redsys.PerformTransaction")
