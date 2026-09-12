from rest_framework.permissions import BasePermission
from CNR_app.models import User

class HasRole(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and
            user.is_authenticated and
            user.role in self.allowed_roles
        )

class IsSuperAdmin(HasRole):
    allowed_roles = (User.Role.SUPER_ADMIN,)

class IsManagerOrAdmin(HasRole):
    allowed_roles = (User.Role.SUPER_ADMIN, User.Role.MANAGER)

class IsAccountantOrAdmin(HasRole):
    allowed_roles = (User.Role.SUPER_ADMIN, User.Role.ACCOUNTANT, User.Role.MANAGER)        