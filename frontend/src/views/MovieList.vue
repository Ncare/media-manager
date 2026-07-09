<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { librariesApi, moviesApi } from '@/api'
import type { Library, Movie } from '@/types'

const router = useRouter()
const movies = ref<Movie[]>([])
const libraries = ref<Library[]>([])
const selectedLib = ref<number | undefined>(undefined)
const onlyUnscraped = ref(false)
const search = ref('')
const loading = ref(false)

const movieLibs = computed(() => libraries.value.filter((l) => l.type === 'movie'))

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { size: 500 }
    if (selectedLib.value) params.library_id = selectedLib.value
    if (onlyUnscraped.value) params.scraped = false
    if (search.value) params.q = search.value
    movies.value = await moviesApi.list(params)
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  libraries.value = await librariesApi.list()
  await load()
})

function title(m: Movie) {
  return m.title || m.filename
}
function poster(m: Movie) {
  return m.poster_path || ''
}
</script>

<template>
  <div class="page">
    <h2>电影</h2>
    <div class="toolbar">
      <el-select v-model="selectedLib" placeholder="全部媒体库" clearable style="width:180px" @change="load">
        <el-option v-for="l in movieLibs" :key="l.id" :label="l.name" :value="l.id" />
      </el-select>
      <el-input v-model="search" placeholder="搜索..." clearable style="width:220px" @change="load" />
      <el-checkbox v-model="onlyUnscraped" @change="load">仅未刮削</el-checkbox>
      <el-button @click="load">刷新</el-button>
    </div>

    <div v-loading="loading" class="poster-grid" style="margin-top:16px">
      <div v-for="m in movies" :key="m.id" class="poster-card" @click="router.push(`/movies/${m.id}`)">
        <div class="poster" :style="{ backgroundImage: poster(m) ? `url(${poster(m)})` : '' }">
          <span v-if="!poster(m)" class="no-poster">无封面</span>
        </div>
        <div class="meta">
          <div class="title">{{ title(m) }}</div>
          <div class="sub">
            {{ m.year || '—' }}
            <el-tag v-if="!m.scraped" size="small" type="info">未刮削</el-tag>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-if="!loading && !movies.length" description="暂无电影,先去媒体库扫描吧" />
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.no-poster {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--muted); font-size: 12px;
}
</style>
