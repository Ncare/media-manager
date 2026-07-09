<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { tvApi, scrapeApi } from '@/api'
import ScrapeDialog from '@/components/ScrapeDialog.vue'
import type { TvShow, Episode } from '@/types'

const props = defineProps<{ id: string | number }>()
const router = useRouter()
const show = ref<TvShow | null>(null)
const episodes = ref<Episode[]>([])
const loading = ref(false)
const scrapeVisible = ref(false)

async function load() {
  loading.value = true
  try {
    show.value = await tvApi.get(Number(props.id))
    // fetch all seasons' episodes; iterate seasons present in folder structure (1..2 typical)
    const eps: Episode[] = []
    for (let s = 1; s <= 5; s++) {
      try {
        const list = await tvApi.episodes(Number(props.id), s)
        if (list.length) eps.push(...list)
      } catch { /* season may not exist */ }
    }
    episodes.value = eps
  } finally {
    loading.value = false
  }
}
onMounted(load)

function defaultQuery() {
  return show.value?.title || show.value?.parsed_title || show.value?.folder_path.split('/').pop() || ''
}

async function autoScrape() {
  if (!show.value) return
  try {
    const results = await scrapeApi.search(defaultQuery(), 'tv', show.value.parsed_year || undefined)
    if (!results.length) {
      ElMessage.warning('未找到匹配结果,请手动搜索')
      scrapeVisible.value = true
      return
    }
    await scrapeApi.match('tv', show.value.id, results[0].tmdb_id)
    ElMessage.success('已自动匹配并刮削(含剧集)')
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '刮削失败')
  }
}
</script>

<template>
  <div class="page" v-loading="loading">
    <el-button text @click="router.back()">← 返回</el-button>
    <div v-if="show" class="detail">
      <div class="poster" :style="{ backgroundImage: show.poster_path ? `url(${show.poster_path})` : '' }">
        <span v-if="!show.poster_path" class="muted">无封面</span>
      </div>
      <div class="info">
        <div class="title-row">
          <h2>{{ show.title || show.folder_path.split('/').pop() }}</h2>
          <span v-if="show.year" class="year">({{ show.year }})</span>
          <el-tag v-if="show.rating" size="small">★ {{ show.rating.toFixed(1) }}</el-tag>
          <el-tag v-if="!show.scraped" size="small" type="info">未刮削</el-tag>
        </div>
        <div class="genres muted" v-if="show.genres">{{ show.genres }}</div>
        <p class="overview">{{ show.overview || '暂无简介' }}</p>
        <div class="file-info muted">
          <div>{{ show.season_count }}季 · {{ show.episode_count }}集 · TMDB: {{ show.tmdb_id || '—' }}</div>
          <div>{{ show.folder_path }}</div>
        </div>
        <div class="actions">
          <el-button type="primary" @click="scrapeVisible = true">手动搜索匹配</el-button>
          <el-button @click="autoScrape">自动刮削(全剧)</el-button>
        </div>
      </div>
    </div>

    <h3 style="margin-top:24px">剧集</h3>
    <el-table v-if="episodes.length" :data="episodes" style="width:100%">
      <el-table-column label="集" width="80">
        <template #default="{ row }">S{{ String(row.season_number).padStart(2,'0') }}E{{ String(row.episode_number).padStart(2,'0') }}</template>
      </el-table-column>
      <el-table-column prop="title" label="标题">
        <template #default="{ row }">{{ row.title || row.filename }}</template>
      </el-table-column>
      <el-table-column prop="overview" label="简介" show-overflow-tooltip>
        <template #default="{ row }">{{ row.overview || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="!row.scraped" size="small" type="info">未刮削</el-tag>
          <el-tag v-else size="small" type="success">已刮削</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无剧集" />

    <ScrapeDialog
      v-model:visible="scrapeVisible"
      media-type="tv"
      :media-id="Number(props.id)"
      :default-query="defaultQuery()"
      :default-year="show?.parsed_year"
      @matched="load"
    />
  </div>
</template>

<style scoped>
.detail { display: flex; gap: 24px; margin-top: 12px; }
.poster { width: 180px; height: 270px; border-radius: 12px; background: var(--panel-2) center/cover; border: 1px solid var(--border); flex-shrink: 0; display:flex; align-items:center; justify-content:center; font-size:12px; }
.info { flex: 1; }
.title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.title-row h2 { margin: 0; }
.year { color: var(--muted); }
.genres { margin-top: 8px; font-size: 13px; }
.overview { margin-top: 12px; line-height: 1.7; font-size: 14px; }
.file-info { margin-top: 16px; font-size: 12px; word-break: break-all; line-height: 1.8; }
.actions { margin-top: 20px; display: flex; gap: 10px; }
</style>
