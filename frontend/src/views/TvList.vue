<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { librariesApi, tvApi } from '@/api'
import type { Library, TvShow } from '@/types'

const router = useRouter()
const shows = ref<TvShow[]>([])
const libraries = ref<Library[]>([])
const selectedLib = ref<number | undefined>(undefined)
const search = ref('')
const onlyUnscraped = ref(false)
const loading = ref(false)

const tvLibs = computed(() => libraries.value.filter((l) => l.type === 'tv'))

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { size: 500 }
    if (selectedLib.value) params.library_id = selectedLib.value
    if (onlyUnscraped.value) params.scraped = false
    if (search.value) params.q = search.value
    shows.value = await tvApi.list(params)
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  libraries.value = await librariesApi.list()
  await load()
})
</script>

<template>
  <div class="page">
    <h2>电视剧</h2>
    <div class="toolbar">
      <el-select v-model="selectedLib" placeholder="全部媒体库" clearable style="width:180px" @change="load">
        <el-option v-for="l in tvLibs" :key="l.id" :label="l.name" :value="l.id" />
      </el-select>
      <el-input v-model="search" placeholder="搜索..." clearable style="width:220px" @change="load" />
      <el-checkbox v-model="onlyUnscraped" @change="load">仅未刮削</el-checkbox>
      <el-button @click="load">刷新</el-button>
    </div>

    <div v-loading="loading" class="poster-grid" style="margin-top:16px">
      <div v-for="s in shows" :key="s.id" class="poster-card" @click="router.push(`/tv/${s.id}`)">
        <div class="poster" :style="{ backgroundImage: s.poster_path ? `url(${s.poster_path})` : '' }">
          <span v-if="!s.poster_path" class="no-poster">无封面</span>
        </div>
        <div class="meta">
          <div class="title">{{ s.title || s.folder_path.split('/').pop() }}</div>
          <div class="sub">
            {{ s.season_count }}季 · {{ s.episode_count }}集
            <el-tag v-if="!s.scraped" size="small" type="info">未刮削</el-tag>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-if="!loading && !shows.length" description="暂无剧集,先去媒体库扫描吧" />
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.no-poster { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--muted); font-size: 12px; }
</style>
