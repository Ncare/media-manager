<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { renameApi, librariesApi, moviesApi, tvApi } from '@/api'
import type { RenameToken, RenamePreviewItem, Movie, Episode, TvShow } from '@/types'

const props = defineProps<{
  modelValue: string
  libraryId?: number
  mediaType: 'movie' | 'tv'      // which kind of sample to preview against
  label?: string
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'change', v: string): void
}>()

const tokens = ref<RenameToken[]>([])
const loading = ref(false)
const samplePreview = ref<RenamePreviewItem | null>(null)
// Element Plus el-input exposes the underlying <input> via .input ref; we grab
// it on mount so we can read/restore the cursor for at-cursor token insertion.
const inputRef = ref<any>(null)
let caret: number | null = null  // last known selection start (-1 = end)

function syncCaret() {
  const el = inputRef.value?.input as HTMLInputElement | undefined
  if (el) caret = el.selectionStart ?? props.modelValue.length
}

function focusInput() {
  // refocus so the user can keep typing right after the inserted token.
  const el = inputRef.value?.input as HTMLInputElement | undefined
  if (el) el.focus()
}

onMounted(async () => {
  try {
    tokens.value = await renameApi.tokens()
  } catch { /* tokens optional */ }
  await loadTokenAvailability()
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
watch(() => props.libraryId, () => loadTokenAvailability())

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
  const snippet = `{${t}}`
  const cur = props.modelValue
  // If we have a recorded caret position, insert there; otherwise append.
  const at = caret != null && caret <= cur.length ? caret : cur.length
  const v = cur.slice(0, at) + snippet + cur.slice(at)
  emit('update:modelValue', v)
  emit('change', v)
  // Restore caret right after the inserted snippet, on next tick (input value
  // needs to propagate to the DOM first).
  const pos = at + snippet.length
  requestAnimationFrame(() => {
    const el = inputRef.value?.input as HTMLInputElement | undefined
    if (el) {
      el.focus()
      el.setSelectionRange(pos, pos)
      caret = pos
    }
  })
}

// Used as v-model's update handler. Going through a real v-model (instead of
// :model-value + manual @input on the native event) fixes IME composition and
// backspace issues where the prop overwrote the input mid-edit.
function onInput(v: string) {
  emit('update:modelValue', v)
  emit('change', v)
  caret = null  // user typed directly; let next insert fall back to end
}

function shortPath(p: string) {
  const parts = p.split('/')
  return parts.slice(-2).join('/')
}

// ---- Token availability (which tokens have values in this library) ----
// null = unknown (no library context, e.g. on the Settings page). Set of token
// names that are populated for at least one media item in the library.
const tokenAvailability = ref<Record<string, 'filled' | 'empty'>>({})

async function loadTokenAvailability() {
  if (!props.libraryId) {
    tokenAvailability.value = {}
    return
  }
  try {
    tokenAvailability.value = await renameApi.tokenAvailability(props.libraryId, props.mediaType)
  } catch {
    tokenAvailability.value = {}
  }
}

function tokenStatus(token: string): 'filled' | 'empty' | 'unknown' {
  const s = tokenAvailability.value[token]
  if (s) return s
  return 'unknown'
}

// Whether we have real availability data (i.e. a library context). Drives the
// legend display.
const hasAvailability = computed(() => Object.keys(tokenAvailability.value).length > 0)

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
      ref="inputRef"
      :model-value="modelValue"
      :placeholder="placeholder || '命名模板...'"
      @update:modelValue="onInput"
      @click="syncCaret"
      @keyup="syncCaret"
      @focus="syncCaret"
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
      <div v-if="hasAvailability" class="legend">
        <span class="legend-item"><i class="dot dot-filled"></i>有数据</span>
        <span class="legend-item"><i class="dot dot-empty"></i>空</span>
        <span class="muted" style="font-size:11px">基于本媒体库的真实媒体统计</span>
      </div>
      <div v-for="(items, group) in groupedTokens" :key="group" class="token-group">
        <div class="group-title">{{ group }}</div>
        <div class="token-list">
          <el-tag
            v-for="t in items"
            :key="t.token"
            size="small"
            :class="['token-tag', 'tok-' + tokenStatus(t.token)]"
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
/* token availability states (only shown when a library context exists) */
.tok-filled { border-color: var(--accent-2, #67c23a) !important; color: var(--accent-2, #67c23a) !important; }
.tok-empty { opacity: 0.4; border-style: dashed !important; }
.tok-unknown { /* default look */ }
/* legend */
.legend { display: flex; align-items: center; gap: 12px; margin-bottom: 2px; font-size: 12px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.dot-filled { background: var(--accent-2, #67c23a); }
.dot-empty { background: transparent; border: 1.5px dashed var(--muted, #999); box-sizing: border-box; }
code { background: var(--panel-2); padding: 1px 5px; border-radius: 3px; }
</style>
