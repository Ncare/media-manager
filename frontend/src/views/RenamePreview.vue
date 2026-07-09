<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { librariesApi, renameApi } from '@/api'
import type { Library, RenamePreviewItem } from '@/types'
import NamingTemplateEditor from '@/components/NamingTemplateEditor.vue'

const libraries = ref<Library[]>([])
const selectedLibId = ref<number | undefined>(undefined)
const customTemplate = ref('')
const useCustomTemplate = ref(false)
const items = ref<RenamePreviewItem[]>([])
const selected = ref<number[]>([])
const loading = ref(false)
const executing = ref(false)
const lastBatch = ref<string | null>(null)

const selectedLib = computed(() => libraries.value.find((l) => l.id === selectedLibId.value))
const activeTemplate = computed(() =>
  useCustomTemplate.value && customTemplate.value ? customTemplate.value : undefined
)

onMounted(async () => {
  libraries.value = await librariesApi.list()
})

// when library changes, reset custom template toggle, load library default,
// and automatically fetch the resource list (no manual "preview" click needed)
watch(selectedLibId, (id) => {
  useCustomTemplate.value = false
  const lib = libraries.value.find((l) => l.id === id)
  customTemplate.value = lib ? (lib.type === 'tv' ? lib.naming_template : lib.naming_template) : ''
  if (id) preview()
})

// keep the table's "new path" column in sync when the custom template is edited.
// the editor already has its own per-row live preview; this re-runs the full table.
let tplTimer: number | undefined
watch(activeTemplate, () => {
  if (!selectedLibId.value) return
  if (tplTimer) clearTimeout(tplTimer)
  tplTimer = window.setTimeout(() => preview(), 450)
})

async function preview() {
  if (!selectedLibId.value) return
  loading.value = true
  selected.value = []
  try {
    const data = await renameApi.preview(selectedLibId.value, activeTemplate.value)
    items.value = data.items
    // do NOT auto-select — let the user choose which rows to rename
    selected.value = []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '预览失败')
  } finally {
    loading.value = false
  }
}

async function execute() {
  if (!selectedLibId.value || !selectedLib.value) return
  if (!selected.value.length) {
    ElMessage.warning('请至少选择一项')
    return
  }
  const mediaType = selectedLib.value.type
  await ElMessageBox.confirm(
    `将对 ${selected.value.length} 个文件执行重命名(可在执行后撤销)。继续?`,
    '确认重命名',
    { type: 'warning' }
  )
  executing.value = true
  try {
    const res = await renameApi.execute(selectedLibId.value, selected.value, mediaType, activeTemplate.value)
    lastBatch.value = res.batch_id
    ElMessage.success(`已重命名 ${res.moved} 个文件,批次: ${res.batch_id}`)
    preview()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '执行失败')
  } finally {
    executing.value = false
  }
}

async function undo() {
  await ElMessageBox.confirm('撤销最近一次重命名批次?', '撤销', { type: 'warning' })
  try {
    const res = await renameApi.undo(lastBatch.value || undefined)
    ElMessage.success(`已撤销 ${res.reverted} 项`)
    lastBatch.value = null
    preview()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '撤销失败')
  }
}

function shortPath(p: string) {
  const parts = p.split('/')
  return parts.slice(-2).join('/')
}
</script>

<template>
  <div class="page">
    <h2>重命名</h2>
    <div class="toolbar">
      <el-select v-model="selectedLibId" placeholder="选择媒体库" style="width:220px">
        <el-option v-for="l in libraries" :key="l.id" :label="`${l.name} (${l.type})`" :value="l.id" />
      </el-select>
      <el-checkbox v-model="useCustomTemplate" :disabled="!selectedLibId">自定义模板</el-checkbox>
      <el-button :disabled="!selectedLibId" :loading="loading" @click="preview" title="重新计算预览">刷新</el-button>
      <el-button type="success" :disabled="!selected.length" :loading="executing" @click="execute">
        执行选中 ({{ selected.length }})
      </el-button>
      <el-button :disabled="!lastBatch" @click="undo">撤销最近批次</el-button>
    </div>

    <!-- customizable template editor -->
    <div v-if="useCustomTemplate && selectedLibId" class="template-panel">
      <div class="panel-title">
        自定义命名模板
        <el-tooltip
          content="可在此临时调整模板而不修改媒体库设置;点标签插入 token;{a;b;c} 表示回退取第一个非空值"
          placement="top"
        >
          <span class="help">ⓘ</span>
        </el-tooltip>
      </div>
      <NamingTemplateEditor
        v-model="customTemplate"
        :library-id="selectedLibId"
        :media-type="selectedLib?.type || 'movie'"
        placeholder="如:{title} ({year})/{originalTitle;title} ({year}) [{resolution};{source}]{ext}"
      />
    </div>

    <el-table
      v-if="items.length"
      :data="items"
      style="width:100%;margin-top:16px"
      @selection-change="(rows: RenamePreviewItem[]) => (selected = rows.map((r) => r.media_id))"
    >
      <el-table-column type="selection" width="45" :selectable="(row: RenamePreviewItem) => !row.conflict" />
      <el-table-column label="原路径">
        <template #default="{ row }">
          <span :class="{ conflict: row.conflict }">{{ shortPath(row.from_path) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="" width="40" center>
        <template #default>→</template>
      </el-table-column>
      <el-table-column label="新路径">
        <template #default="{ row }">
          <span :class="{ conflict: row.conflict }">{{ shortPath(row.to_path) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.conflict" size="small" type="danger">冲突</el-tag>
          <el-tag v-else size="small" type="success">可重命名</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading" description="选择媒体库后将自动加载资源列表" />
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.template-panel {
  margin-top: 16px; padding: 16px;
  background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
}
.panel-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
.panel-title .help { color: var(--muted); cursor: help; }
.conflict { color: var(--danger); }
</style>
