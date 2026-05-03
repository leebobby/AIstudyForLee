<template>
  <div class="diagnose-view">
    <el-tabs v-model="activeTab" type="border-card" class="main-tabs">

      <!-- ══════════════════════════════════════════
           Tab 1: 故障分析
      ══════════════════════════════════════════ -->
      <el-tab-pane label="故障分析" name="faults">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>故障点列表</span>
              <el-button type="primary" @click="analyzeAll" :loading="analyzing">
                <el-icon><FirstAidKit /></el-icon>
                分析所有节点
              </el-button>
            </div>
          </template>
          <el-table :data="faultPoints" stripe>
            <el-table-column prop="plane" label="平面" width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ row.plane }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="fault_type" label="故障类型" width="160" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="severity" label="严重性" width="90">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="发现时间" width="160">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="showFaultDetail(row)">详情</el-button>
                <el-button size="small" type="success" @click="resolveFault(row)">解决</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header><span>日志查询</span></template>
          <div class="log-filters">
            <el-select v-model="logFilter.node_id" placeholder="节点" clearable style="width:150px">
              <el-option v-for="n in nodes" :key="n.id" :label="n.hostname" :value="n.id" />
            </el-select>
            <el-select v-model="logFilter.log_type" placeholder="日志类型" clearable style="width:130px">
              <el-option label="系统日志" value="syslog" />
              <el-option label="内核日志" value="kernel" />
              <el-option label="DPDK日志" value="dpdk" />
              <el-option label="RDMA日志" value="rdma" />
              <el-option label="BMC日志"  value="bmc"  />
            </el-select>
            <el-select v-model="logFilter.level" placeholder="级别" clearable style="width:90px">
              <el-option label="ERROR"   value="error"   />
              <el-option label="WARNING" value="warning" />
              <el-option label="INFO"    value="info"    />
            </el-select>
            <el-button type="primary" @click="loadLogs">查询</el-button>
          </div>
          <el-table :data="logs" stripe size="small" max-height="380">
            <el-table-column prop="log_type" label="类型" width="80" />
            <el-table-column prop="level" label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="getLogLevel(row.level)" size="small">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="消息" />
            <el-table-column prop="collected_at" label="时间" width="160">
              <template #default="{ row }">{{ formatDate(row.collected_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ══════════════════════════════════════════
           Tab 2: 日志采集
      ══════════════════════════════════════════ -->
      <el-tab-pane label="日志采集" name="collect">
        <el-row :gutter="16">
          <el-col :span="14">
            <!-- SSH 配置 -->
            <el-card class="collect-card">
              <template #header>
                <span><el-icon><Setting /></el-icon> SSH 连接配置</span>
              </template>
              <el-form :model="collect" label-width="80px" size="default">
                <el-form-item label="目标节点">
                  <el-select v-model="collect.node_ids" multiple placeholder="选择节点" style="width:100%">
                    <el-option
                      v-for="n in nodes" :key="n.id"
                      :label="`${n.hostname}  (${n.mgmt_ip || '无IP'})`"
                      :value="n.id"
                    />
                  </el-select>
                </el-form-item>
                <el-row :gutter="12">
                  <el-col :span="10">
                    <el-form-item label="用户名">
                      <el-input v-model="collect.ssh_user" placeholder="root" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="10">
                    <el-form-item label="密码">
                      <el-input v-model="collect.ssh_password" type="password" show-password />
                    </el-form-item>
                  </el-col>
                  <el-col :span="4">
                    <el-form-item label="端口">
                      <el-input-number v-model="collect.ssh_port" :min="1" :max="65535" style="width:70px" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item label="目标目录">
                  <el-input v-model="collect.target_dir" placeholder="例: D:\cluster_logs">
                    <template #prepend><el-icon><FolderOpened /></el-icon></template>
                  </el-input>
                  <div class="hint">日志将保存到 &lt;目标目录&gt;\&lt;节点名&gt;\&lt;时间戳&gt;\ 下</div>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 日志文件选择 -->
            <el-card class="collect-card" style="margin-top:14px">
              <template #header><span><el-icon><Document /></el-icon> 日志文件 / 命令</span></template>
              <div class="log-check-grid">
                <el-checkbox
                  v-for="item in predefinedLogs" :key="item.value"
                  v-model="item.checked"
                  class="log-check"
                >
                  <span class="log-label">{{ item.label }}</span>
                  <span class="log-path">{{ item.value }}</span>
                </el-checkbox>
              </div>
              <div class="custom-path-row" style="margin-top:12px">
                <el-input
                  v-model="customLogInput"
                  placeholder="自定义路径或命令，如 /var/log/app.log 或 dmesg -T"
                  style="flex:1"
                  @keyup.enter="addCustomLog"
                />
                <el-button @click="addCustomLog" style="margin-left:8px">添加</el-button>
              </div>
              <div v-if="customLogs.length" style="margin-top:8px">
                <el-tag
                  v-for="(p, i) in customLogs" :key="i"
                  closable @close="customLogs.splice(i,1)"
                  style="margin:3px"
                >{{ p }}</el-tag>
              </div>
            </el-card>

            <div style="margin-top:16px;text-align:right">
              <el-button
                type="primary" size="large" :loading="collecting"
                @click="startCollect"
                :disabled="!collect.node_ids.length || !selectedLogPaths.length"
              >
                <el-icon><Download /></el-icon>
                一键采集日志
              </el-button>
            </div>
          </el-col>

          <!-- 采集结果 -->
          <el-col :span="10">
            <el-card class="collect-card" style="min-height:460px">
              <template #header><span>采集结果</span></template>
              <el-empty v-if="!collectResults.length" description="尚未采集" :image-size="80" />
              <div v-for="res in collectResults" :key="res.node" class="collect-result">
                <div class="result-node-header">
                  <el-icon v-if="res.success" color="#67c23a"><CircleCheck /></el-icon>
                  <el-icon v-else color="#f56c6c"><CircleClose /></el-icon>
                  <span class="result-node-name">{{ res.node }}</span>
                  <el-tag size="small" :type="res.success ? 'success' : 'danger'">
                    {{ res.host }}
                  </el-tag>
                </div>
                <div v-if="res.success">
                  <div class="result-dir">
                    <el-icon><FolderOpened /></el-icon> {{ res.target_dir }}
                  </div>
                  <el-table :data="res.files" size="small" class="file-table">
                    <el-table-column prop="path" label="来源" min-width="120" show-overflow-tooltip />
                    <el-table-column label="状态" width="90">
                      <template #default="{ row }">
                        <el-tag
                          size="small"
                          :type="row.status === 'success' || row.status === 'success_sudo' ? 'success' : (row.status === 'not_found' ? 'info' : 'danger')"
                        >{{ row.status }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="size_kb" label="大小(KB)" width="80" />
                  </el-table>
                </div>
                <el-alert v-else :title="res.error" type="error" :closable="false" style="margin-top:6px" />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- ══════════════════════════════════════════
           Tab 3: 诊断脚本
      ══════════════════════════════════════════ -->
      <el-tab-pane label="诊断脚本" name="scripts">
        <!-- 工具栏 -->
        <div class="scripts-toolbar">
          <el-button type="primary" @click="openScriptDialog(null)">
            <el-icon><Plus /></el-icon> 新建脚本
          </el-button>
          <el-select v-model="scriptCategoryFilter" placeholder="所有分类" clearable style="width:160px">
            <el-option v-for="c in allCategories" :key="c" :label="c" :value="c" />
          </el-select>
          <el-input v-model="scriptSearch" placeholder="搜索脚本名..." clearable style="width:200px">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <!-- 按分类展示 -->
        <div v-if="filteredScripts.length === 0" class="no-scripts">
          <el-empty description="暂无诊断脚本" />
        </div>
        <div v-for="category in visibleCategories" :key="category" class="category-section">
          <div class="category-title">
            <el-icon><Collection /></el-icon>
            {{ category }}
          </div>
          <div class="script-grid">
            <div
              v-for="script in getScriptsByCategory(category)"
              :key="script.id"
              class="script-card"
              :class="{ disabled: !script.enabled }"
            >
              <div class="script-card-body">
                <div class="script-name">{{ script.name }}</div>
                <div class="script-desc">{{ script.description || '—' }}</div>
                <div class="script-meta">
                  <el-tag size="small" type="info">{{ script.target_node_type }}</el-tag>
                  <span class="script-timeout">{{ script.timeout }}s</span>
                </div>
              </div>
              <div class="script-card-actions">
                <el-button
                  type="primary" size="small" :disabled="!script.enabled"
                  @click="openRunDialog(script)"
                >
                  <el-icon><VideoPlay /></el-icon> 运行
                </el-button>
                <el-button size="small" @click="openScriptDialog(script)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" type="danger" @click="confirmDeleteScript(script)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ══════════════════════════════════════════
         故障详情对话框
    ══════════════════════════════════════════ -->
    <el-dialog v-model="detailDialogVisible" title="故障详情" width="600px">
      <el-descriptions :column="2" border v-if="selectedFault">
        <el-descriptions-item label="故障类型">{{ selectedFault.fault_type }}</el-descriptions-item>
        <el-descriptions-item label="平面">{{ selectedFault.plane }}</el-descriptions-item>
        <el-descriptions-item label="严重性">
          <el-tag :type="getSeverityType(selectedFault.severity)">{{ selectedFault.severity }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述">{{ selectedFault.description }}</el-descriptions-item>
      </el-descriptions>
      <div class="suggestions" v-if="selectedFault?.suggestions">
        <h4>建议操作</h4>
        <pre>{{ selectedFault.suggestions }}</pre>
      </div>
    </el-dialog>

    <!-- ══════════════════════════════════════════
         脚本新建/编辑对话框
    ══════════════════════════════════════════ -->
    <el-dialog
      v-model="scriptDialogVisible"
      :title="editingScript ? '编辑诊断脚本' : '新建诊断脚本'"
      width="660px"
    >
      <el-form :model="scriptForm" label-width="90px">
        <el-form-item label="脚本名称" required>
          <el-input v-model="scriptForm.name" placeholder="简短描述该诊断项" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="14">
            <el-form-item label="分类">
              <el-autocomplete
                v-model="scriptForm.category"
                :fetch-suggestions="suggestCategories"
                placeholder="如: 网络诊断"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="节点类型">
              <el-select v-model="scriptForm.target_node_type" style="width:100%">
                <el-option label="所有节点"   value="all"    />
                <el-option label="Master节点" value="master" />
                <el-option label="Slave节点"  value="slave"  />
                <el-option label="Sensor节点" value="sensor" />
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
            type="textarea" :rows="8"
            class="code-input"
            placeholder="输入 SSH 命令或多行 shell 脚本，将在目标节点上执行"
          />
        </el-form-item>
        <el-form-item label="超时(秒)">
          <el-input-number v-model="scriptForm.timeout" :min="5" :max="600" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="scriptForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scriptDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveScript" :loading="savingScript">保存</el-button>
      </template>
    </el-dialog>

    <!-- ══════════════════════════════════════════
         运行脚本对话框
    ══════════════════════════════════════════ -->
    <el-dialog
      v-model="runDialogVisible"
      :title="`运行脚本: ${runningScript?.name}`"
      width="780px"
      @closed="runResults = []"
    >
      <el-form :model="runForm" inline label-width="70px" class="run-form">
        <el-form-item label="目标节点">
          <el-select
            v-model="runForm.node_ids" multiple collapse-tags
            placeholder="选择节点" style="width:260px"
          >
            <el-option
              v-for="n in nodesForRun" :key="n.id"
              :label="`${n.hostname} (${n.mgmt_ip || '无IP'})`"
              :value="n.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="runForm.ssh_user" placeholder="root" style="width:100px" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="runForm.ssh_password" type="password" show-password style="width:120px" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="runForm.ssh_port" :min="1" :max="65535" style="width:80px" />
        </el-form-item>
      </el-form>

      <div class="run-script-preview">
        <pre>{{ runningScript?.script_content }}</pre>
      </div>

      <el-button
        type="primary" :loading="running" @click="executeScript"
        :disabled="!runForm.node_ids.length"
        style="margin-bottom:14px"
      >
        <el-icon><VideoPlay /></el-icon> 执行
      </el-button>

      <!-- 执行结果 -->
      <div v-for="res in runResults" :key="res.node_id" class="run-result-block">
        <div class="run-result-header">
          <span class="run-result-host">{{ res.hostname }}</span>
          <el-tag :type="res.success ? 'success' : 'danger'" size="small">
            exit {{ res.exit_code }}
          </el-tag>
        </div>
        <pre class="run-stdout" v-if="res.stdout">{{ res.stdout }}</pre>
        <pre class="run-stderr" v-if="res.stderr">{{ res.stderr }}</pre>
        <div v-if="!res.stdout && !res.stderr" class="run-empty">(无输出)</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

// ─── 全局状态 ───
const activeTab = ref('faults')
const nodes = ref([])

// ─── Tab1: 故障分析 ───
const faultPoints = ref([])
const logs = ref([])
const analyzing = ref(false)
const detailDialogVisible = ref(false)
const selectedFault = ref(null)
const logFilter = ref({ node_id: '', log_type: '', level: '' })

// ─── Tab2: 日志采集 ───
const collect = ref({
  node_ids: [],
  ssh_user: 'root',
  ssh_password: '',
  ssh_port: 22,
  target_dir: 'D:\\cluster_logs'
})
const predefinedLogs = ref([
  { label: '系统日志',     value: '/var/log/messages',      checked: true  },
  { label: '安全日志',     value: '/var/log/secure',         checked: true  },
  { label: '内核日志',     value: '/var/log/kern.log',       checked: false },
  { label: 'dmesg 输出',  value: 'dmesg',                    checked: true  },
  { label: '审计日志',     value: '/var/log/audit/audit.log',checked: false },
  { label: 'journalctl',  value: 'journalctl --no-pager -n 2000', checked: false },
])
const customLogInput = ref('')
const customLogs = ref([])
const collecting = ref(false)
const collectResults = ref([])

const selectedLogPaths = computed(() => [
  ...predefinedLogs.value.filter(l => l.checked).map(l => l.value),
  ...customLogs.value
])

// ─── Tab3: 诊断脚本 ───
const scripts = ref([])
const scriptCategoryFilter = ref('')
const scriptSearch = ref('')
const scriptDialogVisible = ref(false)
const editingScript = ref(null)
const savingScript = ref(false)
const scriptForm = ref(defaultScriptForm())

const runDialogVisible = ref(false)
const runningScript = ref(null)
const running = ref(false)
const runResults = ref([])
const runForm = ref({ node_ids: [], ssh_user: 'root', ssh_password: '', ssh_port: 22 })

// ─── Computed ───
const allCategories = computed(() => [...new Set(scripts.value.map(s => s.category))])

const filteredScripts = computed(() => {
  return scripts.value.filter(s => {
    const matchCat = !scriptCategoryFilter.value || s.category === scriptCategoryFilter.value
    const matchSearch = !scriptSearch.value ||
      s.name.toLowerCase().includes(scriptSearch.value.toLowerCase()) ||
      (s.description || '').toLowerCase().includes(scriptSearch.value.toLowerCase())
    return matchCat && matchSearch
  })
})

const visibleCategories = computed(() => {
  const cats = filteredScripts.value.map(s => s.category)
  return [...new Set(cats)]
})

const nodesForRun = computed(() => {
  if (!runningScript.value || runningScript.value.target_node_type === 'all') return nodes.value
  return nodes.value.filter(n => n.node_type === runningScript.value.target_node_type)
})

// ─── Helpers ───
function defaultScriptForm() {
  return {
    name: '', description: '', category: '通用诊断',
    script_content: '', target_node_type: 'all',
    timeout: 30, enabled: true
  }
}

const getSeverityType = s => ({ critical: 'danger', warning: 'warning', info: 'info' }[s] || 'info')
const getStatusType   = s => ({ active: 'danger', resolved: 'success' }[s] || 'info')
const getLogLevel     = l => ({ error: 'danger', warning: 'warning', info: 'info' }[l] || 'info')
const formatDate      = d => d ? new Date(d).toLocaleString() : ''

function getScriptsByCategory(cat) {
  return filteredScripts.value.filter(s => s.category === cat)
}

function suggestCategories(query, cb) {
  const cats = allCategories.value.filter(c => c.toLowerCase().includes((query || '').toLowerCase()))
  cb(cats.map(c => ({ value: c })))
}

function addCustomLog() {
  const v = customLogInput.value.trim()
  if (v && !customLogs.value.includes(v)) customLogs.value.push(v)
  customLogInput.value = ''
}

// ─── Tab1 Actions ───
async function loadFaultPoints() {
  try {
    const res = await axios.get('/api/diagnose/faults')
    faultPoints.value = res.data
  } catch { ElMessage.error('获取故障点失败') }
}

async function loadNodes() {
  try {
    const res = await axios.get('/api/nodes')
    nodes.value = res.data
  } catch { console.error('获取节点失败') }
}

async function analyzeAll() {
  analyzing.value = true
  try {
    const res = await axios.post('/api/diagnose/analyze')
    ElMessage.success(`分析完成，发现 ${res.data.faults_found} 个故障`)
    loadFaultPoints()
  } catch { ElMessage.error('分析失败') }
  finally { analyzing.value = false }
}

async function loadLogs() {
  try {
    const params = {}
    if (logFilter.value.node_id) params.node_id = logFilter.value.node_id
    if (logFilter.value.log_type) params.log_type = logFilter.value.log_type
    if (logFilter.value.level) params.level = logFilter.value.level
    const res = await axios.get('/api/diagnose/logs', { params })
    logs.value = res.data
  } catch { ElMessage.error('获取日志失败') }
}

function showFaultDetail(fault) {
  selectedFault.value = fault
  detailDialogVisible.value = true
}

async function resolveFault(fault) {
  try {
    await axios.post(`/api/diagnose/faults/${fault.id}/resolve`)
    ElMessage.success('故障已标记为解决')
    loadFaultPoints()
  } catch { ElMessage.error('操作失败') }
}

// ─── Tab2 Actions ───
async function startCollect() {
  if (!collect.value.target_dir.trim()) {
    ElMessage.warning('请填写目标目录')
    return
  }
  collecting.value = true
  collectResults.value = []
  try {
    const res = await axios.post('/api/diagnose/log-collect', {
      ...collect.value,
      log_paths: selectedLogPaths.value
    })
    collectResults.value = res.data.results
    ElMessage.success(res.data.message)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '采集失败')
  } finally {
    collecting.value = false
  }
}

// ─── Tab3 Actions ───
async function loadScripts() {
  try {
    const res = await axios.get('/api/diagnose/scripts')
    scripts.value = res.data
  } catch { ElMessage.error('获取脚本列表失败') }
}

function openScriptDialog(script) {
  editingScript.value = script
  scriptForm.value = script
    ? { ...script }
    : defaultScriptForm()
  scriptDialogVisible.value = true
}

async function saveScript() {
  if (!scriptForm.value.name.trim() || !scriptForm.value.script_content.trim()) {
    ElMessage.warning('脚本名称和内容不能为空')
    return
  }
  savingScript.value = true
  try {
    if (editingScript.value) {
      await axios.put(`/api/diagnose/scripts/${editingScript.value.id}`, scriptForm.value)
      ElMessage.success('更新成功')
    } else {
      await axios.post('/api/diagnose/scripts', scriptForm.value)
      ElMessage.success('创建成功')
    }
    scriptDialogVisible.value = false
    loadScripts()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingScript.value = false
  }
}

async function confirmDeleteScript(script) {
  try {
    await ElMessageBox.confirm(
      `确定删除脚本「${script.name}」？`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await axios.delete(`/api/diagnose/scripts/${script.id}`)
    ElMessage.success('已删除')
    loadScripts()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

function openRunDialog(script) {
  runningScript.value = script
  runResults.value = []
  // 预填 SSH 配置（复用采集配置）
  runForm.value = {
    node_ids: [],
    ssh_user: collect.value.ssh_user,
    ssh_password: collect.value.ssh_password,
    ssh_port: collect.value.ssh_port
  }
  runDialogVisible.value = true
}

async function executeScript() {
  if (!runForm.value.node_ids.length) {
    ElMessage.warning('请至少选择一个节点')
    return
  }
  running.value = true
  runResults.value = []
  try {
    const res = await axios.post(
      `/api/diagnose/scripts/${runningScript.value.id}/run`,
      runForm.value
    )
    runResults.value = res.data.results
    const ok = runResults.value.filter(r => r.success).length
    ElMessage.success(`执行完成: ${ok}/${runResults.value.length} 个节点成功`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '执行失败')
  } finally {
    running.value = false
  }
}

// ─── Init ───
onMounted(() => {
  loadFaultPoints()
  loadNodes()
  loadLogs()
  loadScripts()
})
</script>

<style scoped>
.diagnose-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.main-tabs {
  flex: 1;
}

/* ── Fault ── */
.card-header { display: flex; justify-content: space-between; align-items: center; }
.log-filters { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }

.suggestions { margin-top: 18px; padding: 14px; background: #0f3460; border-radius: 8px; }
.suggestions h4 { color: #e94560; margin: 0 0 8px; }
.suggestions pre { color: #fff; white-space: pre-wrap; margin: 0; }

/* ── Collect ── */
.collect-card :deep(.el-card__header) { padding: 10px 16px; font-size: 13px; }

.log-check-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.log-check { display: flex; flex-direction: column; }
.log-label { font-weight: 500; font-size: 13px; }
.log-path { font-size: 11px; color: #909399; margin-top: 1px; font-family: monospace; }

.custom-path-row { display: flex; align-items: center; }

.hint { font-size: 11px; color: #909399; margin-top: 4px; }

.collect-result {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.result-node-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.result-node-name { font-weight: 600; font-size: 14px; flex: 1; }
.result-dir { font-size: 11px; color: #606266; margin-bottom: 6px; display: flex; align-items: center; gap: 4px; }
.file-table { font-size: 12px; }

/* ── Scripts ── */
.scripts-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.no-scripts { padding: 40px; }

.category-section { margin-bottom: 24px; }
.category-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid #e94560;
}

.script-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.script-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: box-shadow 0.2s, border-color 0.2s;
  background: #fff;
}
.script-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: #409eff;
}
.script-card.disabled { opacity: 0.55; }

.script-card-body { flex: 1; }
.script-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #1d2129; }
.script-desc { font-size: 12px; color: #606266; min-height: 32px; line-height: 1.5; }
.script-meta { display: flex; align-items: center; gap: 8px; margin-top: 6px; }
.script-timeout { font-size: 11px; color: #909399; }

.script-card-actions { display: flex; gap: 6px; }

/* ── Run Dialog ── */
.run-form { flex-wrap: wrap; gap: 4px; }
.run-script-preview {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 12px 14px;
  margin-bottom: 14px;
  max-height: 120px;
  overflow: auto;
}
.run-script-preview pre {
  color: #d4d4d4;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  margin: 0;
  white-space: pre-wrap;
}

.run-result-block {
  margin-bottom: 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}
.run-result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 500;
}
.run-result-host { flex: 1; }
.run-stdout {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  margin: 0;
  padding: 10px 14px;
  white-space: pre-wrap;
  max-height: 280px;
  overflow: auto;
}
.run-stderr {
  background: #2d1b1b;
  color: #ff8080;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  margin: 0;
  padding: 8px 14px;
  white-space: pre-wrap;
  max-height: 140px;
  overflow: auto;
}
.run-empty { padding: 10px 14px; color: #909399; font-size: 12px; font-style: italic; }
.code-input :deep(textarea) { font-family: 'Consolas', monospace !important; font-size: 13px; }
</style>
