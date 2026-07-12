<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { librariesApi, settingsApi } from '@/api'
import type { Library, LibraryType } from '@/types'
import NamingTemplateEditor from '@/components/NamingTemplateEditor.vue'
import DirectoryBrowser from '@/components/DirectoryBrowser.vue'

const libraries = ref<Library[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const browserVisible = ref(false)
const editing = ref<Library | null>(null)
// Global default templates pulled from the Settings page, so the create form
// starts with whatever the user configured there (not a stale hard-coded value).
const globalDefaults = ref({ movie: '', tv: '', tvShow: '' })
const form = ref({
  name: '',
  type: 'movie' as LibraryType,
  root_path: '',
  naming_template: '',
  tv_show_template: '',
  auto_scrape: true,
})

async function load() {
  loading.value = true
  try {
    libraries.value = await librariesApi.list()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Fetch the global default templates once on mount so openCreate() can use
  // them without an extra round-trip each time the dialog opens.
  try {
    const s = await settingsApi.get()
    globalDefaults.value = {
      movie: s.default_movie_template,
      tv: s.default_tv_template,
      tvShow: s.default_tv_show_template,
    }
  } catch { /* fall back to empty; form will show placeholders */ }
  await load()
})

function openCreate() {
  editing.value = null
  form.value = {
    name: '',
    type: 'movie',
    root_path: '',
    // Start from the Settings-page global defaults. type change will swap them.
    naming_template: globalDefaults.value.movie,
    tv_show_template: globalDefaults.value.tvShow,
    auto_scrape: true,
  }
  dialogVisible.value = true
}

// When the user switches type in the create form, swap to that type's global
// default template (only if they haven't manually edited it yet — but since
// this is a fresh form, it's always safe to overwrite here).
watch(() => form.value.type, (t) => {
  if (editing.value) return  // don't change an existing library's templates
  form.value.naming_template = t === 'tv' ? globalDefaults.value.tv : globalDefaults.value.movie
  form.value.tv_show_template = globalDefaults.value.tvShow
})

function openEdit(lib: Library) {
  editing.value = lib
  form.value = {
    name: lib.name,
    type: lib.type,
    root_path: lib.root_path,
    naming_template: lib.naming_template,
    tv_show_template: lib.tv_show_template,
    auto_scrape: lib.auto_scrape,
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name || !form.value.root_path) {
    ElMessage.warning('请填写名称和路径')
    return
  }
  try {
    if (editing.value) {
      await librariesApi.update(editing.value.id, form.value)
      ElMessage.success('已更新')
    } else {
      await librariesApi.create(form.value)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  }
}

async function scan(lib: Library) {
  try {
    const res = await librariesApi.scan(lib.id)
    ElMessage.success(`扫描已启动 (任务 ${res.task_id})`)
    setTimeout(load, 1500)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '扫描失败')
  }
}

async function remove(lib: Library) {
  await ElMessageBox.confirm(`确定删除媒体库「${lib.name}」?(不会删除媒体文件)`, '确认', {
    type: 'warning',
  })
  await librariesApi.remove(lib.id)
  ElMessage.success('已删除')
  load()
}

function onPickPath(path: string) {
  form.value.root_path = path
}
</script>

<template>
  <div class="page">
    <div class="header">
      <h2>媒体库</h2>
      <el-button type="primary" @click="openCreate">+ 新建媒体库</el-button>
    </div>

    <el-table v-loading="loading" :data="libraries" style="width:100%">
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="type" label="类型" width="90">
        <template #default="{ row }">{{ row.type === 'movie' ? '电影' : '电视剧' }}</template>
      </el-table-column>
      <el-table-column prop="root_path" label="路径" />
      <el-table-column label="数量" width="100">
        <template #default="{ row }">
          {{ row.type === 'movie' ? row.movie_count : row.tv_count }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="scan(row)">扫描</el-button>
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑媒体库' : '新建媒体库'" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如:电影" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio value="movie">电影</el-radio>
            <el-radio value="tv">电视剧</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="form.root_path" placeholder="相对于媒体根目录,例如:Movies">
            <template #append>
              <el-button @click="browserVisible = true">浏览</el-button>
            </template>
          </el-input>
          <div class="muted" style="font-size:12px;margin-top:4px">
            点「浏览」从目录树选择,或手动输入;容器内对应 /media/&lt;路径&gt;
          </div>
        </el-form-item>
        <el-form-item label="命名模板">
          <NamingTemplateEditor
            v-model="form.naming_template"
            :library-id="editing?.id"
            :media-type="form.type"
            placeholder="如:{title} ({year})/{originalTitle;title} ({year}) [{resolution}]{ext}"
          />
          <div class="muted" style="font-size:12px">
            点下方标签可插入 token;支持回退语法 <code>{a;b;c}</code>(取第一个非空值)
            <span v-if="form.type === 'tv'"> · 剧集额外支持 {season} {episode} {seasonEpisode} {showTitle}</span>
          </div>
        </el-form-item>
        <el-form-item v-if="form.type === 'tv'" label="剧集文件夹模板">
          <el-input v-model="form.tv_show_template" placeholder="如:{showTitle} ({year})" />
          <div class="muted" style="font-size:12px;margin-top:4px">用于重命名剧集的根文件夹</div>
        </el-form-item>
        <el-form-item label="扫描后自动刮削">
          <el-switch v-model="form.auto_scrape" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <DirectoryBrowser
      v-model="browserVisible"
      :current="form.root_path"
      @pick="onPickPath"
    />
  </div>
</template>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; }
</style>
