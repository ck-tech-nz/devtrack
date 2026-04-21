from rest_framework import serializers
from .models import KPISnapshot


class KPITeamDeveloperSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id")
    user_name = serializers.CharField(source="user.name")
    avatar = serializers.CharField(source="user.avatar", default="")

    class Meta:
        model = KPISnapshot
        fields = ["user_id", "user_name", "avatar", "scores", "rankings"]
        read_only_fields = fields


class KPISummarySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id")
    user_name = serializers.CharField(source="user.name")
    avatar = serializers.CharField(source="user.avatar", default="")
    groups = serializers.SerializerMethodField()

    class Meta:
        model = KPISnapshot
        fields = ["user_id", "user_name", "avatar", "groups", "scores", "rankings", "period_start", "period_end", "computed_at"]
        read_only_fields = fields

    def get_groups(self, obj):
        return list(obj.user.groups.values_list("name", flat=True))
