<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { scrapeApi } from '@/api'
import type { TmdbSearchResult } from '@/types'

const props = defineProps<{
  visible: boolean
  mediaType: string           // movie | tv
  mediaId: number
  defaultQuery: string
  defaultYear?: number | null
}>()
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'matched'): void
}>()

const query = ref('')
const year = ref<number | undefined>(undefined)
const results = ref<TmdbSearchResult[]>([])
const loading = ref(false)
// tmdb_id of the result currently being matched, or null. Using a per-item
// id instead of a single boolean means clicking "匹配" on one row only
// spins that one button — not every button in the list.
const matchingId = ref<number | null>(null)
// Inline error banner (shown instead of just a toast so the cause survives).
// null = no error; { title, detail } = error to show.
const error = ref<{ title: string; detail: string } | null>(null)

watch(
  () => props.visible,
  (v) => {
    if (v) {
      query.value = props.defaultQuery
      year.value = props.defaultYear || undefined
      results.value = []
      error.value = null
      if (query.value) search()
    }
  }
)

/** Build a human-readable Chinese error message from an axios error.
 *  Distinguishes backend/TMDB errors from network/infra failures, since the
 *  generic "搜索失败" toast hid the real cause (e.g. bad key, NAS offline). */
function toError(e: any): { title: string; detail: string } {
  const status = e?.response?.status
  const detail = e?.response?.data?.detail
  if (status === 400 || status === 502) {
    // Backend or TMDB rejected the request — detail is already localized server-side.
    return { title: '搜索失败', detail: detail || 'TMDB 返回错误' }
  }
  if (!e?.response) {
    // No HTTP response → network/CORS/backend-down. This is the case that was
    // previously swallowed into a bare "搜索失败".
    return {
      title: '无法连接服务',
      detail: e?.message
        ? `网络错误:${e.message}(后端可能未启动或不可达)`
        : '无法连接到后端服务,请检查容器是否在运行',
    }
  }
  return { title: '搜索失败', detail: detail || `服务返回 ${status}` }
}

async function search() {
  if (!query.value) return
  loading.value = true
  error.value = null
  try {
    results.value = await scrapeApi.search(query.value, props.mediaType, year.value)
  } catch (e: any) {
    error.value = toError(e)
  } finally {
    loading.value = false
  }
}

async function match(r: TmdbSearchResult) {
  matchingId.value = r.tmdb_id
  try {
    await scrapeApi.match(props.mediaType, props.mediaId, r.tmdb_id)
    ElMessage.success('已匹配并刮削')
    emit('update:visible', false)
    emit('matched')
  } catch (e: any) {
    const err = toError(e)
    error.value = { title: '匹配失败', detail: err.detail }
  } finally {
    matchingId.value = null
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="刮削匹配 (TMDB)"
    width="640px"
  >
    <div class="search-bar">
      <el-input v-model="query" placeholder="搜索电影/剧集名称..." style="flex:1" @keyup.enter="search" />
      <el-input-number v-model="year" :min="1900" :max="2099" placeholder="年份(可选)" style="width:130px" controls-position="right" />
      <el-button type="primary" :loading="loading" @click="search">搜索</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error.title"
      :description="error.detail"
      type="error"
      show-icon
      :closable="false"
      style="margin-bottom: 12px"
    />

    <div v-loading="loading" class="results">
      <div v-for="r in results" :key="r.tmdb_id" class="result">
        <div class="thumb" :style="{ backgroundImage: r.poster_url ? `url(${r.poster_url})` : '' }">
          <span v-if="!r.poster_url" class="muted">无图</span>
        </div>
        <div class="info">
          <div class="t">{{ r.title }} <span class="muted" v-if="r.original_title">({{ r.original_title }})</span></div>
          <div class="y muted">{{ r.year || '—' }}</div>
          <div class="o muted">{{ r.overview || '暂无简介' }}</div>
        </div>
        <el-button type="primary" size="small" :loading="matchingId === r.tmdb_id" @click="match(r)">匹配</el-button>
      </div>
      <el-empty v-if="!loading && !results.length && !error" description="输入名称后点「搜索」" />
    </div>
  </el-dialog>
</template>

<style scoped>
.search-bar { display: flex; gap: 10px; margin-bottom: 16px; }
.results { max-height: 460px; overflow-y: auto; }
.result { display: flex; gap: 12px; padding: 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; align-items: flex-start; }
.thumb { width: 54px; height: 80px; flex-shrink: 0; background: var(--panel-2) center/cover; border-radius: 4px; display:flex; align-items:center; justify-content:center; font-size:11px; }
.info { flex: 1; min-width: 0; }
.info .t { font-weight: 600; }
.info .o { font-size: 12px; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
