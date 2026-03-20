from rest_framework import serializers
from django.contrib.auth import get_user_model

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
        fields = ["id", "username", "name", "email", "github_id", "avatar", "groups", "permissions"]

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    def get_permissions(self, obj):
        return list(obj.get_all_permissions())
