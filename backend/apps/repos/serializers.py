from rest_framework import serializers
from .models import Repo


class RepoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repo
        fields = [
            "id", "name", "full_name", "url", "description",
            "default_branch", "language", "stars", "status", "connected_at",
        ]
        read_only_fields = ["id", "connected_at"]
