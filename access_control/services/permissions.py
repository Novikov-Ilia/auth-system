from rest_framework import exceptions
from django.db.models import Q
from users.models import User
from ..models import BusinessElement, AccessRoleRule


class Permissions:
    def _check(self, user: User, case: str, rr: AccessRoleRule, owner_id: int) -> None:
        if (
            getattr(rr, case+'_all_permission') or
            (owner_id == user.id and getattr(rr, case+'_permission'))
        ):
            return None
    
        raise exceptions.PermissionDenied("Доступ к элементу запрещён.")

    def check_permission(self, user: User, element_code: str, action: str, owner_id: int = None) -> None:
        if user is None or not user.is_authenticated:
            raise exceptions.NotAuthenticated
        
        be = BusinessElement.objects.filter(code=element_code).first()
        rr = AccessRoleRule.objects.filter(Q(role=user.role) & Q(element=be)).first()
        if not (be and rr):
            raise exceptions.PermissionDenied("Доступ к элементу запрещён.")

        match action:
            case 'read':
                return self._check(user, 'read', rr, owner_id)
            
            case 'update':
                return self._check(user, 'update', rr, owner_id)

            case 'delete':
                return self._check(user, 'delete', rr, owner_id)
            
            case 'create':
                if not rr.create_permission:
                    raise exceptions.PermissionDenied("Доступ к элементу запрещён.")
                
                return None

            case _:
                raise exceptions.PermissionDenied('Данное действие не поддерживается')

            