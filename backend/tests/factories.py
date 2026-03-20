import factory
from faker import Faker
from django.contrib.auth import get_user_model
from apps.settings.models import SiteSettings

fake = Faker("zh_CN")
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(lambda: fake.user_name())
    name = factory.LazyFunction(lambda: fake.name())
    email = factory.LazyFunction(lambda: fake.email())
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class SiteSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteSettings
        django_get_or_create = ("id",)

    id = 1
    labels = ["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"]
    priorities = ["P0", "P1", "P2", "P3"]
    issue_statuses = ["待处理", "进行中", "已解决", "已关闭"]
