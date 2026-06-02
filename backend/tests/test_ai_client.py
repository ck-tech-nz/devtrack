"""LLMClient.list_model_ids 解析回归测试。

复现并防回归:base_url 指向网页(返回 HTML)或服务把模型写成纯字符串数组时,
旧实现(openai SDK models.list)会抛出晦涩的
'str' object has no attribute '_set_private_attributes'。新实现裸 HTTP 解析,
对非标准响应给出可读错误,并同时兼容对象/字符串两种 data 格式。
"""

from unittest.mock import patch

import httpx
import pytest

from apps.ai.client import LLMClient
from apps.ai.models import LLMConfig


class _FakeResp:
    def __init__(self, *, content_type="application/json", payload=None, status=200):
        self.headers = {"content-type": content_type}
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        return self._payload


def _client(base_url="https://api.example.com/v1", api_key="k") -> LLMClient:
    # 内存 LLMConfig,不触达数据库。
    return LLMClient(LLMConfig(name="x", base_url=base_url, api_key=api_key))


@patch("apps.ai.client.httpx.get")
def test_list_model_ids_object_format(mock_get):
    """标准 OpenAI 格式:data 为 [{"id": ...}]。"""
    mock_get.return_value = _FakeResp(
        payload={"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
    )
    assert _client().list_model_ids() == ["gpt-4o", "gpt-4o-mini"]
    # 走到 {base_url}/models,并带上 Bearer 头。
    called_url = mock_get.call_args.args[0]
    assert called_url == "https://api.example.com/v1/models"
    assert mock_get.call_args.kwargs["headers"]["Authorization"] == "Bearer k"


@patch("apps.ai.client.httpx.get")
def test_list_model_ids_string_format(mock_get):
    """部分本地推理服务:data 为纯字符串数组,结果去重并排序。"""
    mock_get.return_value = _FakeResp(payload={"data": ["m2", "m1", "m2"]})
    assert _client().list_model_ids() == ["m1", "m2"]


@patch("apps.ai.client.httpx.get")
def test_list_model_ids_html_page_raises_readable_error(mock_get):
    """base_url 指向网页(返回 HTML)时,给出可读错误而非 pydantic 内部报错。"""
    mock_get.return_value = _FakeResp(content_type="text/html; charset=utf-8", payload=None)
    with pytest.raises(ValueError, match="网页"):
        _client(base_url="http://172.16.1.176:8080/v1").list_model_ids()
