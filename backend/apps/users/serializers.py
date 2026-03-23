from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .avatar_choices import AVATAR_CHOICES, random_avatar

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "github_id", "avatar"]


class MeSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "github_id", "avatar", "groups", "permissions", "settings", "is_superuser"]
        read_only_fields = ["id", "username", "groups", "permissions", "is_superuser"]

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    def get_permissions(self, obj):
        return list(obj.get_all_permissions())


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    name = serializers.CharField(max_length=50, required=False, default="")
    email = serializers.EmailField(required=False, default="")
    avatar = serializers.CharField(max_length=50, required=False, default="")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该用户名已被注册")
        return value

    def validate_avatar(self, value):
        if value and value not in AVATAR_CHOICES:
            raise serializers.ValidationError("无效的头像选择")
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "两次密码输入不一致"})
        validate_password(data["password"])
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        avatar = validated_data.pop("avatar", "") or random_avatar()
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            name=validated_data.get("name", ""),
            email=validated_data.get("email", ""),
            avatar=avatar,
            is_active=False,
        )
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "avatar", "github_id", "is_active", "date_joined", "groups"]

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    groups = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = User
        fields = ["name", "email", "avatar", "is_active", "groups"]

    def validate_avatar(self, value):
        if value and value not in AVATAR_CHOICES:
            raise serializers.ValidationError("无效的头像选择")
        return value

    def validate_groups(self, value):
        from django.contrib.auth.models import Group
        groups = []
        for name in value:
            try:
                groups.append(Group.objects.get(name=name))
            except Group.DoesNotExist:
                raise serializers.ValidationError(f"用户组 '{name}' 不存在")
        return groups

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("当前密码错误")
        return value

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "两次密码输入不一致"})
        validate_password(data["new_password"])
        return data
