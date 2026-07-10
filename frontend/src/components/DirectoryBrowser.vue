<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { librariesApi } from '@/api'

const props = defineProps<{
  modelValue: boolean   // dialog visibility
  current?: string      // currently-selected path (pre-highlights it)
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'pick', path: string): void
}>()

// el-tree node shape. `path` is relative to the media root (what we store).
interface DirNode {
  name: string
  path: string
}

const treeRef = ref()
// Bumped on every open so el-tree fully remounts with a clean lazy store,
// avoiding stale/duplicated nodes from a previous session.
const treeKey = ref(0)
const selected = ref('')

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selected.value = props.current ?? ''
      treeKey.value++ // fresh tree each open
    }
  },
)

// Pure lazy loading: el-tree calls this for EVERY level, including the root
// (level 0, where node.data is undefined). A single data source means no
// duplication.
async function load(node: any, resolve: (children: DirNode[]) => void) {
  try {
    const path = node.level === 0 ? '' : node.data?.path ?? ''
    const dirs = await librariesApi.browse(path)
    resolve(dirs.map((d) => ({ name: d.name, path: d.path })))
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '读取目录失败')
    resolve([])
  }
}

function handleNodeClick(data: DirNode) {
  selected.value = data.path
}

function confirmPick() {
  if (!selected.value) {
    ElMessage.warning('请先选择一个目录')
    return
  }
  emit('pick', selected.value)
  emit('update:modelValue', false)
}

// Whether a node is the currently-highlighted selection.
function isSelected(data: DirNode) {
  return data.path === selected.value
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    title="选择目录"
    width="480px"
    append-to-body
  >
    <div class="path-bar">
      <span class="muted">媒体根目录 / </span>
      <strong>{{ selected || '（点击下方目录选择）' }}</strong>
    </div>
    <el-tree
      ref="treeRef"
      :key="treeKey"
      :data="[]"
      node-key="path"
      :props="{ label: 'name' }"
      lazy
      :load="load"
      :highlight-current="true"
      :expand-on-click-node="false"
      @node-click="handleNodeClick"
      class="dir-tree"
    >
      <template #default="{ data }">
        <span class="tree-row" :class="{ active: isSelected(data) }">
          <span class="tree-name">{{ data.name }}</span>
        </span>
      </template>
    </el-tree>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="confirmPick">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.path-bar {
  padding: 8px 12px;
  background: var(--panel-2);
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  word-break: break-all;
}
.dir-tree {
  max-height: 360px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 4px;
}
.tree-row {
  display: flex;
  align-items: center;
  flex: 1;
  padding: 2px 4px;
}
.tree-row.active .tree-name {
  color: var(--accent);
  font-weight: 600;
}
.tree-name {
  font-size: 14px;
}
</style>
