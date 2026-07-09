<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer,
  FolderOpened,
  Film,
  VideoCamera,
  Switch,
  Setting,
} from '@element-plus/icons-vue'
import { tasksApi } from '@/api'
import type { Task } from '@/types'

const route = useRoute()
const runningTasks = ref<Task[]>([])
let timer: number | undefined

const nav = [
  { to: '/', icon: Odometer, label: '概览' },
  { to: '/libraries', icon: FolderOpened, label: '媒体库' },
  { to: '/movies', icon: Film, label: '电影' },
  { to: '/tv', icon: VideoCamera, label: '电视剧' },
  { to: '/rename', icon: Switch, label: '重命名' },
  { to: '/settings', icon: Setting, label: '设置' },
]

async function refreshTasks() {
  try {
    const all = await tasksApi.list()
    runningTasks.value = all.filter((t) => t.status === 'running' || t.status === 'pending')
  } catch {
    /* ignore */
  }
}
onMounted(() => {
  refreshTasks()
  timer = window.setInterval(refreshTasks, 3000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">🎬</span>
        <span class="name">MediaManager</span>
      </div>
      <nav>
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: route.path === item.to }"
        >
          <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div v-if="runningTasks.length" class="tasks">
        <div class="tasks-title">运行中任务</div>
        <div v-for="t in runningTasks" :key="t.id" class="task">
          <span class="task-type">{{ t.type }}</span>
          <span class="task-msg">{{ t.message || t.status }}</span>
        </div>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; }
.sidebar {
  width: 200px;
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.brand {
  display: flex; align-items: center; gap: 8px;
  padding: 18px 16px;
  font-size: 16px; font-weight: 700;
  border-bottom: 1px solid var(--border);
}
.brand .logo { font-size: 20px; }
nav { padding: 12px 8px; display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  color: var(--muted);
  font-size: 14px;
}
.nav-item:hover { background: var(--panel-2); color: var(--text); }
.nav-item.active { background: var(--panel-2); color: var(--accent); }
.nav-item .nav-icon { font-size: 18px; flex-shrink: 0; }
.tasks { margin-top: auto; padding: 12px; border-top: 1px solid var(--border); font-size: 12px; }
.tasks-title { color: var(--muted); margin-bottom: 6px; }
.task { margin-bottom: 6px; }
.task-type { color: var(--accent-2); margin-right: 6px; }
.task-msg { color: var(--muted); }
.main { flex: 1; overflow-y: auto; }
</style>
