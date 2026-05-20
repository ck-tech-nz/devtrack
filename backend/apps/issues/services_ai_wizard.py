"""AI wizard service — three-stage LLM pipeline that drafts an Issue from a
free-form bug description. Used by the SSE endpoint POST /api/issues/ai-draft/.
"""
import json
import logging
from dataclasses import dataclass

from apps.ai.client import LLMClient
from apps.ai.models import Prompt


logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 20


@dataclass
class AiWizardError(Exception):
    step: int
    code: str
    message: str

    def __str__(self):
        return f"[step {self.step}] {self.code}: {self.message}"


# 每个阶段的预期字段;格式为 (key, type, optional)。
# 在下游代码信任 LLM 输出之前先校验形状,防止幻觉字段污染入库数据
SCHEMA_CLASSIFY = [("category", str, False), ("scope", str, False)]
SCHEMA_EXTRACT = [("title", str, False), ("priority", str, False), ("module", str, False)]
SCHEMA_GENERATE = [
    ("repro_steps", str, True),
    ("expected_behavior", str, True),
    ("labels", list, True),
    ("follow_up_questions", list, True),
]

SCHEMA_ONESHOT = [
    ("title", str, False),
    ("priority", str, False),
    ("module", str, False),
    ("repro_steps", str, True),
    ("expected_behavior", str, True),
    ("labels", list, True),
    ("follow_up_questions", list, True),
    ("inferred_env", str, True),
]

ONESHOT_TIMEOUT_SECONDS = 25
ONESHOT_RETRY_COUNT = 1   # one retry on bad JSON (total 2 attempts)

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB

ALLOWED_PRIORITIES = {"P0", "P1", "P2", "P3"}


def _read_attachment_bytes(file_key: str) -> bytes:
    """Module-level indirection so tests can patch the storage read."""
    from apps.tools.storage import read_object
    return read_object(file_key)


def _validate_shape(step: int, slug: str, data, schema):
    """Validate parsed LLM output against expected shape.

    - Required field missing or wrong type → raise AiWizardError.
    - Optional field missing or wrong type → coerce to default. LLMs occasionally
      emit `follow_up_questions: null` or `labels: "..."` instead of a list; we
      shouldn't abort the whole wizard over a recoverable optional field.
    """
    if not isinstance(data, dict):
        raise AiWizardError(step=step, code="llm_bad_shape", message=f"{slug} 返回非对象")
    for key, expected_type, optional in schema:
        if key not in data or not isinstance(data[key], expected_type):
            if optional:
                data[key] = "" if expected_type is str else (expected_type())
                continue
            raise AiWizardError(
                step=step, code="llm_bad_shape",
                message=(
                    f"{slug} 缺少字段 {key}" if key not in data
                    else f"{slug} 字段 {key} 类型错误（期望 {expected_type.__name__}）"
                ),
            )
    return data


