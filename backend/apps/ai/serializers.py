from rest_framework import serializers


class AnalysisResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    updated_at = serializers.DateTimeField(allow_null=True)
    is_fresh = serializers.BooleanField(default=True)
    result = serializers.JSONField(allow_null=True)
    error_message = serializers.CharField(allow_null=True, required=False)
