from rest_framework.permissions import BasePermission

from apps.projects.models import ProjectMember


class IsProjectMember(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    @staticmethod
    def can_access_project(user, project_id: int) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return ProjectMember.objects.filter(project_id=project_id, user=user).exists()


class IsProjectManagerOrSuperuser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    @staticmethod
    def can_manage_project(user, project_id: int) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return ProjectMember.objects.filter(
            project_id=project_id,
            user=user,
            is_manager=True,
        ).exists()
