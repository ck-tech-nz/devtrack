# Label System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the label system from flat string arrays to rich objects with colors and descriptions, add a GitHub-style label picker popover and a management modal on the issue detail page.

**Architecture:** Backend SiteSettings.labels changes from `["前端", ...]` to `{"前端": {"foreground": "#fff", "background": "#0075ca", "description": "..."}}`. A new PATCH endpoint allows updating labels. Frontend replaces inline toggle buttons with a popover picker + modal for CRUD. Issue.labels (per-issue) stays as `string[]`.

**Tech Stack:** Django REST Framework, PostgreSQL JSONField, Nuxt 4 (Vue 3), Nuxt UI (UPopover, UModal, UInput, UButton, UCheckbox)

---

### Task 1: Update Backend Default Labels and Model

**Files:**
- Modify: `backend/apps/settings/models.py:5-6` (default_labels function)

- [ ] **Step 1: Update `default_labels()` to return dict format**

```python
def default_labels():
    return {
        "前端": {"foreground": "#ffffff", "background": "#0075ca", "description": "前端相关问题"},
        "后端": {"foreground": "#ffffff", "background": "#e99695", "description": "后端相关问题"},
        "Bug": {"foreground": "#ffffff", "background": "#d73a4a", "description": "程序错误"},
        "优化": {"foreground": "#ffffff", "background": "#a2eeef", "description": "性能或代码优化"},
        "需求": {"foreground": "#ffffff", "background": "#7057ff", "description": "新功能需求"},
        "文档": {"foreground": "#ffffff", "background": "#0075ca", "description": "文档改进"},
        "CI/CD": {"foreground": "#ffffff", "background": "#e4e669", "description": "持续集成与部署"},
        "安全": {"foreground": "#ffffff", "background": "#d73a4a", "description": "安全相关问题"},
        "性能": {"foreground": "#ffffff", "background": "#f9d0c4", "description": "性能问题"},
        "UI/UX": {"foreground": "#ffffff", "background": "#bfd4f2", "description": "界面与体验"},
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/apps/settings/models.py
git commit -m "feat(settings): update default_labels to dict format with colors and descriptions"
```

---

### Task 2: Data Migration

**Files:**
- Create: `backend/apps/settings/migrations/0002_convert_labels_to_dict.py`

- [ ] **Step 1: Create the data migration**

```python
from django.db import migrations

# Preset palette for migrating existing string labels
PALETTE = [
    "#0075ca", "#e99695", "#d73a4a", "#a2eeef", "#7057ff",
    "#0e8a16", "#e4e669", "#f9d0c4", "#bfd4f2", "#c5def5",
]


def forwards(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    for settings in SiteSettings.objects.all():
        labels = settings.labels
        if isinstance(labels, list):
            new_labels = {}
            for i, name in enumerate(labels):
                new_labels[name] = {
                    "foreground": "#ffffff",
                    "background": PALETTE[i % len(PALETTE)],
                    "description": "",
                }
            settings.labels = new_labels
            settings.save(update_fields=["labels"])


def backwards(apps, schema_editor):
    SiteSettings = apps.get_model("settings", "SiteSettings")
    for settings in SiteSettings.objects.all():
        labels = settings.labels
        if isinstance(labels, dict):
            settings.labels = list(labels.keys())
            settings.save(update_fields=["labels"])


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
```

- [ ] **Step 2: Run the migration**

Run: `cd backend && uv run python manage.py migrate settings`
Expected: `Applying settings.0002_convert_labels_to_dict... OK`

- [ ] **Step 3: Verify in shell**

Run: `cd backend && uv run python manage.py shell -c "from apps.settings.models import SiteSettings; s = SiteSettings.get_solo(); print(type(s.labels), list(s.labels.keys())[:3])"`
Expected: `<class 'dict'> ['前端', '后端', 'Bug']`

- [ ] **Step 4: Commit**

```bash
git add backend/apps/settings/migrations/0002_convert_labels_to_dict.py
git commit -m "feat(settings): data migration to convert labels array to dict format"
```

---

### Task 3: Update Backend Serializers and Add Labels PATCH Endpoint

