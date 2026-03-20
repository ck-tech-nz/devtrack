from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Repo
from .serializers import RepoSerializer


class RepoListCreateView(generics.ListCreateAPIView):
    queryset = Repo.objects.all()
    serializer_class = RepoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # No pagination for repos list


class RepoDetailView(generics.RetrieveDestroyAPIView):
    queryset = Repo.objects.all()
    serializer_class = RepoSerializer
    permission_classes = [IsAuthenticated]
