from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from apps.permissions import FullDjangoModelPermissions
from .serializers import (
    UserSerializer, MeSerializer, RegisterSerializer,
    AdminUserSerializer, AdminUserUpdateSerializer, ChangePasswordSerializer,
)

User = get_user_model()


class MeView(RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserSerializer
    permission_classes = [FullDjangoModelPermissions]


class UserDetailView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [FullDjangoModelPermissions]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def update(self, request, *args, **kwargs):
        """Use AdminUserUpdateSerializer for input but return AdminUserSerializer for response."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = AdminUserUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserSerializer(instance).data)


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "密码修改成功"})
