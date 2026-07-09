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

// Re-run the table preview whenever the user toggles "custom template" on/off.
// (typing inside the editor is handled by onTemplateInput below.)
watch(useCustomTemplate, (on) => {
  if (on && selectedLibId.value) debouncedPreview()
})

// race guard: only the latest preview request may update the table, so a fast
// typist never sees a stale (slow, older) response overwrite a newer one.
let previewReqId = 0

async function preview(preserveSelection = false) {
  if (!selectedLibId.value) return
  const reqId = ++previewReqId
  loading.value = true
  if (!preserveSelection) selected.value = []
  try {
    const data = await renameApi.preview(selectedLibId.value, activeTemplate.value)
    if (reqId !== previewReqId) return   // a newer request superseded us; discard
    items.value = data.items
    if (!preserveSelection) selected.value = []
  } catch (e: any) {
    if (reqId === previewReqId) ElMessage.error(e?.response?.data?.detail || '预览失败')
  } finally {
    if (reqId === previewReqId) loading.value = false
  }
}

// the editor emits @change on every keystroke; debounce the table re-preview so
// the "new path" column tracks the template live without hammering the API.
let tplTimer: number | undefined
function onTemplateInput() {
  if (!selectedLibId.value) return
  if (tplTimer) clearTimeout(tplTimer)
  tplTimer = window.setTimeout(() => preview(true), 450)
}
function debouncedPreview() {
  if (tplTimer) clearTimeout(tplTimer)
  tplTimer = window.setTimeout(() => preview(true), 200)
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

// ---- TV tree view ----
// Group flat episode items into a show -> season -> episode tree so the preview
// table can render hierarchically (el-table tree mode).
interface TvNode {
  id: string                       // unique key for row-key
  _group: boolean                  // true = show/season folder row (not selectable)
  label: string                    // display name for group rows
  children?: TvNode[]              // only on group rows
  // group-only: the renamed folder name (shown in the "new path" column)
  newFolder?: string
  // leaf-only fields mirror RenamePreviewItem
  media_id?: number
  from_path?: string
  to_path?: string
  conflict?: boolean
}

const isTv = computed(() => selectedLib.value?.type === 'tv')

const tvTree = computed<TvNode[]>(() => {
  if (!isTv.value) return []
  // group by show, then by season
  const shows = new Map<number, { title: string; seasons: Map<number, RenamePreviewItem[]> }>()
  for (const it of items.value) {
    if (it.show_id == null) continue
    let s = shows.get(it.show_id)
    if (!s) {
      s = { title: it.show_title || `剧集 ${it.show_id}`, seasons: new Map() }
      shows.set(it.show_id, s)
    }
    const sn = it.season_number ?? 0
    let arr = s.seasons.get(sn)
    if (!arr) {
      arr = []
      s.seasons.set(sn, arr)
    }
    arr.push(it)
  }
  const tree: TvNode[] = []
  for (const [showId, s] of shows) {
    const seasonNodes: TvNode[] = []
    for (const [sn, eps] of [...s.seasons.entries()].sort((a, b) => a[0] - b[0])) {
      const leafs: TvNode[] = eps.map((ep) => ({
        id: `e-${ep.media_id}`,
        _group: false,
        label: ep.from_path.split('/').pop() || ep.to_path.split('/').pop() || '',
        media_id: ep.media_id,
        from_path: ep.from_path,
        to_path: ep.to_path,
        conflict: ep.conflict,
      }))
      // season folder new name: take from any child's to_season_folder
      const seasonFolder = eps.find((e) => e.to_season_folder)?.to_season_folder
      seasonNodes.push({
        id: `s-${showId}-${sn}`,
        _group: true,
        label: sn > 0 ? `第 ${sn} 季` : '特别篇',
        newFolder: seasonFolder || undefined,
        children: leafs,
      })
    }
    // show folder new name: take from any child's to_show_folder
    const showFolder = [...s.seasons.values()].flat().find((e) => e.to_show_folder)?.to_show_folder
    tree.push({
      id: `t-${showId}`,
      _group: true,
      label: s.title,
      newFolder: showFolder || undefined,
      children: seasonNodes,
    })
  }
  return tree
})
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
        @change="onTemplateInput"
      />
    </div>

    <!-- Movies: flat table -->
    <el-table
      v-if="items.length && !isTv"
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

    <!-- TV: hierarchical tree table (show -> season -> episode) -->
    <el-table
      v-else-if="isTv && tvTree.length"
      :data="tvTree"
      row-key="id"
      :tree-props="{ children: 'children' }"
      default-expand-all
      style="width:100%;margin-top:16px"
      @selection-change="(rows: TvNode[]) => (selected = rows.filter((r) => !r._group).map((r) => r.media_id!))"
    >
      <el-table-column type="selection" width="45" :selectable="(row: TvNode) => !row._group && !row.conflict" />
      <el-table-column label="名称">
        <template #default="{ row }">
          <span v-if="row._group" class="group-label">
            {{ row.label }}
            <span v-if="row.newFolder && row.newFolder !== row.label" class="folder-new">→ {{ row.newFolder }}</span>
          </span>
          <span v-else :class="{ conflict: row.conflict }">{{ row.label }}</span>
        </template>
      </el-table-column>
      <el-table-column label="" width="40" center>
        <template #default="{ row }">
          <span v-if="!row._group">→</span>
        </template>
      </el-table-column>
      <el-table-column label="重命名为">
        <template #default="{ row }">
          <!-- group rows: folder rename shown above (in 名称 column); leaf rows: new filename -->
          <span v-if="!row._group" :class="{ conflict: row.conflict }">{{ shortPath(row.to_path) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <template v-if="!row._group">
            <el-tag v-if="row.conflict" size="small" type="danger">冲突</el-tag>
            <el-tag v-else size="small" type="success">可重命名</el-tag>
          </template>
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
.group-label { font-weight: 600; color: var(--accent); }
.folder-new { color: var(--accent-2); font-weight: 400; font-size: 13px; }
</style>
