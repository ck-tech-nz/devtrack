import factory
from faker import Faker
from django.contrib.auth import get_user_model
from apps.settings.models import SiteSettings
from apps.projects.models import Project, ProjectMember
from apps.issues.models import Issue, Activity
from apps.repos.models import Repo

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


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.LazyFunction(lambda: fake.catch_phrase())
    description = factory.LazyFunction(lambda: fake.paragraph())
    status = "进行中"


class ProjectMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectMember

    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = "member"


class IssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Issue

    project = factory.SubFactory(ProjectFactory)
    title = factory.LazyFunction(lambda: fake.sentence())
    description = factory.LazyFunction(lambda: fake.paragraph())
    priority = factory.Iterator(["P0", "P1", "P2", "P3"])
    status = "待处理"
    labels = factory.LazyFunction(lambda: [fake.random_element(["前端", "后端", "Bug"])])
    reporter = factory.SubFactory(UserFactory)


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activity

    user = factory.SubFactory(UserFactory)
    issue = factory.SubFactory(IssueFactory)
    action = "created"
    detail = ""


class RepoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Repo

    name = factory.LazyFunction(lambda: fake.word() + "-" + fake.word())
    full_name = factory.LazyAttribute(lambda o: f"org/{o.name}")
    url = factory.LazyAttribute(lambda o: f"https://github.com/{o.full_name}")
    description = factory.LazyFunction(lambda: fake.sentence())
    default_branch = "main"
    language = factory.Iterator(["Python", "TypeScript", "Go", "Java"])
    stars = factory.LazyFunction(lambda: fake.random_int(0, 500))
    status = "在线"
