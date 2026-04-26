<template>
  <div class="diagnose-view">
    <!-- 故障分析 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>故障分析</span>
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
        <el-table-column prop="fault_type" label="故障类型" width="150" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="severity" label="严重性" width="80">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="发现时间" width="150">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showFaultDetail(row)">详情</el-button>
            <el-button size="small" type="success" @click="resolveFault(row)">解决</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 日志查询 -->
    <el-card>
      <template #header>
        <span>日志查询</span>
      </template>

      <div class="log-filters">
        <el-select v-model="logFilter.node_id" placeholder="节点" clearable style="width: 150px">
          <el-option v-for="node in nodes" :key="node.id" :label="node.hostname" :value="node.id" />
        </el-select>
        <el-select v-model="logFilter.log_type" placeholder="日志类型" clearable style="width: 120px">
          <el-option label="系统日志" value="syslog" />
          <el-option label="内核日志" value="kernel" />
          <el-option label="DPDK日志" value="dpdk" />
          <el-option label="RDMA日志" value="rdma" />
          <el-option label="BMC日志" value="bmc" />
        </el-select>
        <el-select v-model="logFilter.level" placeholder="级别" clearable style="width: 80px">
          <el-option label="ERROR" value="error" />
          <el-option label="WARNING" value="warning" />
          <el-option label="INFO" value="info" />
        </el-select>
        <el-button type="primary" @click="loadLogs">查询</el-button>
      </div>

      <el-table :data="logs" stripe size="small" max-height="400">
        <el-table-column prop="log_type" label="类型" width="80" />
        <el-table-column prop="level" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getLogLevel(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column prop="collected_at" label="时间" width="150">
          <template #default="{ row }">
            {{ formatDate(row.collected_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 故障详情对话框 -->
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const faultPoints = ref([])
const logs = ref([])
const nodes = ref([])
const analyzing = ref(false)
const detailDialogVisible = ref(false)
const selectedFault = ref(null)

const logFilter = ref({
  node_id: '',
  log_type: '',
  level: ''
})

const getSeverityType = (severity) => {
  const types = { 'critical': 'danger', 'warning': 'warning', 'info': 'info' }
  return types[severity] || 'info'
}

const getStatusType = (status) => {
  const types = { 'active': 'danger', 'resolved': 'success' }
  return types[status] || 'info'
}

const getLogLevel = (level) => {
  const types = { 'error': 'danger', 'warning': 'warning', 'info': 'info' }
  return types[level] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const loadFaultPoints = async () => {
  try {
    const response = await axios.get('/api/diagnose/faults')
    faultPoints.value = response.data
  } catch (e) {
    ElMessage.error('获取故障点失败')
  }
}

const loadNodes = async () => {
  try {
    const response = await axios.get('/api/nodes')
    nodes.value = response.data
  } catch (e) {
    console.error('获取节点失败', e)
  }
}

const analyzeAll = async () => {
  analyzing.value = true
  try {
    const response = await axios.post('/api/diagnose/analyze')
    ElMessage.success(`分析完成，发现 ${response.data.faults_found} 个故障`)
    loadFaultPoints()
  } catch (e) {
    ElMessage.error('分析失败')
  } finally {
    analyzing.value = false
  }
}

const loadLogs = async () => {
  try {
    const params = {}
    if (logFilter.value.node_id) params.node_id = logFilter.value.node_id
    if (logFilter.value.log_type) params.log_type = logFilter.value.log_type
    if (logFilter.value.level) params.level = logFilter.value.level

    const response = await axios.get('/api/diagnose/logs', { params })
    logs.value = response.data
  } catch (e) {
    ElMessage.error('获取日志失败')
  }
}

const showFaultDetail = (fault) => {
  selectedFault.value = fault
  detailDialogVisible.value = true
}

const resolveFault = async (fault) => {
  try {
    await axios.post(`/api/diagnose/faults/${fault.id}/resolve`)
    ElMessage.success('故障已标记为解决')
    loadFaultPoints()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadFaultPoints()
  loadNodes()
  loadLogs()
})
</script>

<style scoped>
.diagnose-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.suggestions {
  margin-top: 20px;
  padding: 15px;
  background: #0f3460;
  border-radius: 8px;
}

.suggestions h4 {
  color: #e94560;
  margin: 0 0 10px 0;
}

.suggestions pre {
  color: #fff;
  white-space: pre-wrap;
  margin: 0;
}
</style>