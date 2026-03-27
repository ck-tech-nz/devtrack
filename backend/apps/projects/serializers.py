from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectMember

User = get_user_model()


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    avatar = serializers.URLField(source="user.avatar", read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["user_id", "user_name", "avatar", "role"]


class ProjectMemberCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=["owner", "admin", "member"])

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("用户不存在")
        return value


class ProjectListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    issue_count = serializers.SerializerMethodField()
    repos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "repos",
            "member_count", "issue_count", "created_at", "updated_at",
        ]

    def get_member_count(self, obj):
        return obj.project_members.count()

    def get_issue_count(self, obj):
        return obj.issues.count() if hasattr(obj, "issues") else 0


class ProjectDetailSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(source="project_members", many=True, read_only=True)
    repos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "repos",
            "members", "created_at", "updated_at",
        ]


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "name", "description", "status", "remark",
            "estimated_completion", "actual_hours", "repos",
        ]
