from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.external.authentication import APIKeyAuthentication
from apps.permissions import FullDjangoModelPermissions
from apps.settings.models import ExternalAPIKey


class ExternalAPIDocsView(APIView):
    """返回外部 API 接口文档（结构化 JSON，便于前端渲染和 AI 读取）。"""
    permission_classes = [IsAuthenticated, FullDjangoModelPermissions]
    queryset = ExternalAPIKey.objects.none()

    def get(self, request):
        return Response({
            "title": "DevTrack 外部 API 接口文档",
            "version": "v1",
            "base_url": "/api/external",
            "authentication": {
                "type": "Bearer Token",
                "header": "Authorization: Bearer {api_key}",
                "description": "在 Django 管理后台创建 API Key，每个 Key 绑定一个项目和默认负责人。",
            },
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/api/external/issues/",
                    "summary": "创建问题",
                    "description": "外部平台提交反馈，自动在 DevTrack 中创建问题工单。",
                    "request_body": {
                        "content_type": "application/json",
                        "fields": [
                            {"name": "title", "type": "string", "required": True, "max_length": 200, "description": "问题标题"},
                            {"name": "type", "type": "string", "required": False, "default": "", "description": "反馈类型，映射为标签：bug/BUG→Bug, feature/功能建议→需求, improvement/体验改进→优化"},
                            {"name": "priority", "type": "string", "required": False, "default": "P2", "description": "优先级：P0(紧急), P1(高), P2(中), P3(低)"},
                            {"name": "description", "type": "string", "required": False, "default": "", "description": "问题详细描述"},
                            {"name": "module", "type": "string", "required": False, "default": "", "description": "所属模块，会作为标签添加"},
                            {"name": "source_feedback_id", "type": "string", "required": False, "default": "", "description": "外部平台反馈ID，用于去重和关联"},
                            {"name": "reporter", "type": "object", "required": False, "description": "报告人信息", "fields": [
                                {"name": "tenant_id", "type": "string", "description": "租户ID"},
                                {"name": "tenant_name", "type": "string", "description": "租户名称"},
                                {"name": "user_id", "type": "string", "description": "用户ID"},
                                {"name": "user_name", "type": "string", "description": "用户姓名"},
                                {"name": "contact", "type": "string", "description": "联系方式"},
                            ]},
                            {"name": "context", "type": "object", "required": False, "description": "上下文信息", "fields": [
                                {"name": "page_url", "type": "string", "description": "当前页面URL"},
                                {"name": "page_title", "type": "string", "description": "页面标题"},
                                {"name": "browser", "type": "string", "description": "浏览器信息"},
                                {"name": "os", "type": "string", "description": "操作系统"},
                                {"name": "resolution", "type": "string", "description": "屏幕分辨率"},
                                {"name": "navigation_path", "type": "array", "description": "导航路径"},
                                {"name": "console_errors", "type": "array", "description": "控制台错误"},
                            ]},
                            {"name": "attachments", "type": "array", "required": False, "description": "附件列表", "fields": [
                                {"name": "type", "type": "string", "description": "附件类型 (screenshot/file)"},
                                {"name": "url", "type": "string", "description": "附件URL"},
                            ]},
                        ],
                        "example": {
                            "title": "案件导入页面上传Excel后无响应",
                            "type": "bug",
                            "priority": "P1",
                            "description": "上传5MB的Excel文件后页面卡住不动",
                            "module": "case_management",
                            "source_feedback_id": "FB202604040001",
                            "reporter": {
                                "tenant_id": "T001",
                                "tenant_name": "XX催收公司",
                                "user_id": "U001",
                                "user_name": "张三",
                                "contact": "13800138000",
                            },
                            "context": {
                                "page_url": "/case/import",
                                "browser": "Chrome 120.0",
                                "os": "Windows 11",
                            },
                            "attachments": [
                                {"type": "screenshot", "url": "https://cdn.example.com/img.png"},
                            ],
                        },
                    },
                    "responses": [
                        {"status": 201, "description": "创建成功", "example": {
                            "id": 42,
                            "issue_number": "ISS-042",
                            "title": "案件导入页面上传Excel后无响应",
                            "status": "待处理",
                            "priority": "P1",
                            "created_at": "2026-04-04T10:00:00Z",
                        }},
                        {"status": 401, "description": "认证失败（API Key 无效或缺失）"},
                        {"status": 409, "description": "反馈ID重复", "example": {
                            "detail": "反馈已存在",
                            "existing_issue_id": 42,
                        }},
                    ],
                },
                {
                    "method": "GET",
                    "path": "/api/external/issues/",
                    "summary": "查询问题列表",
                    "description": "获取通过 API 创建的问题列表，支持分页和过滤。结果仅限当前 API Key 绑定的项目。",
                    "query_params": [
                        {"name": "feedback_id", "type": "string", "description": "按外部反馈ID过滤"},
                        {"name": "status", "type": "string", "description": "按状态过滤：待处理/进行中/已解决/已关闭"},
                        {"name": "priority", "type": "string", "description": "按优先级过滤：P0/P1/P2/P3"},
                        {"name": "page", "type": "integer", "description": "页码，默认 1"},
                        {"name": "page_size", "type": "integer", "description": "每页数量，默认 20，最大 100"},
                    ],
                    "responses": [
                        {"status": 200, "description": "成功", "example": {
                            "count": 25,
                            "next": "/api/external/issues/?page=2",
                            "previous": None,
                            "results": [{
                                "id": 42,
                                "issue_number": "ISS-042",
                                "title": "案件导入页面上传Excel后无响应",
                                "status": "待处理",
                                "priority": "P1",
                                "assignee": "bot",
                                "labels": ["Bug", "case_management"],
                                "created_at": "2026-04-04T10:00:00Z",
                                "updated_at": "2026-04-04T11:30:00Z",
                                "resolved_at": None,
                                "source_feedback_id": "FB202604040001",
                            }],
                        }},
                    ],
                },
                {
                    "method": "GET",
                    "path": "/api/external/issues/{id}/",
                    "summary": "查询单个问题",
                    "description": "获取指定问题的详细信息。只能查询当前 API Key 绑定项目中通过 API 创建的问题。",
                    "path_params": [
                        {"name": "id", "type": "integer", "description": "问题ID"},
                    ],
                    "responses": [
                        {"status": 200, "description": "成功", "example": {
                            "id": 42,
                            "issue_number": "ISS-042",
                            "title": "案件导入页面上传Excel后无响应",
                            "status": "进行中",
                            "priority": "P1",
                            "assignee": "李四",
                            "labels": ["Bug", "case_management"],
                            "created_at": "2026-04-04T10:00:00Z",
                            "updated_at": "2026-04-04T14:00:00Z",
                            "resolved_at": None,
                            "source_feedback_id": "FB202604040001",
                        }},
                        {"status": 404, "description": "问题不存在或不属于当前项目"},
                    ],
                },
            ],
            "error_format": {
                "description": "所有错误响应格式统一",
                "example": {"detail": "错误描述信息"},
            },
        })


class ExternalAPITestView(APIView):
    """验证 API Key 是否有效，返回绑定的项目和负责人信息。"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        if not hasattr(request, "api_key") or request.api_key is None:
            return Response(
                {"valid": False, "detail": "API Key 无效或未提供"},
                status=401,
            )
        key = request.api_key
        return Response({
            "valid": True,
            "key_name": key.name,
            "project": key.project.name,
            "default_assignee": key.default_assignee.name if key.default_assignee else None,
        })