**Files:**
- Modify: `backend/apps/settings/serializers.py` (add LabelSettingsSerializer)
- Modify: `backend/apps/settings/views.py` (add LabelSettingsView)
- Modify: `backend/apps/settings/urls.py` (register labels/ route)
- Modify: `backend/apps/issues/serializers.py:105-111` (fix validate_labels)

- [ ] **Step 1: Write failing test for the labels PATCH endpoint**

Create/append to `backend/tests/test_settings.py`:

```python
class TestLabelSettingsAPI:
    def test_patch_labels(self, auth_client, site_settings):
        new_labels = {
            "前端": {"foreground": "#ffffff", "background": "#0075ca", "description": "前端相关"},
            "NewLabel": {"foreground": "#000000", "background": "#ff0000", "description": "新标签"},
        }
        response = auth_client.patch(
            "/api/settings/labels/",
            data={"labels": new_labels},
            format="json",
        )
        assert response.status_code == 200
        assert "NewLabel" in response.data["labels"]
        assert response.data["labels"]["NewLabel"]["background"] == "#ff0000"

    def test_patch_labels_unauthenticated(self, api_client, site_settings):
        response = api_client.patch(
            "/api/settings/labels/",
            data={"labels": {}},
            format="json",
        )
        assert response.status_code == 401

    def test_patch_labels_invalid_format(self, auth_client, site_settings):
        response = auth_client.patch(
            "/api/settings/labels/",
            data={"labels": {"Bad": {"foreground": "#fff"}}},
            format="json",
        )
        assert response.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_settings.py::TestLabelSettingsAPI -v`
