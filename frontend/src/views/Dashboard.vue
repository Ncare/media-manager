<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { librariesApi, moviesApi, tvApi, settingsApi, tasksApi } from '@/api'
import type { Library, AppSettings, Task } from '@/types'

const libraries = ref<Library[]>([])
const movieTotal = ref(0)
const tvTotal = ref(0)
const settings = ref<AppSettings | null>(null)
const tasks = ref<Task[]>([])

onMounted(async () => {
  const [libs, settingsData, taskList] = await Promise.all([
    librariesApi.list(),
    settingsApi.get(),
    tasksApi.list(),
  ])
  libraries.value = libs
  settings.value = settingsData
  tasks.value = taskList.slice(0, 10)
  if (libs.some((l) => l.type === 'movie')) {
    moviesApi.list({ size: 1 }).then((m) => (movieTotal.value = m.length))
  }
  if (libs.some((l) => l.type === 'tv')) {
    tvApi.list({ size: 1 }).then((t) => (tvTotal.value = t.length))
  }
})
</script>

<template>
  <div class="page">
    <h2>概览</h2>

    <div class="cards">
      <div class="stat">
        <div class="num">{{ libraries.length }}</div>
        <div class="label">媒体库</div>
      </div>
      <div class="stat">
        <div class="num">{{ movieTotal }}</div>
        <div class="label">电影</div>
      </div>
      <div class="stat">
        <div class="num">{{ tvTotal }}</div>
        <div class="label">电视剧</div>
      </div>
      <div class="stat">
        <div class="num" :class="{ ok: settings?.tmdb_configured, warn: !settings?.tmdb_configured }">
          {{ settings?.tmdb_configured ? '已配置' : '未配置' }}
        </div>
        <div class="label">TMDB</div>
      </div>
    </div>

    <h3>媒体库</h3>
    <el-table v-if="libraries.length" :data="libraries" style="width:100%">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="type" label="类型" width="90" />
      <el-table-column prop="root_path" label="路径" />
      <el-table-column label="数量" width="100">
        <template #default="{ row }">
          {{ row.type === 'movie' ? row.movie_count : row.tv_count }}
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="还没有媒体库,去「媒体库」创建一个吧" />

    <h3>最近任务</h3>
    <el-table v-if="tasks.length" :data="tasks" style="width:100%">
      <el-table-column prop="type" label="类型" width="90" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="信息" />
      <el-table-column prop="updated_at" label="时间" width="200">
        <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString() }}</template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="暂无任务" />
  </div>
</template>

<style scoped>
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}
.stat .num { font-size: 28px; font-weight: 700; }
.stat .label { color: var(--muted); font-size: 13px; margin-top: 4px; }
.num.ok { color: var(--accent-2); }
.num.warn { color: var(--danger); }
h3 { margin: 24px 0 12px; font-size: 16px; }
</style>
