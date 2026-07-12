<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsApi } from '@/api'
import { useThemeStore } from '@/stores/theme'
import type { AppSettings } from '@/types'

const theme = useThemeStore()

const settings = ref<AppSettings | null>(null)
const apiKey = ref('')
// Masked key returned by backend (e.g. "****abcd"); used as the input's
// initial display so the user can see a key is configured without exposing
// it. A save only submits the key when the user edits it away from this.
const maskedKey = ref('')
const language = ref('zh-CN')
const proxyUrl = ref('')
const proxyEnabled = ref(false)
const saving = ref(false)
const showKey = ref(false)
const testing = ref(false)
// Result of the last "test connection" run; null = not tested yet.
const testResult = ref<{ ok: boolean; message: string } | null>(null)

async function testKey() {
  testing.value = true
  testResult.value = null
  try {
    // If the input still holds the masked value, the user hasn't changed it —
    // send no key so the backend tests its currently configured key instead.
    const raw = apiKey.value
    const key = raw && raw !== maskedKey.value ? raw : undefined
    testResult.value = await settingsApi.testTmdb(key)
  } catch (e: any) {
    testResult.value = {
      ok: false,
      message: e?.response?.data?.detail || e?.message || '测试失败,无法连接后端',
    }
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  settings.value = await settingsApi.get()
  language.value = settings.value.tmdb_language
  maskedKey.value = settings.value.tmdb_key_masked || ''
  apiKey.value = maskedKey.value
  proxyUrl.value = settings.value.tmdb_proxy_url || ''
  proxyEnabled.value = settings.value.tmdb_proxy_enabled
})

async function save() {
  saving.value = true
  try {
    const payload: Partial<AppSettings> & { tmdb_api_key?: string } = {
      tmdb_language: language.value,
      tmdb_proxy_url: proxyUrl.value,
      tmdb_proxy_enabled: proxyEnabled.value,
    }
    if (apiKey.value && apiKey.value !== maskedKey.value) payload.tmdb_api_key = apiKey.value
    settings.value = await settingsApi.update(payload)
    proxyUrl.value = settings.value.tmdb_proxy_url || ''
    proxyEnabled.value = settings.value.tmdb_proxy_enabled
    maskedKey.value = settings.value.tmdb_key_masked || ''
    apiKey.value = maskedKey.value
    ElMessage.success('已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <h2>设置</h2>
    <el-card class="card">
      <div class="card-head">主题外观</div>
      <div class="theme-chips">
        <button
          v-for="t in theme.themes"
          :key="t.id"
          class="theme-chip"
          :class="{ active: theme.currentId === t.id }"
          :style="{ background: t.swatch }"
          @click="theme.setTheme(t.id)"
        >
          <span class="theme-chip-name">{{ t.label }}</span>
        </button>
      </div>
      <div class="muted" style="font-size:12px;margin-top:10px">
        当前:{{ theme.current.label }} · 选择会立即生效并记住
      </div>
    </el-card>

    <el-card class="card" style="margin-top:16px" v-if="settings">
      <div class="status">
        TMDB 状态:
        <el-tag :type="settings.tmdb_configured ? 'success' : 'danger'" size="small">
          {{ settings.tmdb_configured ? '已配置' : '未配置' }}
        </el-tag>
        <span class="muted" style="margin-left:8px">媒体根目录: {{ settings.media_root }}</span>
      </div>

      <el-form label-width="160px" style="margin-top:20px;max-width:640px">
        <el-form-item label="TMDB API Key">
          <el-input
            v-model="apiKey"
            :type="showKey ? 'text' : 'password'"
            placeholder="未配置;申请:themoviedb.org/settings/api"
          >
            <template #append>
              <el-button @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</el-button>
            </template>
          </el-input>
          <div class="key-actions">
            <el-button :loading="testing" @click="testKey">测试连接</el-button>
            <div class="muted" style="font-size:12px">
              免费申请:https://www.themoviedb.org/settings/api (选 Developer 类型) · 填好后可先「测试连接」再保存
            </div>
          </div>
          <el-alert
            v-if="testResult"
            :title="testResult.message"
            :type="testResult.ok ? 'success' : 'error'"
            show-icon
            :closable="true"
            @close="testResult = null"
            style="margin-top:8px"
          />
        </el-form-item>
        <el-form-item label="TMDB 语言">
          <el-select v-model="language" style="width:200px">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
            <el-option label="日本語" value="ja-JP" />
            <el-option label="繁體中文" value="zh-TW" />
          </el-select>
        </el-form-item>
        <el-divider content-position="left">网络代理(国内 NAS 访问 TMDB)</el-divider>
        <el-form-item label="启用代理">
          <el-switch v-model="proxyEnabled" />
          <span class="muted" style="margin-left:12px;font-size:12px">
            开启后,访问 TMDB 的请求经下方代理地址转发
          </span>
        </el-form-item>
        <el-form-item label="代理地址">
          <el-input
            v-model="proxyUrl"
            :disabled="!proxyEnabled"
            placeholder="http://192.168.x.x:7890"
            style="max-width:400px"
          />
          <div class="muted" style="font-size:12px;margin-top:4px">
            填 mihomo / Clash 的 mixed-port 地址(含 NAS 局域网 IP + 端口)。HTTP / SOCKS5 均可。
            配好后保存,再点上方「测试连接」验证。
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="card" style="margin-top:16px">
      <div class="muted">
        <strong>提示:</strong>环境变量 <code>TMDB_API_KEY</code> 会优先生效。
        如需更换,修改 .env 后重启容器,或在此页填入新 Key 保存。
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.card { background: var(--panel) !important; }
.status { display: flex; align-items: center; gap: 8px; }
code { background: var(--panel-2); padding: 2px 6px; border-radius: 4px; }
.card-head { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
/* 按钮 + 提示文字竖排,和输入框等宽对齐 */
.key-actions { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; margin-top: 8px; width: 100%; }
.theme-chips { display: flex; gap: 12px; flex-wrap: wrap; }
.theme-chip {
  position: relative;
  width: 96px; height: 56px;
  border-radius: 8px;
  border: 2px solid var(--border);
  cursor: pointer;
  overflow: hidden;
  display: flex; align-items: flex-end; justify-content: center;
  padding: 0 0 6px;
  transition: transform 0.12s, border-color 0.12s, box-shadow 0.12s;
}
.theme-chip:hover { transform: translateY(-2px); }
.theme-chip.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 30%, transparent);
}
.theme-chip-name {
  color: #fff; font-size: 12px; font-weight: 600;
  text-shadow: 0 1px 3px rgba(0,0,0,0.75);
  mix-blend-mode: difference;
}
</style>
