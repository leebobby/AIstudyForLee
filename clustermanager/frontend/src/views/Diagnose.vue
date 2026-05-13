<template>
  <div class="diagnose-view">
    <!-- ══ 脚本配置全局操作栏 ══ -->
    <div class="scripts-mgmt-bar">
      <span class="bar-label">脚本配置</span>
      <div class="bar-actions">
        <el-tooltip content="将当前所有脚本导出为 JSON 文件" placement="bottom">
          <el-button size="small" @click="exportScripts">
            <el-icon><Download /></el-icon>&nbsp;导出配置
          </el-button>
        </el-tooltip>
        <el-tooltip content="从 JSON 文件导入脚本（按名称合并）" placement="bottom">
          <el-button size="small" @click="importFileRef.click()">
            <el-icon><Upload /></el-icon>&nbsp;导入配置
          </el-button>
        </el-tooltip>
        <input ref="importFileRef" type="file" accept=".json" style="display:none" @change="onImportFile" />
        <el-tooltip :content="bundleInfo.exists
          ? `发布包: ${bundleInfo.count} 个脚本，更新于 ${formatDate(bundleInfo.mtime)}`
          : '尚未生成发布配置'" placement="bottom">
          <el-button size="small" type="primary" @click="saveBundle" :loading="savingBundle">
            <el-icon><Box /></el-icon>&nbsp;保存为发布配置
          </el-button>
        </el-tooltip>
        <el-tag v-if="bundleInfo.exists" size="small" type="success" class="bundle-tag">
          已有发布包 ({{ bundleInfo.count }} 脚本)
        </el-tag>
      </div>
    </div>

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
      <el-form :model="runForm" label-width="80px" class="run-form-block">
        <!-- 模式切换 -->
        <el-form-item label="目标方式">
          <el-radio-group v-model="runForm.target_mode" size="small">
            <el-radio-button value="ips">手动 IP</el-radio-button>
            <el-radio-button value="nodes">节点选择</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 目标值 -->
        <el-form-item :label="runForm.target_mode === 'ips' ? '目标 IP' : '目标节点'">
          <el-input
            v-if="runForm.target_mode === 'ips'"
            v-model="runForm.manual_ips"
            style="width:360px"
            placeholder="172.16.3.100（多个用英文逗号分隔）"
          />
          <el-select
            v-else
            v-model="runForm.node_ids" multiple collapse-tags
            style="width:360px" placeholder="选择节点（含离线）"
          >
            <el-option
              v-for="n in nodes" :key="n.id"
              :label="`${n.hostname} (${n.ctrl_ip || n.mgmt_ip || '无IP'}) [${n.status}]`"
              :value="n.id"
            />
          </el-select>
          <div v-if="runForm.target_mode === 'ips'" class="run-ip-hint">
            SSH 将直接连到此 IP, 不依赖节点管理
          </div>
        </el-form-item>

        <!-- 凭据 + 端口 -->
        <el-form-item label="SSH 凭据">
          <el-input v-model="runForm.ssh_user" placeholder="用户名" style="width:120px" />
          <el-input v-model="runForm.ssh_password" type="password" show-password
                    placeholder="密码" style="width:160px;margin-left:8px" />
          <el-input v-model.number="runForm.ssh_port" type="number" min="1" max="65535"
                    placeholder="端口" style="width:90px;margin-left:8px" />
        </el-form-item>
      </el-form>

      <pre class="script-preview">{{ runDialog.script?.script_content }}</pre>

      <div class="run-action-bar">
        <el-button
          type="primary" :loading="running"
          @click="executeScript"
          :disabled="runForm.target_mode === 'nodes' ? !runForm.node_ids.length : !runForm.manual_ips.trim()"
        >
          <el-icon><VideoPlay /></el-icon>&nbsp;执行
        </el-button>
        <el-tag v-if="credsLoaded" size="small" type="success">
          已保存凭据 ({{ runForm.ssh_user }})
        </el-tag>
        <span v-if="runProgress.total" class="run-progress">
          已完成 {{ runResults.length }} / {{ runProgress.total }}
        </span>
      </div>

      <div v-for="res in runResults" :key="res.node_id" class="run-result">
        <div class="run-result-title">
          <span>
            {{ res.hostname }}
            <span class="run-host">{{ res.host || '—' }}</span>
          </span>
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

// ─── 运行脚本 (流式 SSE + 凭据持久化) ───
const PWD_MASK = '********'
const runDialog = ref({ visible: false, script: null })
const runForm = ref({
  target_mode: 'ips',           // 默认手动 IP 模式（无在线节点时也能用）
  node_ids: [],
  manual_ips: '172.16.3.100',   // 默认控制面 IP
  ssh_user: 'root',
  ssh_password: '',
  ssh_port: 22,
})
const running = ref(false)
const runResults = ref([])
const runProgress = ref({ total: 0 })
const credsLoaded = ref(false)

// 只有 status === 'online' 的节点可作为脚本执行目标 (SSH 走 ctrl_ip)
const onlineNodes = computed(() => nodes.value.filter(n => n.status === 'online'))

async function loadSavedCreds() {
  try {
    const res = await axios.get('/api/diagnose/ssh-creds')
    if (res.data.has_saved) {
      runForm.value.ssh_user = res.data.ssh_user || 'root'
      runForm.value.ssh_port = res.data.ssh_port || 22
      runForm.value.ssh_password = PWD_MASK    // 占位符, 提交时后端会用已保存的真密码
      credsLoaded.value = true
    } else {
      credsLoaded.value = false
    }
  } catch {
    credsLoaded.value = false
  }
}

