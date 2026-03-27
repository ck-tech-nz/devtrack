from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import GroupViewSet, PageRouteViewSet, PermissionViewSet

router = DefaultRouter()
router.register("routes", PageRouteViewSet, basename="pageroute")

urlpatterns = [
    path("", include(router.urls)),
    path("permissions/", PermissionViewSet.as_view({"get": "list", "post": "create"})),
    path("permissions/<int:pk>/", PermissionViewSet.as_view({"delete": "destroy"})),
    path("groups/", GroupViewSet.as_view({"get": "list", "post": "create"})),
    path("groups/<int:pk>/", GroupViewSet.as_view({"patch": "partial_update"})),
]
