"""Central definitions and authorization helpers for account role groups.

Account roles are intentionally kept separate from content-facing labels such as
``MemberContentItem.role``. Add a new account role here and the authorization
and role-management APIs will pick it up automatically.
"""

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    USER = 'user'
    ADMIN = 'admin'
    SUPERADMIN = 'superadmin'


class Permission(str, Enum):
    ADMIN_ACCESS = 'admin.access'
    MANAGE_ROLES = 'roles.manage'


@dataclass(frozen=True)
class RoleGroup:
    name: str
    rank: int
    permissions: frozenset[str]
    assignable: bool = True

    def to_dict(self):
        return {
            'name': self.name,
            'rank': self.rank,
            'permissions': sorted(self.permissions),
            'assignable': self.assignable,
        }


ROLE_GROUPS = {
    Role.USER.value: RoleGroup(
        name=Role.USER.value,
        rank=10,
        permissions=frozenset(),
    ),
    Role.ADMIN.value: RoleGroup(
        name=Role.ADMIN.value,
        rank=50,
        permissions=frozenset({Permission.ADMIN_ACCESS.value}),
    ),
    Role.SUPERADMIN.value: RoleGroup(
        name=Role.SUPERADMIN.value,
        rank=100,
        permissions=frozenset({
            Permission.ADMIN_ACCESS.value,
            Permission.MANAGE_ROLES.value,
        }),
        # The configured root account is the only superadmin. Its role is not
        # assignable through the role-management API.
        assignable=False,
    ),
}

DEFAULT_ROLE = Role.USER.value


def get_role_group(role):
    """Return a role group, or ``None`` for an unknown/legacy database value."""
    if isinstance(role, Role):
        role = role.value
    return ROLE_GROUPS.get(role)


def has_permission(role, permission):
    group = get_role_group(role)
    permission_value = permission.value if isinstance(permission, Permission) else permission
    return bool(group and permission_value in group.permissions)


def assignable_role_names():
    return [group.name for group in ROLE_GROUPS.values() if group.assignable]


def serialized_role_groups():
    return [group.to_dict() for group in ROLE_GROUPS.values()]