class AiWizardService:
    """Three-stage LLM pipeline for the issue creation wizard.

    Each stage:
      1. classify(description) → {category, scope}
      2. extract(description, classify, modules) → {title, priority, module}
      3. generate(description, classify, extract, labels) → {repro_steps, expected_behavior, labels}

    On any LLM failure or malformed JSON, raises AiWizardError carrying the
    failed step number and a typed error code for the SSE layer to relay.
    """

    def _run_prompt(self, step: int, slug: str, **format_kwargs) -> dict:
        prompt = Prompt.objects.filter(slug=slug, is_active=True).first()
        if prompt is None:
            raise AiWizardError(step=step, code="missing_prompt", message=f"未配置 Prompt: {slug}")

        config = prompt.llm_config

        try:
            user_prompt = prompt.user_prompt_template.format(**format_kwargs)
        except KeyError as e:
            raise AiWizardError(step=step, code="prompt_format_error", message=f"模板缺失变量 {e}")

        try:
            raw = LLMClient(config).complete(
                model=prompt.llm_model,
                system_prompt=prompt.system_prompt,
                user_prompt=user_prompt,
                temperature=prompt.temperature,
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except Exception as e:
            logger.warning("wizard step=%s LLM call failed: %s", step, e, exc_info=True)
            raise AiWizardError(step=step, code="llm_call_failed", message="AI 调用失败，请重试")

        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("wizard step=%s bad JSON: %r", step, raw)
            raise AiWizardError(step=step, code="llm_bad_json", message="AI 返回格式异常，请重试")

    def classify(self, description: str) -> dict:
        result = self._run_prompt(step=1, slug="wizard_classify", description=description)
        return _validate_shape(1, "wizard_classify", result, SCHEMA_CLASSIFY)

    def extract(self, description: str, classify: dict, modules: list) -> dict:
        result = self._run_prompt(
            step=2,
            slug="wizard_extract",
            description=description,
            classify_json=json.dumps(classify, ensure_ascii=False),
            modules_json=json.dumps(modules, ensure_ascii=False),
        )
        result = _validate_shape(2, "wizard_extract", result, SCHEMA_EXTRACT)
        # 将 priority 限定在合法集合,默认 P2
        if result.get("priority") not in ALLOWED_PRIORITIES:
            result["priority"] = "P2"
        # 截断 title 以避免幻觉超长字符串
        result["title"] = (result.get("title") or "")[:200]
        # module 必须是字符串,且限定在已知模块列表 (或退回到"其他")
        mod = result.get("module") or ""
        if modules and mod not in modules:
            mod = "其他" if "其他" in modules else (modules[0] if modules else "")
        result["module"] = mod
        return result

    def generate(self, description: str, classify: dict, extract: dict, labels: list) -> dict:
        result = self._run_prompt(
            step=3,
            slug="wizard_generate",
            description=description,
            classify_json=json.dumps(classify, ensure_ascii=False),
            extract_json=json.dumps(extract, ensure_ascii=False),
            labels_json=json.dumps(labels, ensure_ascii=False),
        )
        result = _validate_shape(3, "wizard_generate", result, SCHEMA_GENERATE)
        # 过滤 labels 到已知集合,最多 3 个
        raw_labels = result.get("labels") or []
        if not isinstance(raw_labels, list):
            raw_labels = []
        valid_set = set(labels)
        result["labels"] = [l for l in raw_labels if isinstance(l, str) and l in valid_set][:3]
        # 限制追问数量与单条长度
        raw_q = result.get("follow_up_questions") or []
        if not isinstance(raw_q, list):
            raw_q = []
        result["follow_up_questions"] = [str(q)[:100] for q in raw_q if q][:3]
        # 截断长字符串
        result["repro_steps"] = (result.get("repro_steps") or "")[:2000]
        result["expected_behavior"] = (result.get("expected_behavior") or "")[:500]
        return result

    def oneshot_revise(
        self,
        current_draft: dict,
        instruction: str,
        images: list[tuple[str, bytes]],
    ) -> dict:
        """Single multimodal LLM call that either (a) returns an updated draft
        based on the user instruction, or (b) signals 'submit' when the user
        is just confirming the existing draft (e.g. "OK"/"好的"/"提交吧")。

        Return shape:
          - {"action": "submit"}                        when LLM classifies as confirm
          - {"action": "update", ...draft fields}       when LLM revised the draft

        Caller (stream_revise) decides which SSE event to emit based on action.
        Frontend's existing 'draft' event handler still works since the update
        case carries all standard draft fields alongside the action tag.

        Retries once on bad JSON; on vision failure falls back to text-only.
        """
        from apps.ai.services import parse_json_response
        from apps.settings.models import SiteSettings

        prompt = Prompt.objects.filter(slug="wizard_revise", is_active=True).first()
        if prompt is None:
            raise AiWizardError(step=1, code="missing_prompt", message="未配置 Prompt: wizard_revise")

        config = prompt.llm_config

        site = SiteSettings.get_solo()
        modules = list(site.modules or [])
        labels_dict = site.labels or {}
        labels_list = list(labels_dict.keys()) if isinstance(labels_dict, dict) else list(labels_dict)

        # 只把白名单字段送给 LLM, 避免前端塞额外噪声 (例如 v 号/版本元数据)
        sanitized = {
            "title": (current_draft.get("title") or "")[:200],
            "priority": current_draft.get("priority") or "P2",
            "module": current_draft.get("module") or "",
            "repro_steps": (current_draft.get("repro_steps") or "")[:2000],
            "expected_behavior": (current_draft.get("expected_behavior") or "")[:500],
            "labels": [l for l in (current_draft.get("labels") or []) if isinstance(l, str)][:10],
            "follow_up_questions": [
                str(q)[:200] for q in (current_draft.get("follow_up_questions") or []) if q
            ][:5],
            "inferred_env": (current_draft.get("inferred_env") or "")[:200],
        }

        try:
            user_prompt = prompt.user_prompt_template.format(
                current_draft_json=json.dumps(sanitized, ensure_ascii=False),
                instruction=instruction,
                modules_json=json.dumps(modules, ensure_ascii=False),
                labels_json=json.dumps(labels_list, ensure_ascii=False),
            )
        except KeyError as e:
            raise AiWizardError(step=1, code="prompt_format_error", message=f"模板缺失变量 {e}")

        client = LLMClient(config)
        vision_warning = None
        attempts_left = ONESHOT_RETRY_COUNT + 1
        current_images = list(images)
        parsed = None

        while attempts_left > 0:
            attempts_left -= 1
            try:
                raw = client.complete_multimodal(
                    model=prompt.llm_model,
                    system_prompt=prompt.system_prompt,
                    user_prompt=user_prompt,
                    images=current_images,
                    temperature=prompt.temperature,
                    timeout=ONESHOT_TIMEOUT_SECONDS,
                )
            except Exception as e:
                if current_images:
                    logger.warning("wizard_revise vision call failed, falling back to text-only: %s", e)
                    vision_warning = "AI 未能读取截图,已基于文字修订"
                    current_images = []
                    attempts_left += 1
                    continue
                logger.warning("wizard_revise LLM call failed: %s", e, exc_info=True)
                raise AiWizardError(step=1, code="llm_call_failed", message="AI 调用失败,请重试")

            try:
                parsed = parse_json_response(raw)
                break
            except (json.JSONDecodeError, ValueError):
                if attempts_left == 0:
                    logger.warning("wizard_revise bad JSON after retries: %r", raw)
                    raise AiWizardError(step=1, code="llm_bad_json", message="AI 返回格式异常,请重试")

        # action 分类: submit 路径直接短路返回, 不走 draft schema 校验
        if isinstance(parsed, dict) and parsed.get("action") == "submit":
            return {"action": "submit"}

        # update 路径 (action 缺失也视为 update, 兼容老 prompt) - 走标准 draft 校验
        if isinstance(parsed, dict):
            parsed.pop("action", None)
        parsed = _validate_shape(1, "wizard_revise", parsed, SCHEMA_ONESHOT)
        self._sanitize_oneshot(parsed, modules, labels_list)
        if vision_warning:
            parsed["follow_up_questions"] = [vision_warning] + list(parsed.get("follow_up_questions") or [])
            parsed["follow_up_questions"] = parsed["follow_up_questions"][:3]
        parsed["action"] = "update"
        return parsed

    def oneshot_draft(self, description: str, images: list[tuple[str, bytes]]) -> dict:
        """Single multimodal LLM call that produces a complete draft.

        Returns the merged shape (title/priority/module/repro_steps/
        expected_behavior/labels/follow_up_questions/inferred_env). On vision
        failure, retries text-only and prepends a follow_up_question warning.
        On bad JSON, retries once.
        """
        from apps.ai.services import parse_json_response
        from apps.settings.models import SiteSettings

        prompt = Prompt.objects.filter(slug="wizard_oneshot", is_active=True).first()
        if prompt is None:
            raise AiWizardError(step=1, code="missing_prompt", message="未配置 Prompt: wizard_oneshot")

        config = prompt.llm_config

        site = SiteSettings.get_solo()
        modules = list(site.modules or [])
        labels_dict = site.labels or {}
        labels_list = list(labels_dict.keys()) if isinstance(labels_dict, dict) else list(labels_dict)

        try:
            user_prompt = prompt.user_prompt_template.format(
                description=description,
                modules_json=json.dumps(modules, ensure_ascii=False),
                labels_json=json.dumps(labels_list, ensure_ascii=False),
            )
        except KeyError as e:
            raise AiWizardError(step=1, code="prompt_format_error", message=f"模板缺失变量 {e}")

        client = LLMClient(config)
        vision_warning = None
        attempts_left = ONESHOT_RETRY_COUNT + 1
        current_images = list(images)
        parsed = None

        while attempts_left > 0:
            attempts_left -= 1
            try:
                raw = client.complete_multimodal(
                    model=prompt.llm_model,
                    system_prompt=prompt.system_prompt,
                    user_prompt=user_prompt,
                    images=current_images,
                    temperature=prompt.temperature,
                    timeout=ONESHOT_TIMEOUT_SECONDS,
                )
            except Exception as e:
                if current_images:
                    logger.warning("wizard_oneshot vision call failed, falling back to text-only: %s", e)
                    vision_warning = "AI 未能读取截图，已基于文字生成"
                    current_images = []
                    # 视觉失败不消耗 JSON 重试预算
                    attempts_left += 1
                    continue
                logger.warning("wizard_oneshot LLM call failed: %s", e, exc_info=True)
                raise AiWizardError(step=1, code="llm_call_failed", message="AI 调用失败，请重试")

            try:
                parsed = parse_json_response(raw)
                break
            except (json.JSONDecodeError, ValueError):
                if attempts_left == 0:
                    logger.warning("wizard_oneshot bad JSON after retries: %r", raw)
                    raise AiWizardError(step=1, code="llm_bad_json", message="AI 返回格式异常，请重试")

        parsed = _validate_shape(1, "wizard_oneshot", parsed, SCHEMA_ONESHOT)
        self._sanitize_oneshot(parsed, modules, labels_list)
        if vision_warning:
            parsed["follow_up_questions"] = [vision_warning] + list(parsed.get("follow_up_questions") or [])
            parsed["follow_up_questions"] = parsed["follow_up_questions"][:3]
        return parsed

    @staticmethod
    def _sanitize_oneshot(data: dict, modules: list, labels_list: list) -> None:
        """In-place validation per spec §5.4."""
        title = (data.get("title") or "").strip()[:200]
        if not title:
            raise AiWizardError(step=1, code="llm_bad_shape", message="title 为空")
        data["title"] = title

        if data.get("priority") not in ALLOWED_PRIORITIES:
            data["priority"] = "P2"

        mod = (data.get("module") or "").strip()
        if modules and mod not in modules:
            mod = "其他" if "其他" in modules else modules[0]
        data["module"] = mod

        data["repro_steps"] = (data.get("repro_steps") or "")[:2000]
        data["expected_behavior"] = (data.get("expected_behavior") or "")[:500]
        data["inferred_env"] = (data.get("inferred_env") or "")[:200]

        raw_labels = data.get("labels") or []
        if not isinstance(raw_labels, list):
            raw_labels = []
        valid = set(labels_list)
        data["labels"] = [l for l in raw_labels if isinstance(l, str) and l in valid][:3]

        raw_q = data.get("follow_up_questions") or []
        if not isinstance(raw_q, list):
            raw_q = []
        data["follow_up_questions"] = [str(q)[:100] for q in raw_q if q][:3]

    def _load_image_attachments(self, attachment_ids: list, owner) -> list[tuple[str, bytes]]:
        """Resolve attachment_ids → up to MAX_IMAGES (mime, bytes) pairs.

        - Filters to image MIME types only
        - 仅允许调用者本人上传的附件 (uploaded_by=owner),防止跨用户 IDOR
          泄露图片内容 (LLM 会 OCR 图片返回到 SSE 响应中)
        - Skips files larger than MAX_IMAGE_BYTES
        - Silently skips read failures (logs warning) so one bad attachment
          doesn't abort the whole wizard call
        """
        if not attachment_ids or owner is None:
            return []

        from apps.tools.models import Attachment

        rows = list(
            Attachment.objects
            .filter(id__in=attachment_ids, mime_type__startswith="image/", uploaded_by=owner)
            .order_by("created_at")
        )

        out: list[tuple[str, bytes]] = []
        for att in rows:
            if att.file_size > MAX_IMAGE_BYTES:
                logger.info("wizard skipping oversize image %s (%d bytes)", att.file_name, att.file_size)
                continue
            try:
                raw = _read_attachment_bytes(att.file_key)
            except Exception as e:
                logger.warning("wizard could not read attachment %s: %s", att.file_key, e)
                continue
            out.append((att.mime_type, raw))
            if len(out) >= MAX_IMAGES:
                break
        return out

    def stream_draft(self, description: str, project_id=None, attachment_ids=None, user=None):
        """Dispatch on AI_WIZARD_LEGACY: True → v1 3-stage, False → v2 oneshot.

        `user` is the authenticated requester. Required for v2 to scope
        attachment resolution to attachments the user actually owns.
        """
        from django.conf import settings
        if getattr(settings, "AI_WIZARD_LEGACY", False):
            # Legacy path keeps its original signature (description only) —
            # v1 does not accept attachments so no per-user filter is needed.
            yield from self._stream_draft_legacy(description)
        else:
            yield from self._stream_draft_v2(
                description=description,
                project_id=project_id,
                attachment_ids=attachment_ids or [],
                user=user,
            )

    def stream_revise(self, current_draft: dict, instruction: str, attachment_ids=None, user=None):
        """SSE 流式 wrap oneshot_revise - 同步处理两种 action:
          - update: emit ('draft', {...})  与 stream_draft 一致, 前端追加新 draft turn
          - submit: emit ('submit', {})    前端跳过 draft 渲染, 直接触发"提交" 动作

        Events: step(running) → step(done) → draft | submit → done.
                On failure: step(error) + error.
        """
        import time
        t0 = time.monotonic()

        STEP_LABEL = "AI 正在更新草稿"
        yield ("step", {"step": 1, "label": STEP_LABEL, "status": "running"})

        images = self._load_image_attachments(attachment_ids or [], user)

        try:
            result = self.oneshot_revise(current_draft, instruction, images)
        except AiWizardError as e:
            logger.warning(
                "wizard revise AiWizardError code=%s elapsed_ms=%d",
                e.code, int((time.monotonic() - t0) * 1000),
            )
            yield ("step", {"step": 1, "label": STEP_LABEL, "status": "error"})
            yield ("error", {"code": e.code, "message": e.message})
            yield ("done", {})
            return
        except BaseException:
            logger.exception(
                "wizard revise unexpected failure elapsed_ms=%d",
                int((time.monotonic() - t0) * 1000),
            )
            yield ("step", {"step": 1, "label": STEP_LABEL, "status": "error"})
            yield ("error", {"code": "llm_call_failed", "message": "AI 调用失败,请重试"})
            yield ("done", {})
            return

        # action=submit 短路: AI 判定用户在确认, 直接发 submit 信号
        if result.get("action") == "submit":
            logger.info("wizard revise → submit elapsed_ms=%d", int((time.monotonic() - t0) * 1000))
            yield ("step", {"step": 1, "label": "✓ 已确认提交", "status": "done"})
            yield ("submit", {})
            yield ("done", {})
            return

        # action=update: 走 draft 路径 (这一段是纯 dict 操作, 不会抛 AiWizardError)
        image_meta = self._load_image_metadata(attachment_ids or [], user)
        draft = dict(result)
        draft.pop("action", None)
        draft["description"] = self._assemble_revise_description(
            current_draft.get("description", ""), draft.get("inferred_env", ""), image_meta,
        )

        logger.info("wizard revise ok elapsed_ms=%d", int((time.monotonic() - t0) * 1000))
        yield ("step", {"step": 1, "label": STEP_LABEL, "status": "done"})
        yield ("draft", draft)
        yield ("done", {})

    @staticmethod
    def _assemble_revise_description(prev_description: str, inferred_env: str, image_meta: list | None = None) -> str:
        """修订路径: 保留上一份 description 的主体, 仅追加用户本轮上传的新图片链接。

        若 prev_description 已经含同 URL 的图片标记, 不再重复追加 (用 URL 子串判断,
        简单粗暴但够用; 真正去重还得解析 markdown, 不值)。
        """
        base = (prev_description or "").rstrip()
        parts: list[str] = [base] if base else []
        for att in image_meta or []:
            name = att.get("file_name") or "image"
            url = att.get("file_url") or ""
            if url and url not in base:
                parts.append(f"![{name}]({url})")
        return "\n\n".join(parts)

    def _stream_draft_v2(self, description: str, project_id, attachment_ids: list | None = None, user=None):
        """v2 generator yielding (event_name, payload) for the SSE layer.

        Single LLM call (oneshot multimodal draft). Issue-content-unrelated
        side-effects — auto-assign, future enrichment — are deferred to Celery
        tasks fired from POST /api/issues/, on the principle that the submitter
        only cares whether the AI draft matches their intent, not who handles
        the issue afterwards.

        Events: step(running) → step(done) + draft → done.
                On failure: step(error) + error.
        """
        import time
        t0 = time.monotonic()

        STEP_LABEL = "理解描述与截图"
        yield ("step", {"step": 1, "label": STEP_LABEL, "status": "running"})

        images = self._load_image_attachments(attachment_ids or [], user)

        try:
            draft = self.oneshot_draft(description, images)
            image_meta = self._load_image_metadata(attachment_ids or [], user)
            draft["description"] = self._assemble_description(
                description, draft.get("inferred_env", ""), image_meta,
            )
        except AiWizardError as e:
            logger.warning(
                "wizard oneshot AiWizardError code=%s elapsed_ms=%d",
                e.code, int((time.monotonic() - t0) * 1000),
            )
            yield ("step", {"step": 1, "label": STEP_LABEL, "status": "error"})
            yield ("error", {"code": e.code, "message": e.message})
            yield ("done", {})
            return
        except BaseException:
            logger.exception(
                "wizard oneshot unexpected failure elapsed_ms=%d",
                int((time.monotonic() - t0) * 1000),
            )
            yield ("step", {"step": 1, "label": STEP_LABEL, "status": "error"})
            yield ("error", {"code": "llm_call_failed", "message": "AI 调用失败，请重试"})
            yield ("done", {})
            return

        logger.info("wizard oneshot ok elapsed_ms=%d", int((time.monotonic() - t0) * 1000))
        yield ("step", {"step": 1, "label": STEP_LABEL, "status": "done"})
        yield ("draft", draft)
        yield ("done", {})

    @staticmethod
    def _assemble_description(user_description: str, inferred_env: str, image_meta: list | None = None) -> str:
        """Server-side description assembly per spec §4.3.

        Order: raw user description → inferred_env blockquote → image markdown.
        Each block separated by a blank line. Image attachments are embedded as
        ![name](file_url) so the issue body previews inline (fixes Bug 1).
        """
        raw = (user_description or "").rstrip()
        env = (inferred_env or "").strip()
        parts: list[str] = []
        if raw:
            parts.append(raw)
        if env:
            parts.append(f"> 🤖 *AI 推断环境*: {env}")
        for att in image_meta or []:
            name = att.get("file_name") or "image"
            url = att.get("file_url") or ""
            if url:
                parts.append(f"![{name}]({url})")
        return "\n\n".join(parts)

    def _load_image_metadata(self, attachment_ids: list, owner) -> list[dict]:
        """Return image attachment metadata (file_name, file_url) for inline markdown.

        Separate from _load_image_attachments which reads raw bytes for the
        vision LLM call — this one only needs the URL for the markdown.

        Also scoped to owner=uploaded_by, mirroring _load_image_attachments;
        otherwise an attacker could inline another user's image URL into the
        new Issue's description.
        """
        if not attachment_ids or owner is None:
            return []
        from apps.tools.models import Attachment
        return list(
            Attachment.objects
            .filter(id__in=attachment_ids, mime_type__startswith="image/", uploaded_by=owner)
            .order_by("created_at")
            .values("file_name", "file_url")
        )

    def _stream_draft_legacy(self, description: str):
        """Generator yielding (event_name, data_dict) tuples for the SSE layer.

        Yields ('_heartbeat', None) between stages so the view layer can detect
        client disconnect via BrokenPipeError before incurring the next LLM call.

        Events:
          ("step", {...}) ("draft", {...}) ("done", {})
          ("error", {...}) on failure
          ("_heartbeat", None) — internal signaling, view converts to SSE comment
        """
        from apps.settings.models import SiteSettings

        site = SiteSettings.get_solo()
        modules = list(site.modules or [])
        labels_dict = site.labels or {}
        labels_list = list(labels_dict.keys()) if isinstance(labels_dict, dict) else list(labels_dict)

        try:
            classify = self.classify(description)
            yield ("step", {
                "step": 1,
                "label": "识别问题类型与影响范围",
                "status": "done",
                "result": classify,
            })
            yield ("_heartbeat", None)

            extract = self.extract(description, classify, modules)
            yield ("step", {
                "step": 2,
                "label": "提取关键字段",
                "status": "done",
                "result": extract,
            })
            yield ("_heartbeat", None)

            generate = self.generate(description, classify, extract, labels_list)
            yield ("step", {
                "step": 3,
                "label": "生成复现步骤与预期行为",
                "status": "done",
                "result": generate,
            })

            yield ("draft", self._merge(description, classify, extract, generate))
            yield ("done", {})

        except AiWizardError as e:
            yield ("error", {"step": e.step, "code": e.code, "message": e.message})

    def _merge(self, description: str, classify: dict, extract: dict, generate: dict) -> dict:
        return {
            "title": extract.get("title", ""),
            "description": description,  # client decides whether to use AI-rephrased or raw input
            "repro_steps": generate.get("repro_steps", ""),
            "expected_behavior": generate.get("expected_behavior", ""),
            "priority": extract.get("priority", "P2"),
            "module": extract.get("module", ""),
            "labels": generate.get("labels", []),
            "follow_up_questions": generate.get("follow_up_questions", []),
            "environment": None,
        }
