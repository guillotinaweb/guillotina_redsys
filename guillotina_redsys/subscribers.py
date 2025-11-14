from guillotina import configure
from guillotina.interfaces import IContainer, IObjectAddedEvent, IRolePermissionManager


@configure.subscriber(for_=(IContainer, IObjectAddedEvent))
async def created_object(obj, event):
    manager = IRolePermissionManager(obj)
    manager.grant_permission_to_role_no_inherit(
        "guillotina.AccessContent", "guillotina.Anonymous"
    )
