<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { renameApi, librariesApi, moviesApi, tvApi } from '@/api'
import type { RenameToken, RenamePreviewItem, Movie, Episode, TvShow } from '@/types'

const props = defineProps<{
  modelValue: string
  libraryId?: number
  mediaType: 'movie' | 'tv'      // which kind of sample to preview against
  label?: string
  placeholder?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const tokens = ref<RenameToken[]>([])
const loading = ref(false)
const samplePreview = ref<RenamePreviewItem | null>(null)

onMounted(async () => {
  try {
    tokens.value = await renameApi.tokens()
  } catch { /* tokens optional */ }
})

// Re-run preview whenever the template or library changes (debounced).
let timer: number | undefined
watch(
  () => [props.modelValue, props.libraryId],
  () => {
    if (timer) clearTimeout(timer)
    timer = window.setTimeout(refreshPreview, 350)
  }
)

async function refreshPreview() {
  if (!props.libraryId || !props.modelValue) {
    samplePreview.value = null
    return
  }
  loading.value = true
  try {
    const data = await renameApi.preview(props.libraryId, props.modelValue)
    samplePreview.value = data.items[0] || null
  } catch {
    samplePreview.value = null
  } finally {
    loading.value = false
  }
}

function insertToken(t: string) {
  // insert at cursor / append
  emit('update:modelValue', props.modelValue + `{${t}}`)
}

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}

function shortPath(p: string) {
  const parts = p.split('/')
  return parts.slice(-2).join('/')
}

const groupedTokens = ref<Record<string, RenameToken[]>>({})
watch(tokens, (tks) => {
  const g: Record<string, RenameToken[]> = {}
  for (const t of tks) (g[t.for] ||= []).push(t)
  groupedTokens.value = g
})
</script>

<template>
  <div class="template-editor">
    <el-input
      :model-value="modelValue"
      :placeholder="placeholder || '命名模板...'"
      @input="onInput"
    >
      <template #append>
        <el-tooltip content="模板中可用下方列出的 token;{a;b;c} 表示按顺序回退取第一个非空值" placement="top">
          <el-button>?</el-button>
        </el-tooltip>
      </template>
    </el-input>

    <!-- live preview -->
    <div v-if="samplePreview" class="preview" v-loading="loading">
      <span class="muted">预览:</span>
      <code class="from">{{ shortPath(samplePreview.from_path) }}</code>
      <span class="arrow">→</span>
      <code class="to">{{ shortPath(samplePreview.to_path) }}</code>
    </div>

    <!-- token cheat sheet -->
    <div class="tokens">
      <div v-for="(items, group) in groupedTokens" :key="group" class="token-group">
        <div class="group-title">{{ group }}</div>
        <div class="token-list">
          <el-tag
            v-for="t in items"
            :key="t.token"
            size="small"
            class="token-tag"
            @click="insertToken(t.token)"
            :title="t.desc + ' (示例:' + t.example + ')'"
          >
            {{ '{' + t.token + '}' }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.template-editor { display: flex; flex-direction: column; gap: 10px; }
.preview {
  font-size: 12px; padding: 8px 10px;
  background: var(--panel-2); border-radius: 6px;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.preview .arrow { color: var(--accent); }
.preview .from { color: var(--muted); text-decoration: line-through; }
.preview .to { color: var(--accent-2); }
.tokens { display: flex; flex-direction: column; gap: 8px; }
.token-group { }
.group-title { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.token-list { display: flex; flex-wrap: wrap; gap: 6px; }
.token-tag { cursor: pointer; }
.token-tag:hover { opacity: 0.85; }
code { background: var(--panel-2); padding: 1px 5px; border-radius: 3px; }
</style>