function openRunDialog(script) {
  runDialog.value = { visible: true, script }
  runResults.value = []
  runProgress.value = { total: 0 }
  loadSavedCreds()
  loadNodes()        // 拉最新节点状态, 仅在线节点可选
}

async function executeScript() {
  // 构造请求体：按模式取 node_ids 或 target_ips
  const payload = {
    node_ids: runForm.value.target_mode === 'nodes' ? runForm.value.node_ids : [],
    target_ips: runForm.value.target_mode === 'ips'
      ? runForm.value.manual_ips.split(',').map(s => s.trim()).filter(Boolean)
      : [],
    ssh_user: runForm.value.ssh_user,
    ssh_password: runForm.value.ssh_password,
    ssh_port: Number(runForm.value.ssh_port) || 22,
  }
  if (!payload.node_ids.length && !payload.target_ips.length) {
    ElMessage.warning('请选择节点或填写目标 IP')
    return
  }
  running.value = true
  runResults.value = []
  runProgress.value = { total: 0 }

  try {
    const resp = await fetch(`/api/diagnose/scripts/${runDialog.value.script.id}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`
      try { detail = (await resp.json()).detail || detail } catch {}
      throw new Error(detail)
    }

    // 解析 SSE 数据流: 每事件 `data: {...}\n\n`
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    let endEvent = null

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const chunk = buf.slice(0, idx).trim()
        buf = buf.slice(idx + 2)
        if (!chunk.startsWith('data:')) continue
        const json = chunk.replace(/^data:\s*/, '')
        if (!json) continue
        let evt
        try { evt = JSON.parse(json) } catch { continue }

        if (evt.type === 'start') {
          runProgress.value = { total: evt.total }
        } else if (evt.type === 'result') {
          runResults.value.push(evt)        // 增量追加, 实时显示
        } else if (evt.type === 'end') {
          endEvent = evt
        }
      }
    }

    const total = endEvent?.total ?? runResults.value.length
    const ok = endEvent?.success ?? runResults.value.filter(r => r.success).length
    ElMessage[ok === total ? 'success' : 'warning'](`执行完成: ${ok}/${total} 个节点成功`)

    // 凭据持久化: 仅当用户实际输入了新密码时, 后端会自动保存
    // 这里再拉一次状态以更新标签
    if (runForm.value.ssh_password && runForm.value.ssh_password !== PWD_MASK) {
      loadSavedCreds()
    }
  } catch (e) {
    ElMessage.error(e.message || '执行失败')
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

// ─── 发布包管理 ───
const importFileRef = ref(null)
const savingBundle = ref(false)
const bundleInfo = ref({ exists: false, count: 0, mtime: null })

async function loadBundleInfo() {
  try {
    const res = await axios.get('/api/diagnose/scripts/bundle-info')
    bundleInfo.value = res.data
  } catch { /* ignore */ }
}

function exportScripts() {
  window.open('/api/diagnose/scripts/export', '_blank')
}

async function onImportFile(event) {
  const file = event.target.files[0]
  if (!file) return
  event.target.value = ''
  let data
  try {
    data = JSON.parse(await file.text())
  } catch {
    ElMessage.error('文件格式错误，请选择合法的 JSON 文件')
    return
  }
  const scripts = data.scripts || (Array.isArray(data) ? data : null)
  if (!scripts) { ElMessage.error('JSON 中未找到 scripts 字段'); return }

  try {
    await ElMessageBox.confirm(
      `将导入 ${scripts.length} 个脚本（同名脚本将被覆盖），继续？`,
      '导入确认', { type: 'warning', confirmButtonText: '导入', cancelButtonText: '取消' }
    )
    const res = await axios.post('/api/diagnose/scripts/import', { scripts, mode: 'merge' })
    ElMessage.success(`导入完成：新建 ${res.data.created}，更新 ${res.data.updated}`)
    loadScripts()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '导入失败')
  }
}

async function saveBundle() {
  try {
    await ElMessageBox.confirm(
      '将当前数据库中的全部脚本保存为发布配置（scripts_bundle.json）。\n新环境首次启动时将自动加载此配置。',
      '保存为发布配置', { type: 'info', confirmButtonText: '保存', cancelButtonText: '取消' }
    )
    savingBundle.value = true
    const res = await axios.post('/api/diagnose/scripts/save-bundle')
    ElMessage.success(res.data.message)
    loadBundleInfo()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingBundle.value = false
  }
}

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

// 打开运行对话框前刷新一次节点状态, 避免列表里出现已离线的旧节点

onMounted(() => {
  loadScripts()
  loadNodes()
  loadBundleInfo()
})
</script>

<style scoped>
/* ─── 整体 ─── */
.diagnose-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ─── 发布配置操作栏 ─── */
.scripts-mgmt-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #0d1b2e;
  border-bottom: 1px solid #0f3460;
  flex-shrink: 0;
}
.bar-label {
  font-size: 12px;
  font-weight: 600;
  color: #5577aa;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bundle-tag {
  font-size: 11px;
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
.run-form-block { width: 100%; }
.run-form-block :deep(.el-form-item) { margin-bottom: 12px; }
.run-ip-hint {
  font-size: 11px;
  color: #8b949e;
  margin-top: 4px;
}
.run-form-block :deep(.el-radio-button__inner) {
  background: #0f3460;
  border-color: #1e4080;
  color: #8b949e;
}
.run-form-block :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #e94560;
  border-color: #e94560;
  color: #fff;
}

.run-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.run-progress {
  color: #8b949e;
  font-size: 12px;
}
.run-host {
  color: #8b949e;
  font-size: 11px;
  font-family: Consolas, monospace;
  margin-left: 8px;
}
.run-empty-hint {
  color: #e0a64b;
  font-size: 11px;
  margin-left: 8px;
}
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
