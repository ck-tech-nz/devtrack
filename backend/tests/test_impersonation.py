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


from rest_framework_simplejwt.tokens import AccessToken


def test_superuser_can_impersonate_regular_user(superuser_client):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 200
    body = resp.json()
    assert "access" in body and "refresh" in body
    token = AccessToken(body["access"])
    # simplejwt 5.5+ 把 user_id claim 序列化为字符串（兼容 UUID 主键），故需转回 int 比较
    assert int(token["user_id"]) == target.id
    assert token["impersonated_by"] is not None


def test_can_impersonate_staff_non_superuser(superuser_client):
    target = UserFactory(is_superuser=False, is_staff=True, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 200


def test_cannot_impersonate_superuser(superuser_client):
    target = UserFactory(is_superuser=True, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 403


def test_cannot_impersonate_inactive_user(superuser_client):
    target = UserFactory(is_superuser=False, is_active=False)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 400


def test_target_not_found_returns_404(superuser_client):
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": 99999999})
    assert resp.status_code == 404


def test_regular_user_cannot_impersonate(regular_client):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = regular_client.post("/api/auth/impersonate/", {"user_id": target.id})
    assert resp.status_code == 403


def test_nested_impersonation_rejected(superuser_client):
    target = UserFactory(is_superuser=False, is_active=True)
    other = UserFactory(is_superuser=False, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    access = resp.json()["access"]
    # 用全新客户端，仅凭模拟态 access token 鉴权（避免 force_authenticate 把 request.auth 置空）
    from rest_framework.test import APIClient
    impersonated = APIClient()
    impersonated.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    resp2 = impersonated.post("/api/auth/impersonate/", {"user_id": other.id})
    assert resp2.status_code == 403
    # 必须由嵌套守卫返回，而非 is_superuser 校验（两者 detail 不同）
    assert resp2.json()["detail"] == "不可嵌套模拟"


def test_impersonation_refresh_token_is_short_lived(superuser_client):
    target = UserFactory(is_superuser=False, is_active=True)
    resp = superuser_client.post("/api/auth/impersonate/", {"user_id": target.id})
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken(resp.json()["refresh"])
    assert refresh["exp"] - refresh["iat"] <= 3600
