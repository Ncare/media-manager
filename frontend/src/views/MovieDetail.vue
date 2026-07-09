<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { moviesApi, scrapeApi } from '@/api'
import ScrapeDialog from '@/components/ScrapeDialog.vue'
import type { Movie } from '@/types'

const props = defineProps<{ id: string | number }>()
const router = useRouter()
const movie = ref<Movie | null>(null)
const loading = ref(false)
const scrapeVisible = ref(false)

async function load() {
  loading.value = true
  try {
    movie.value = await moviesApi.get(Number(props.id))
  } finally {
    loading.value = false
  }
}
onMounted(load)

function defaultQuery() {
  return movie.value?.title || movie.value?.parsed_title || ''
}
async function autoScrape() {
  if (!movie.value) return
  try {
    const results = await scrapeApi.search(defaultQuery(), 'movie', movie.value.parsed_year || undefined)
    if (!results.length) {
      ElMessage.warning('未找到匹配结果,请手动搜索')
      scrapeVisible.value = true
      return
    }
    await scrapeApi.match('movie', movie.value.id, results[0].tmdb_id)
    ElMessage.success('已自动匹配并刮削')
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '刮削失败')
  }
}
</script>

<template>
  <div class="page" v-loading="loading">
    <el-button text @click="router.back()">← 返回</el-button>
    <div v-if="movie" class="detail">
      <div
        class="backdrop"
        :style="{ backgroundImage: movie.backdrop_path ? `url(${movie.backdrop_path})` : 'var(--panel)' }"
      >
        <div class="poster" :style="{ backgroundImage: movie.poster_path ? `url(${movie.poster_path})` : '' }">
          <span v-if="!movie.poster_path" class="muted">无封面</span>
        </div>
      </div>
      <div class="info">
        <div class="title-row">
          <h2>{{ movie.title || movie.filename }}</h2>
          <span v-if="movie.year" class="year">({{ movie.year }})</span>
          <el-tag v-if="movie.rating" size="small">★ {{ movie.rating.toFixed(1) }}</el-tag>
          <el-tag v-if="!movie.scraped" size="small" type="info">未刮削</el-tag>
        </div>
        <div class="genres muted" v-if="movie.genres">{{ movie.genres }}</div>
        <p class="overview">{{ movie.overview || '暂无简介' }}</p>

        <div class="file-info muted">
          <div>文件: {{ movie.file_path }}</div>
          <div>分辨率: {{ movie.resolution || '—' }} · TMDB: {{ movie.tmdb_id || '—' }}</div>
        </div>

        <div class="actions">
          <el-button type="primary" @click="scrapeVisible = true">手动搜索匹配</el-button>
          <el-button @click="autoScrape">自动刮削</el-button>
        </div>
      </div>
    </div>
    <ScrapeDialog
      v-model:visible="scrapeVisible"
      media-type="movie"
      :media-id="Number(props.id)"
      :default-query="defaultQuery()"
      :default-year="movie?.parsed_year"
      @matched="load"
    />
  </div>
</template>

<style scoped>
.detail { display: flex; gap: 24px; margin-top: 12px; }
.backdrop {
  width: 300px; height: 450px; border-radius: 12px;
  background: var(--panel-2) center/cover; position: relative;
  border: 1px solid var(--border); flex-shrink: 0;
}
.poster {
  position: absolute; bottom: -1px; left: -1px; width: 130px; height: 195px;
  border-radius: 8px; background: var(--panel) center/cover;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
  border: 1px solid var(--border);
}
.info { flex: 1; }
.title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.title-row h2 { margin: 0; }
.year { color: var(--muted); }
.genres { margin-top: 8px; font-size: 13px; }
.overview { margin-top: 12px; line-height: 1.7; font-size: 14px; }
.file-info { margin-top: 16px; font-size: 12px; word-break: break-all; line-height: 1.8; }
.actions { margin-top: 20px; display: flex; gap: 10px; }
</style>
