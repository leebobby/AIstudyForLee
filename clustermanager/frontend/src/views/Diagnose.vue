<template>
  <div class="diagnose-view">
    <el-tabs v-model="activeTab" class="diag-tabs">

      <!-- ══════════════════════════════════════
           Tab 1: 业务诊断
      ══════════════════════════════════════ -->
      <el-tab-pane label="业务诊断" name="business">
        <div class="tab-toolbar">
          <el-button type="primary" size="small" @click="openNewTypeDialog('business')">
            <el-icon><FolderAdd /></el-icon>&nbsp;新建诊断类型
          </el-button>
          <el-button size="small" @click="openScriptDialog(null, 'business')">
            <el-icon><Plus /></el-icon>&nbsp;新建脚本
          </el-button>
        </div>

        <div v-if="!businessCategories.length" class="empty-hint">
          暂无诊断类型，点击「新建诊断类型」开始
        </div>
        <div v-for="cat in businessCategories" :key="'biz-' + cat" class="category-section">
          <div class="category-header">
            <span class="cat-bullet">▣</span>{{ cat }}
          </div>
          <div class="script-grid">
            <div
              v-for="s in getScripts('business', cat)" :key="s.id"
              class="script-card" :class="{ 'script-card--disabled': !s.enabled }"
            >
              <div class="script-card-body">
                <div class="sc-name">{{ s.name }}</div>
                <div class="sc-desc">{{ s.description || '—' }}</div>
                <div class="sc-meta">
                  <el-tag size="small" type="info">{{ s.target_node_type }}</el-tag>
                  <span class="sc-timeout">{{ s.timeout }}s</span>
                </div>
              </div>
              <div class="script-card-footer">
                <el-button type="primary" size="small" :disabled="!s.enabled" @click="openRunDialog(s)">
                  <el-icon><VideoPlay /></el-icon> 运行
                </el-button>
                <el-button size="small" @click="openScriptDialog(s, 'business')">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" type="danger" @click="confirmDelete(s)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <div v-if="!getScripts('business', cat).length" class="script-card-empty">
              <el-button text type="primary" @click="openScriptDialog(null, 'business', cat)">
                <el-icon><Plus /></el-icon> 添加脚本
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ══════════════════════════════════════
           Tab 2: 硬件诊断
      ══════════════════════════════════════ -->
      <el-tab-pane label="硬件诊断" name="hardware">
        <div class="tab-toolbar">
          <el-button type="primary" size="small" @click="openNewTypeDialog('hardware')">
            <el-icon><FolderAdd /></el-icon>&nbsp;新建诊断类型
          </el-button>
          <el-button size="small" @click="openScriptDialog(null, 'hardware')">
            <el-icon><Plus /></el-icon>&nbsp;新建脚本
          </el-button>
        </div>

        <div v-if="!hardwareCategories.length" class="empty-hint">
          暂无诊断类型，点击「新建诊断类型」开始
        </div>
        <div v-for="cat in hardwareCategories" :key="'hw-' + cat" class="category-section">
          <div class="category-header">
            <span class="cat-bullet">▣</span>{{ cat }}
          </div>
          <div class="script-grid">
            <div
              v-for="s in getScripts('hardware', cat)" :key="s.id"
              class="script-card" :class="{ 'script-card--disabled': !s.enabled }"
            >
              <div class="script-card-body">
                <div class="sc-name">{{ s.name }}</div>
                <div class="sc-desc">{{ s.description || '—' }}</div>
                <div class="sc-meta">
                  <el-tag size="small" type="info">{{ s.target_node_type }}</el-tag>
                  <span class="sc-timeout">{{ s.timeout }}s</span>
                </div>
              </div>
              <div class="script-card-footer">
                <el-button type="primary" size="small" :disabled="!s.enabled" @click="openRunDialog(s)">
                  <el-icon><VideoPlay /></el-icon> 运行
                </el-button>
                <el-button size="small" @click="openScriptDialog(s, 'hardware')">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" type="danger" @click="confirmDelete(s)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <div v-if="!getScripts('hardware', cat).length" class="script-card-empty">
              <el-button text type="primary" @click="openScriptDialog(null, 'hardware', cat)">
                <el-icon><Plus /></el-icon> 添加脚本
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ══════════════════════════════════════
           Tab 3: 日志采集
      ══════════════════════════════════════ -->
      <el-tab-pane label="日志采集" name="collect">
        <el-card class="query-card">
          <el-row :gutter="24">
            <el-col :span="7">
              <div class="form-section-label">角色</div>
              <el-checkbox-group v-model="logQuery.roles" class="vert-checks">
                <el-checkbox value="master">Master</el-checkbox>
                <el-checkbox value="slave">Slave</el-checkbox>
                <el-checkbox value="subswath">Subswath</el-checkbox>
                <el-checkbox value="globalstorage">GlobalStorage</el-checkbox>
              </el-checkbox-group>
            </el-col>
            <el-col :span="7">
              <div class="form-section-label">日志目录</div>
              <el-checkbox-group v-model="logQuery.log_types" class="vert-checks">
                <el-checkbox value="business">业务日志</el-checkbox>
                <el-checkbox value="system">系统日志</el-checkbox>
                <el-checkbox value="kernel">内核日志</el-checkbox>
                <el-checkbox value="network">网卡日志</el-checkbox>
              </el-checkbox-group>
            </el-col>
            <el-col :span="10">
              <div class="form-section-label">时间范围</div>
              <el-date-picker
                v-model="logQuery.time_range"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                size="small"
                style="width:100%"
                value-format="YYYY-MM-DDTHH:mm:ss"
              />
              <el-button
                type="primary" style="margin-top:14px;width:100%"
                @click="queryLogs" :loading="querying"
              >
                <el-icon><Search /></el-icon>&nbsp;查询日志
              </el-button>
            </el-col>
          </el-row>
        </el-card>

        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>采集结果</span>
              <el-tag v-if="logResults.length" type="info" size="small">共 {{ logResults.length }} 条</el-tag>
            </div>
          </template>
          <el-empty
            v-if="!logResults.length && !querying"
            description="选择条件后点击「查询日志」"
            :image-size="80"
          />
          <el-table v-else :data="logResults" size="small" max-height="480" stripe>
            <el-table-column prop="timestamp" label="时间" width="160">
              <template #default="{ row }">{{ formatDate(row.timestamp) }}</template>
            </el-table-column>
            <el-table-column prop="node" label="节点" width="140" show-overflow-tooltip />
            <el-table-column prop="role" label="角色" width="110">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="log_type" label="日志类型" width="90" />
            <el-table-column prop="level" label="级别" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="levelColor(row.level)">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="内容" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- ══ 新建诊断类型 ══ -->
    <el-dialog v-model="newTypeDialog.visible" title="新建诊断类型" width="420px">
      <el-form label-width="90px">
        <el-form-item label="类型名称">
          <el-input
            v-model="newTypeDialog.name"
            placeholder="如: 性能诊断"
            @keyup.enter="confirmNewType"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newTypeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmNewType">创建</el-button>
      </template>
    </el-dialog>

    <!-- ══ 脚本新建/编辑 ══ -->
    <el-dialog
      v-model="scriptDialog.visible"
      :title="scriptDialog.editing ? '编辑脚本' : '新建脚本'"
      width="700px"
    >
      <el-form :model="scriptForm" label-width="90px">
        <el-form-item label="脚本名称" required>
          <el-input v-model="scriptForm.name" placeholder="简短描述该诊断项" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="14">
            <el-form-item label="所属分类">
              <el-autocomplete
                v-model="scriptForm.category"
                :fetch-suggestions="suggestCats"
                placeholder="选择或输入分类"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="节点类型">
              <el-select v-model="scriptForm.target_node_type" style="width:100%">
                <el-option label="所有节点" value="all" />
                <el-option label="Master" value="master" />
                <el-option label="Slave" value="slave" />
                <el-option label="Sensor" value="sensor" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="scriptForm.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="脚本内容" required>
          <el-input
            v-model="scriptForm.script_content"
            type="textarea" :rows="10"
            class="code-textarea"
            placeholder="输入 SSH 命令或 shell 脚本，将在目标节点上远程执行"
          />
          <div class="import-hint">
            <input
              ref="fileInputRef" type="file"
              style="display:none" accept=".sh,.py,.bash,.txt"
              @change="onFileImport"
            />
            <el-button text type="primary" size="small" @click="fileInputRef.click()">
              <el-icon><Upload /></el-icon> 导入本地脚本文件
            </el-button>
          </div>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="scriptForm.timeout" :min="5" :max="600" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="scriptForm.enabled" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="scriptDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveScript" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- ══ 运行脚本 ══ -->
    <el-dialog
      v-model="runDialog.visible"
      :title="`运行: ${runDialog.script?.name}`"
      width="780px"
      @closed="runResults = []"
    >
      <el-form :model="runForm" inline label-width="70px" class="run-form">
        <el-form-item label="目标节点">
          <el-select
            v-model="runForm.node_ids" multiple collapse-tags
            style="width:230px" placeholder="选择节点"
          >
            <el-option
              v-for="n in nodes" :key="n.id"
              :label="`${n.hostname} (${n.mgmt_ip || '无IP'})`" :value="n.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="runForm.ssh_user" placeholder="root" style="width:90px" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="runForm.ssh_password" type="password" show-password style="width:120px" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="runForm.ssh_port" :min="1" :max="65535" style="width:85px" />
        </el-form-item>
      </el-form>

      <pre class="script-preview">{{ runDialog.script?.script_content }}</pre>

      <el-button
        type="primary" :loading="running"
        @click="executeScript" :disabled="!runForm.node_ids.length"
        style="margin-bottom:14px"
      >
        <el-icon><VideoPlay /></el-icon>&nbsp;执行
      </el-button>

      <div v-for="res in runResults" :key="res.node_id" class="run-result">
        <div class="run-result-title">
          <span>{{ res.hostname }}</span>
          <el-tag size="small" :type="res.success ? 'success' : 'danger'">exit {{ res.exit_code }}</el-tag>
        </div>
        <pre class="run-stdout">{{ res.stdout || '(无输出)' }}</pre>
        <pre v-if="res.stderr" class="run-stderr">{{ res.stderr }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

// ─── 节点 ───
const nodes = ref([])

// ─── Tab ───
const activeTab = ref('business')

// ─── 脚本数据 ───
const scripts = ref([])

function getScripts(tab, cat) {
  return scripts.value.filter(s => s.script_tab === tab && s.category === cat)
}

// ─── 分类管理 ───
const DEFAULT_CATS = {
  business: ['初始化', '检测流程', 'LT流程', 'PDA流程'],
  hardware: ['存储诊断', '设备诊断', '网络诊断', '系统诊断'],
}

function loadUserCats(tab) {
  try { return JSON.parse(localStorage.getItem(`diag_cats_${tab}`) || '[]') } catch { return [] }
}
function saveUserCats(tab, list) {
  localStorage.setItem(`diag_cats_${tab}`, JSON.stringify(list))
}

const userBusinessCats = ref(loadUserCats('business'))
const userHardwareCats = ref(loadUserCats('hardware'))

const businessCategories = computed(() => {
  const fromScripts = scripts.value.filter(s => s.script_tab === 'business').map(s => s.category)
  return [...new Set([...DEFAULT_CATS.business, ...userBusinessCats.value, ...fromScripts])]
})
const hardwareCategories = computed(() => {
  const fromScripts = scripts.value.filter(s => s.script_tab === 'hardware').map(s => s.category)
  return [...new Set([...DEFAULT_CATS.hardware, ...userHardwareCats.value, ...fromScripts])]
})

// ─── 新建类型 ───
const newTypeDialog = ref({ visible: false, name: '', tab: 'business' })

function openNewTypeDialog(tab) {
  newTypeDialog.value = { visible: true, name: '', tab }
}
function confirmNewType() {
  const name = newTypeDialog.value.name.trim()
  if (!name) { ElMessage.warning('请输入类型名称'); return }
  const tab = newTypeDialog.value.tab
  if (tab === 'business') {
    if (!businessCategories.value.includes(name)) {
      userBusinessCats.value.push(name)
      saveUserCats('business', userBusinessCats.value)
    }
  } else {
    if (!hardwareCategories.value.includes(name)) {
      userHardwareCats.value.push(name)
      saveUserCats('hardware', userHardwareCats.value)
    }
  }
  ElMessage.success(`已创建「${name}」`)
  newTypeDialog.value.visible = false
}

// ─── 脚本 CRUD ───
const scriptDialog = ref({ visible: false, editing: null, tab: 'business' })
const saving = ref(false)
const fileInputRef = ref(null)

function defaultForm(tab = 'business', cat = '') {
  return {
    name: '', description: '',
    script_tab: tab,
    category: cat || (tab === 'business' ? DEFAULT_CATS.business[0] : DEFAULT_CATS.hardware[0]),
    script_content: '', target_node_type: 'all',
    timeout: 30, enabled: true
  }
}
const scriptForm = ref(defaultForm())

function openScriptDialog(script, tab, presetCat = '') {
  scriptDialog.value = { visible: true, editing: script, tab }
  scriptForm.value = script ? { ...script } : defaultForm(tab, presetCat)
}

function suggestCats(query, cb) {
  const cats = scriptDialog.value.tab === 'business' ? businessCategories.value : hardwareCategories.value
  cb(cats.filter(c => c.includes(query || '')).map(c => ({ value: c })))
}

function onFileImport(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = e => {
    scriptForm.value.script_content = e.target.result
    ElMessage.success(`已导入: ${file.name}`)
  }
  reader.readAsText(file, 'utf-8')
  event.target.value = ''
}

async function saveScript() {
  if (!scriptForm.value.name.trim() || !scriptForm.value.script_content.trim()) {
    ElMessage.warning('脚本名称和内容不能为空')
    return
  }
  saving.value = true
  try {
    if (scriptDialog.value.editing) {
      await axios.put(`/api/diagnose/scripts/${scriptDialog.value.editing.id}`, scriptForm.value)
      ElMessage.success('更新成功')
    } else {
      await axios.post('/api/diagnose/scripts', scriptForm.value)
      ElMessage.success('创建成功')
    }
    scriptDialog.value.visible = false
    loadScripts()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(script) {
  try {
    await ElMessageBox.confirm(`确定删除「${script.name}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
    await axios.delete(`/api/diagnose/scripts/${script.id}`)
    ElMessage.success('已删除')
    loadScripts()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

// ─── 运行脚本 ───
const runDialog = ref({ visible: false, script: null })
const runForm = ref({ node_ids: [], ssh_user: 'root', ssh_password: '', ssh_port: 22 })
const running = ref(false)
const runResults = ref([])

function openRunDialog(script) {
  runDialog.value = { visible: true, script }
  runResults.value = []
}

async function executeScript() {
  if (!runForm.value.node_ids.length) { ElMessage.warning('请选择节点'); return }
  running.value = true
  runResults.value = []
  try {
    const res = await axios.post(
      `/api/diagnose/scripts/${runDialog.value.script.id}/run`,
      runForm.value
    )
    runResults.value = res.data.results
    const ok = runResults.value.filter(r => r.success).length
    ElMessage[ok === runResults.value.length ? 'success' : 'warning'](
      `执行完成: ${ok}/${runResults.value.length} 个节点成功`
    )
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '执行失败')
  } finally {
    running.value = false
  }
}

// ─── 日志查询 ───
const logQuery = ref({ roles: ['master'], log_types: ['system'], time_range: null })
const querying = ref(false)
const logResults = ref([])

async function queryLogs() {
  if (!logQuery.value.roles.length || !logQuery.value.log_types.length) {
    ElMessage.warning('请至少选择一个角色和一个日志类型')
    return
  }
  querying.value = true
  logResults.value = []
  try {
    const payload = {
      roles: logQuery.value.roles,
      log_types: logQuery.value.log_types,
      start_time: logQuery.value.time_range?.[0] || null,
      end_time: logQuery.value.time_range?.[1] || null,
    }
    const res = await axios.post('/api/diagnose/query-logs', payload)
    logResults.value = res.data.entries
    ElMessage.success(`查询到 ${res.data.total} 条日志`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '查询失败')
  } finally {
    querying.value = false
  }
}

// ─── Helpers ───
const levelColor = l => ({ error: 'danger', warning: 'warning', info: 'success', debug: 'info' }[l] || 'info')
const formatDate = d => d ? new Date(d).toLocaleString() : ''

// ─── Init ───
async function loadScripts() {
  try {
    const res = await axios.get('/api/diagnose/scripts')
    scripts.value = res.data
  } catch { ElMessage.error('加载脚本失败') }
}

async function loadNodes() {
  try {
    const res = await axios.get('/api/nodes')
    nodes.value = res.data
  } catch { /* ignore */ }
}

onMounted(() => {
  loadScripts()
  loadNodes()
})
</script>

<style scoped>
/* ─── 整体 ─── */
.diagnose-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ─── Tabs 深色风格 ─── */
.diag-tabs { flex: 1; }

.diag-tabs :deep(.el-tabs__header) {
  background: #16213e;
  border-bottom: 2px solid #0f3460;
  margin-bottom: 0;
  padding: 0 4px;
}
.diag-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: transparent;
}
.diag-tabs :deep(.el-tabs__item) {
  color: #8899aa;
  height: 46px;
  line-height: 46px;
  padding: 0 26px;
  font-size: 14px;
  letter-spacing: 0.3px;
}
.diag-tabs :deep(.el-tabs__item:hover) { color: #e94560; }
.diag-tabs :deep(.el-tabs__item.is-active) {
  color: #e94560;
  font-weight: 600;
}
.diag-tabs :deep(.el-tabs__active-bar) { background-color: #e94560; }
.diag-tabs :deep(.el-tabs__content) {
  padding: 20px;
  background: transparent;
  overflow-y: auto;
}

/* ─── Toolbar ─── */
.tab-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
}

/* ─── 分类区块 ─── */
.empty-hint {
  color: #666;
  padding: 40px;
  text-align: center;
}
.category-section { margin-bottom: 30px; }
.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e94560;
}
.cat-bullet { color: #e94560; font-size: 15px; }

/* ─── 脚本卡片 ─── */
.script-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.script-card {
  background: #0f3460;
  border: 1px solid rgba(233, 69, 96, 0.2);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.script-card:hover {
  border-color: #e94560;
  box-shadow: 0 4px 14px rgba(233, 69, 96, 0.18);
}
.script-card--disabled { opacity: 0.5; }

.script-card-body { flex: 1; }
.sc-name { font-weight: 600; font-size: 14px; color: #fff; margin-bottom: 4px; }
.sc-desc { font-size: 12px; color: #8899aa; min-height: 34px; line-height: 1.6; }
.sc-meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.sc-timeout { font-size: 11px; color: #556; }

.script-card-footer { display: flex; gap: 6px; }

.script-card-empty {
  border: 1px dashed rgba(233, 69, 96, 0.3);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 110px;
  color: #556;
}

/* ─── 日志采集 ─── */
.query-card { margin-bottom: 16px; }
.form-section-label {
  color: #a0a0a0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.vert-checks { display: flex; flex-direction: column; gap: 10px; }
.vert-checks :deep(.el-checkbox__label) { color: #d0d0d0; }

.card-header { display: flex; justify-content: space-between; align-items: center; }

/* ─── 脚本编辑 ─── */
.code-textarea :deep(textarea) {
  font-family: 'Consolas', 'Monaco', monospace !important;
  font-size: 13px;
  background: #0d1117;
  color: #c9d1d9;
  border-color: #30363d;
}
.import-hint { margin-top: 6px; }

/* ─── 运行对话框 ─── */
.run-form { flex-wrap: wrap; gap: 4px; }
.script-preview {
  background: #0d1117;
  color: #8b949e;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 12px 14px;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 120px;
  overflow: auto;
  margin-bottom: 14px;
}
.run-result {
  margin-bottom: 14px;
  border: 1px solid #0f3460;
  border-radius: 6px;
  overflow: hidden;
}
.run-result-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #0f3460;
  color: #fff;
  font-weight: 500;
}
.run-stdout {
  background: #0d1117;
  color: #c9d1d9;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  margin: 0;
  padding: 10px 14px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow: auto;
}
.run-stderr {
  background: #1c0a0a;
  color: #ff7b7b;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  margin: 0;
  padding: 8px 14px;
  white-space: pre-wrap;
  max-height: 140px;
  overflow: auto;
}
</style>