Expected: FAIL (404 — endpoint doesn't exist yet)

- [ ] **Step 3: Add LabelSettingsSerializer**

Replace `backend/apps/settings/serializers.py` with:

```python
import re
from rest_framework import serializers
from .models import SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["labels", "priorities", "issue_statuses"]


class LabelSettingsSerializer(serializers.Serializer):
    labels = serializers.DictField(child=serializers.DictField())

    def validate_labels(self, value):
        hex_re = re.compile(r'^#[0-9a-fA-F]{3,8}$')
        for name, props in value.items():
            if not isinstance(props, dict):
                raise serializers.ValidationError(f"标签 '{name}' 格式错误")
            missing = {"foreground", "background", "description"} - set(props.keys())
            if missing:
                raise serializers.ValidationError(f"标签 '{name}' 缺少字段: {missing}")
            for color_field in ("foreground", "background"):
                if not hex_re.match(props[color_field]):
                    raise serializers.ValidationError(
                        f"标签 '{name}' 的 {color_field} 不是有效的十六进制颜色"
                    )
        return value
```

- [ ] **Step 4: Add LabelSettingsView**

Replace `backend/apps/settings/views.py` with:

```python
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SiteSettings
from .serializers import SiteSettingsSerializer, LabelSettingsSerializer


class SiteSettingsView(RetrieveAPIView):
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return SiteSettings.get_solo()


class LabelSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = LabelSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settings = SiteSettings.get_solo()
        settings.labels = serializer.validated_data["labels"]
        settings.save(update_fields=["labels"])
        return Response({"labels": settings.labels})
```

- [ ] **Step 5: Register the URL**

Replace `backend/apps/settings/urls.py` with:

```python
from django.urls import path
from .views import SiteSettingsView, LabelSettingsView

urlpatterns = [
    path("", SiteSettingsView.as_view(), name="site-settings"),
    path("labels/", LabelSettingsView.as_view(), name="label-settings"),
]
```

- [ ] **Step 6: Fix `validate_labels` in issue serializer**

In `backend/apps/issues/serializers.py`, change `validate_labels` (lines 105-111) from:

```python
    def validate_labels(self, value):
        site_settings = SiteSettings.get_solo()
        valid = set(site_settings.labels)
        invalid = [l for l in value if l not in valid]
        if invalid:
            raise serializers.ValidationError(f"无效的标签: {invalid}")
        return value
```

to:

```python
    def validate_labels(self, value):
        site_settings = SiteSettings.get_solo()
        valid = set(site_settings.labels.keys()) if isinstance(site_settings.labels, dict) else set(site_settings.labels)
        invalid = [l for l in value if l not in valid]
        if invalid:
            raise serializers.ValidationError(f"无效的标签: {invalid}")
        return value
```

- [ ] **Step 7: Run all tests**

Run: `cd backend && uv run pytest tests/test_settings.py tests/test_issues.py -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add backend/apps/settings/serializers.py backend/apps/settings/views.py backend/apps/settings/urls.py backend/apps/issues/serializers.py backend/tests/test_settings.py
git commit -m "feat(settings): add PATCH /api/settings/labels/ endpoint and fix label validation for dict format"
```

---

### Task 4: Update Test Factories and Existing Tests

**Files:**
- Modify: `backend/tests/factories.py:32` (SiteSettingsFactory labels)
- Modify: `backend/tests/test_settings.py:14-16` (fix test_default_labels assertions)

- [ ] **Step 1: Update SiteSettingsFactory**

In `backend/tests/factories.py`, change line 32 from:

```python
    labels = ["前端", "后端", "Bug", "优化", "需求", "文档", "CI/CD", "安全", "性能", "UI/UX"]
```

to:

```python
    labels = {
        "前端": {"foreground": "#ffffff", "background": "#0075ca", "description": "前端相关问题"},
        "后端": {"foreground": "#ffffff", "background": "#e99695", "description": "后端相关问题"},
        "Bug": {"foreground": "#ffffff", "background": "#d73a4a", "description": "程序错误"},
        "优化": {"foreground": "#ffffff", "background": "#a2eeef", "description": ""},
        "需求": {"foreground": "#ffffff", "background": "#7057ff", "description": ""},
        "文档": {"foreground": "#ffffff", "background": "#0075ca", "description": ""},
        "CI/CD": {"foreground": "#ffffff", "background": "#e4e669", "description": ""},
        "安全": {"foreground": "#ffffff", "background": "#d73a4a", "description": ""},
        "性能": {"foreground": "#ffffff", "background": "#f9d0c4", "description": ""},
        "UI/UX": {"foreground": "#ffffff", "background": "#bfd4f2", "description": ""},
    }
```

- [ ] **Step 2: Update test_default_labels in test_settings.py**

Change the `test_default_labels` method from:

```python
    def test_default_labels(self, site_settings):
        assert "前端" in site_settings.labels
        assert "Bug" in site_settings.labels
        assert len(site_settings.labels) == 10
```

to:

```python
    def test_default_labels(self, site_settings):
        assert "前端" in site_settings.labels
        assert "Bug" in site_settings.labels
        assert len(site_settings.labels) == 10
        assert site_settings.labels["前端"]["background"] == "#0075ca"
```

- [ ] **Step 3: Update test_get_settings_authenticated**

The existing test `test_get_settings_authenticated` asserts `response.data["labels"] == site_settings.labels`. This still works because the factory now returns a dict and the API returns a dict. No change needed.

- [ ] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest -v`
Expected: All pass (including issue tests that use IssueFactory with `labels` containing string values like `["前端", "后端", "Bug"]` — these are validated against the dict keys)

- [ ] **Step 5: Commit**

```bash
git add backend/tests/factories.py backend/tests/test_settings.py
git commit -m "test(settings): update factories and tests for dict-format labels"
```

---

### Task 5: Frontend — Label Picker Popover on Issue Detail Page

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

This task replaces the inline toggle buttons (lines 174-185) with a label picker popover, updates the data type of `labelItems`, and adds colored pill display for applied labels.

- [ ] **Step 1: Update `labelItems` type and data loading**

In `frontend/app/pages/app/issues/[id].vue`, change line 440 from:

```typescript
const labelItems = ref<string[]>([])
```

to:

```typescript
const labelItems = ref<Record<string, { foreground: string; background: string; description: string }>>({})
```

Change line 728 from:

```typescript
labelItems.value = settingsData?.labels || []
```

to:

```typescript
labelItems.value = settingsData?.labels || {}
```

- [ ] **Step 2: Add label picker state variables**

After the `labelItems` declaration, add:

```typescript
const showLabelPicker = ref(false)
const labelSearchQuery = ref('')
const showLabelManager = ref(false)

const filteredLabelNames = computed(() => {
  const names = Object.keys(labelItems.value)
  if (!labelSearchQuery.value) return names
  const q = labelSearchQuery.value.toLowerCase()
  return names.filter(n => n.toLowerCase().includes(q) || labelItems.value[n].description.toLowerCase().includes(q))
})
```

- [ ] **Step 3: Replace the label section template**

Replace lines 174-185 (the `<div v-if="labelItems.length">` block) with:

```vue
          <div class="space-y-1.5">
            <UPopover v-model:open="showLabelPicker" :popper="{ placement: 'bottom-start' }">
              <button class="flex items-center justify-between w-full group cursor-pointer">
                <label class="text-xs font-medium text-gray-400 dark:text-gray-500 cursor-pointer">标签</label>
                <UIcon name="i-heroicons-cog-6-tooth" class="w-4 h-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300" />
              </button>
              <template #panel>
                <div class="w-72 p-0">
                  <div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
                    <p class="text-xs font-semibold text-gray-900 dark:text-gray-100">应用标签</p>
                  </div>
                  <div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
                    <UInput v-model="labelSearchQuery" placeholder="筛选标签" size="xs" icon="i-heroicons-magnifying-glass" />
                  </div>
                  <div class="max-h-64 overflow-y-auto">
                    <button
                      v-for="name in filteredLabelNames"
                      :key="name"
                      class="flex items-start gap-2 w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      @click="toggleLabel(name)"
                    >
                      <UIcon
                        :name="form.labels.includes(name) ? 'i-heroicons-check' : ''"
                        class="w-4 h-4 mt-0.5 shrink-0"
                        :class="form.labels.includes(name) ? 'text-gray-900 dark:text-gray-100' : 'text-transparent'"
                      />
                      <span
                        class="w-3 h-3 rounded-full mt-1 shrink-0"
                        :style="{ backgroundColor: labelItems[name]?.background || '#ccc' }"
                      />
                      <div class="min-w-0">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ name }}</div>
                        <div v-if="labelItems[name]?.description" class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ labelItems[name].description }}</div>
                      </div>
                    </button>
                    <div v-if="!filteredLabelNames.length" class="px-3 py-4 text-center text-xs text-gray-400">无匹配标签</div>
                  </div>
                  <button
                    class="w-full px-3 py-2 text-xs text-center text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
                    @click="showLabelPicker = false; showLabelManager = true"
                  >编辑标签</button>
                </div>
              </template>
            </UPopover>
            <!-- Applied labels as colored pills -->
            <div class="flex items-center gap-1.5 flex-wrap">
              <span
                v-for="lbl in form.labels"
                :key="lbl"
                class="px-2 py-0.5 rounded-full text-xs font-medium"
                :style="{
                  backgroundColor: labelItems[lbl]?.background || '#e5e7eb',
                  color: labelItems[lbl]?.foreground || '#374151',
                }"
              >{{ lbl }}</span>
              <span v-if="!form.labels.length" class="text-xs text-gray-400 dark:text-gray-500">无标签</span>
            </div>
          </div>
