<script setup lang="ts">
definePageMeta({ layout: 'default' })

interface BackupRecord {
  id: number
  filename: string
  file_size: number | null
  status: 'running' | 'success' | 'failed'
  error_message: string
  created_by_name: string | null
  created_at: string
}

const { api } = useApi()
const toast = useToast()

const loading = ref(false)
const creating = ref(false)
const backups = ref<BackupRecord[]>([])
const total = ref(0)
const page = ref(1)

const columns = [
  { accessorKey: 'filename', header: '文件名' },
  { accessorKey: 'file_size', header: '大小' },
  { accessorKey: 'status', header: '状态' },
  { accessorKey: 'created_by_name', header: '操作人' },
  { accessorKey: 'created_at', header: '时间' },
  { accessorKey: 'actions', header: '操作' },
]

function formatSize(bytes: number | null): string {
  if (bytes == null) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

const statusMap: Record<string, { label: string; color: 'success' | 'warning' | 'error' }> = {
  running: { label: '备份中', color: 'warning' },
  success: { label: '成功', color: 'success' },
  failed: { label: '失败', color: 'error' },
}

async function fetchBackups() {
  loading.value = true
  try {
    const res = await api<any>(`/api/settings/backups/?page=${page.value}`)
    backups.value = res.results
    total.value = res.count
  } finally {
    loading.value = false
  }
}

async function triggerBackup() {
  creating.value = true
  try {
    await api<BackupRecord>('/api/settings/backups/create/', { method: 'POST' })
    toast.add({ title: '备份完成', color: 'success' })
    await fetchBackups()
  } catch (e: any) {
    const msg = e?.data?.detail || '备份失败'
    toast.add({ title: msg, color: 'error' })
  } finally {
    creating.value = false
  }
}

async function downloadBackup(row: BackupRecord) {
  const token = localStorage.getItem('access_token')
  try {
    const response = await fetch(`/api/settings/backups/${row.id}/download/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new Error()
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ title: '下载失败', color: 'error' })
  }
}

async function deleteBackup(row: BackupRecord) {
  if (!confirm(`确定要删除备份 ${row.filename}？`)) return
  try {
    await api(`/api/settings/backups/${row.id}/`, { method: 'DELETE' })
    toast.add({ title: '已删除', color: 'success' })
    await fetchBackups()
  } catch {
    toast.add({ title: '删除失败', color: 'error' })
  }
}

watch(page, fetchBackups)
onMounted(fetchBackups)
</script>

<template>
  <div class="p-6 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold">数据库备份</h1>
      <UButton
        icon="i-heroicons-arrow-down-tray"
        :loading="creating"
        @click="triggerBackup"
      >
        立即备份
      </UButton>
    </div>

    <UTable
      :data="backups"
      :columns="columns"
      :loading="loading"
      :ui="{ th: 'text-xs', td: 'text-sm' }"
    >
      <template #file_size-cell="{ row }">
        {{ formatSize(row.original.file_size) }}
      </template>
      <template #status-cell="{ row }">
        <UBadge
          :color="statusMap[row.original.status]?.color"
          variant="subtle"
        >
          {{ statusMap[row.original.status]?.label }}
        </UBadge>
      </template>
      <template #created_by_name-cell="{ row }">
        {{ row.original.created_by_name || '-' }}
      </template>
      <template #created_at-cell="{ row }">
        {{ formatTime(row.original.created_at) }}
      </template>
      <template #actions-cell="{ row }">
        <div class="flex gap-2">
          <UButton
            v-if="row.original.status === 'success'"
            size="xs"
            variant="ghost"
            icon="i-heroicons-arrow-down-tray"
            @click="downloadBackup(row.original)"
          />
          <UButton
            size="xs"
            variant="ghost"
            color="error"
            icon="i-heroicons-trash"
            @click="deleteBackup(row.original)"
          />
        </div>
      </template>
    </UTable>

    <div v-if="total > 20" class="flex justify-center">
      <UPagination
        v-model="page"
        :total="total"
        :items-per-page="20"
        @update:model-value="fetchBackups"
      />
    </div>
  </div>
</template>
