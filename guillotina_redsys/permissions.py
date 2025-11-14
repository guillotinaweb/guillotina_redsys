from guillotina import configure


configure.permission("redsys.Public", "Public access to content of redsys")
configure.permission("redsys.PerformTransaction", "Allow to perform a transaction")
configure.grant(role="guillotina.Member", permission="redsys.PerformTransaction")
configure.grant(role="guillotina.Manager", permission="redsys.PerformTransaction")
configure.grant(permission="redsys.Public", role="guillotina.Anonymous")
configure.grant(permission="redsys.Public", role="guillotina.Manager")
configure.grant(permission="redsys.Public", role="guillotina.Member")