```

- [ ] **Step 4: Verify the picker renders and toggles labels**

Run: `cd frontend && npm run dev`
Navigate to an issue detail page, click the "标签" row, verify the popover opens with search, checkboxes, color dots, and descriptions. Toggling a label should auto-save.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "feat(frontend): replace label toggle buttons with GitHub-style picker popover"
```

---

### Task 6: Frontend — Label Management Modal

**Files:**
- Modify: `frontend/app/pages/app/issues/[id].vue`

- [ ] **Step 1: Add management modal state**

After the `showLabelManager` declaration (added in Task 5), add:

```typescript
const editingLabel = ref<string | null>(null)
const editForm = ref({ name: '', foreground: '#ffffff', background: '#0075ca', description: '' })
const addingLabel = ref(false)
const labelSaving = ref(false)

function startEditLabel(name: string) {
  editingLabel.value = name
  addingLabel.value = false
  const lbl = labelItems.value[name]
  editForm.value = { name, foreground: lbl.foreground, background: lbl.background, description: lbl.description }
}

function startAddLabel() {
  addingLabel.value = true
  editingLabel.value = null
  editForm.value = { name: '', foreground: '#ffffff', background: '#0075ca', description: '' }
}

function cancelEditLabel() {
  editingLabel.value = null
  addingLabel.value = false
}

async function saveLabelEdit() {
  labelSaving.value = true
  try {
    const updated = { ...labelItems.value }
    // If editing and name changed, remove old key
    if (editingLabel.value && editingLabel.value !== editForm.value.name) {
      delete updated[editingLabel.value]
    }
    updated[editForm.value.name] = {
      foreground: editForm.value.foreground,
      background: editForm.value.background,
      description: editForm.value.description,
    }
    const res = await api<any>('/api/settings/labels/', { method: 'PATCH', body: { labels: updated } })
    labelItems.value = res.labels
    editingLabel.value = null
    addingLabel.value = false
  } catch (e) {
    console.error('Save label failed:', e)
  } finally {
    labelSaving.value = false
  }
}

async function deleteLabel(name: string) {
  labelSaving.value = true
  try {
    const updated = { ...labelItems.value }
    delete updated[name]
    const res = await api<any>('/api/settings/labels/', { method: 'PATCH', body: { labels: updated } })
    labelItems.value = res.labels
  } catch (e) {
    console.error('Delete label failed:', e)
  } finally {
    labelSaving.value = false
  }
}
```

