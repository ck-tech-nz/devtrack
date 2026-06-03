import pytest
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_list_includes_is_superuser(superuser_client):
    UserFactory(is_superuser=False)
    resp = superuser_client.get("/api/users/")
    assert resp.status_code == 200
    rows = resp.json()["results"]
    assert rows, "expected at least one user in results"
    assert all("is_superuser" in row for row in rows)
