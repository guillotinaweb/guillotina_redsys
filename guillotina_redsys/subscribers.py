from guillotina import configure
from guillotina.interfaces import IContainer
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IRolePermissionManager


@configure.subscriber(for_=(IContainer, IObjectAddedEvent))
async def created_object(obj, event):
    manager = IRolePermissionManager(obj)
    manager.grant_permission_to_role_no_inherit(
        "guillotina.AccessContent", "guillotina.Anonymous"
    )