- [ ] **Step 2: Add the management modal template**

Add this after the label picker `</div>` (the `space-y-1.5` div), before the next `<div>` section (the "信息" card):

```vue
          <!-- Label Management Modal -->
          <UModal v-model:open="showLabelManager">
            <template #content>
              <div class="p-5 space-y-4">
                <div class="flex items-center justify-between">
                  <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">管理标签</h3>
                  <div class="flex items-center gap-2">
                    <UButton size="xs" icon="i-heroicons-plus" @click="startAddLabel">新增</UButton>
                    <UButton size="xs" variant="ghost" icon="i-heroicons-x-mark" @click="showLabelManager = false" />
                  </div>
                </div>

                <!-- Add new label form -->
                <div v-if="addingLabel" class="rounded-lg border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 p-3 space-y-2">
                  <UInput v-model="editForm.name" placeholder="标签名称" size="sm" />
                  <UInput v-model="editForm.description" placeholder="描述" size="sm" />
                  <div class="flex items-center gap-3">
                    <div class="flex items-center gap-1.5">
                      <label class="text-xs text-gray-500">背景</label>
                      <input type="color" v-model="editForm.background" class="w-6 h-6 rounded cursor-pointer border-0 p-0" />
                      <UInput v-model="editForm.background" size="xs" class="w-24" />
                    </div>
                    <div class="flex items-center gap-1.5">
                      <label class="text-xs text-gray-500">文字</label>
                      <input type="color" v-model="editForm.foreground" class="w-6 h-6 rounded cursor-pointer border-0 p-0" />
                      <UInput v-model="editForm.foreground" size="xs" class="w-24" />
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded-full text-xs font-medium" :style="{ backgroundColor: editForm.background, color: editForm.foreground }">{{ editForm.name || '预览' }}</span>
                  </div>
                  <div class="flex items-center gap-2 justify-end">
                    <UButton size="xs" variant="ghost" @click="cancelEditLabel">取消</UButton>
                    <UButton size="xs" :loading="labelSaving" :disabled="!editForm.name.trim()" @click="saveLabelEdit">保存</UButton>
                  </div>
                </div>

                <!-- Label list -->
                <div class="space-y-1 max-h-96 overflow-y-auto">
                  <div v-for="(props, name) in labelItems" :key="name">
                    <!-- Display mode -->
                    <div v-if="editingLabel !== name" class="flex items-center justify-between py-2 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 group">
                      <div class="flex items-center gap-2 min-w-0">
                        <span class="px-2 py-0.5 rounded-full text-xs font-medium shrink-0" :style="{ backgroundColor: props.background, color: props.foreground }">{{ name }}</span>
                        <span class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ props.description }}</span>
                      </div>
                      <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                        <UButton size="xs" variant="ghost" icon="i-heroicons-pencil-square" @click="startEditLabel(name as string)" />
                        <UButton size="xs" variant="ghost" color="error" icon="i-heroicons-trash" @click="deleteLabel(name as string)" />
                      </div>
                    </div>
                    <!-- Edit mode -->
                    <div v-else class="rounded-lg border border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 p-3 space-y-2">
                      <UInput v-model="editForm.name" placeholder="标签名称" size="sm" />
                      <UInput v-model="editForm.description" placeholder="描述" size="sm" />
                      <div class="flex items-center gap-3">
                        <div class="flex items-center gap-1.5">
                          <label class="text-xs text-gray-500">背景</label>
                          <input type="color" v-model="editForm.background" class="w-6 h-6 rounded cursor-pointer border-0 p-0" />
                          <UInput v-model="editForm.background" size="xs" class="w-24" />
                        </div>
                        <div class="flex items-center gap-1.5">
                          <label class="text-xs text-gray-500">文字</label>
                          <input type="color" v-model="editForm.foreground" class="w-6 h-6 rounded cursor-pointer border-0 p-0" />
                          <UInput v-model="editForm.foreground" size="xs" class="w-24" />
                        </div>
                      </div>
                      <div class="flex items-center gap-2">
                        <span class="px-2 py-0.5 rounded-full text-xs font-medium" :style="{ backgroundColor: editForm.background, color: editForm.foreground }">{{ editForm.name || '预览' }}</span>
                      </div>
                      <div class="flex items-center gap-2 justify-end">
                        <UButton size="xs" variant="ghost" @click="cancelEditLabel">取消</UButton>
                        <UButton size="xs" :loading="labelSaving" :disabled="!editForm.name.trim()" @click="saveLabelEdit">保存</UButton>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </UModal>
```

