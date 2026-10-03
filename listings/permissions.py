from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Изменять объявление/комментарий может только автор или staff."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "seller", None) or getattr(obj, "author", None)
        return owner == request.user or request.user.is_staff
