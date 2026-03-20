from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import get_user_model
from .models import Issue, Activity
from .serializers import (
    IssueListSerializer, IssueDetailSerializer,
    IssueCreateUpdateSerializer, BatchUpdateSerializer,
)

User = get_user_model()


class IssueListCreateView(generics.ListCreateAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee")
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["priority", "status", "assignee", "project"]
    search_fields = ["title"]
    ordering_fields = ["created_at", "priority", "updated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IssueCreateUpdateSerializer
        return IssueListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        labels = self.request.query_params.get("labels")
        if labels:
            qs = qs.filter(labels__contains=[labels])
        return qs


class IssueDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Issue.objects.select_related("reporter", "assignee")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return IssueCreateUpdateSerializer
        return IssueDetailSerializer


class BatchUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BatchUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        issues = Issue.objects.filter(id__in=data["ids"])
        count = issues.count()

        if data["action"] == "assign":
            user = User.objects.get(id=data["value"])
            issues.update(assignee=user)
        elif data["action"] == "set_priority":
            issues.update(priority=data["value"])

        return Response({"updated": count})