- [ ] **Step 3: Test the management modal**

Run: `cd frontend && npm run dev`
Navigate to issue detail → click label gear icon → click "编辑标签" → verify:
- Modal opens with list of all labels as colored pills
- Click pencil to edit a label (name, color, description)
- Click "新增" to add a new label
- Click trash to delete
- Color pickers work, preview updates live
- Save calls PATCH and refreshes the picker

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/app/issues/[id].vue
git commit -m "feat(frontend): add label management modal with CRUD and color pickers"
```

---

### Task 7: Update Issues List Page

**Files:**
- Modify: `frontend/app/pages/app/issues/index.vue`

- [ ] **Step 1: Update `labelOptions` derivation**

In `frontend/app/pages/app/issues/index.vue`, change line 294 from:

```typescript
const labelOptions = ref<string[]>([])
```

to:

```typescript
const labelOptions = ref<string[]>([])
```

(Type stays `string[]` — it holds label names for the select menu.)

Change line 588 from:

```typescript
labelOptions.value = settingsData?.labels || []
```

to:

```typescript
const rawLabels = settingsData?.labels || {}
labelOptions.value = typeof rawLabels === 'object' && !Array.isArray(rawLabels) ? Object.keys(rawLabels) : rawLabels
```

- [ ] **Step 2: Verify the create-issue modal works**

Run: `cd frontend && npm run dev`
Navigate to issues list → open create issue modal → verify the label select menu shows label names and creating an issue with labels works.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/app/issues/index.vue
git commit -m "feat(frontend): update issues list page to derive label names from dict format"
```

---

### Task 8: Full Integration Test

**Files:** None (verification only)

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && uv run pytest -v`
Expected: All tests pass

- [ ] **Step 2: Run frontend type check**

Run: `cd frontend && npx nuxi typecheck`
Expected: No new errors

- [ ] **Step 3: End-to-end manual verification**

1. Open issue detail page → verify colored label pills display
2. Click label gear → popover opens → search works → toggle labels → auto-saves
3. Click "编辑标签" → modal opens → add new label with custom colors → save → new label appears in picker
4. Edit existing label's color → save → pill colors update
5. Delete a label → confirm it's gone from picker
6. Open issues list → create new issue with labels → verify it works
7. Check Django admin `/api/admin/settings/sitesettings/` → labels field shows dict format
