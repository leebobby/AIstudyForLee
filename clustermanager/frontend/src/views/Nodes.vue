<template>
  <div class="nodes-view">
    <!-- 节点列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点列表 (三平面网络)</span>
          <div class="header-actions">
            <el-select v-model="filterType" placeholder="节点类型" clearable style="width: 120px">
              <el-option label="Master" value="master" />
              <el-option label="Slave" value="slave" />
            </el-select>
            <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 100px">
              <el-option label="在线" value="online" />
              <el-option label="离线" value="offline" />
              <el-option label="告警" value="warning" />
            </el-select>
            <el-button type="primary" @click="loadNodes">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredNodes" stripe>
        <el-table-column prop="hostname" label="主机名" width="120" />
        <el-table-column prop="node_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.node_type === 'master' ? 'danger' : 'info'">
              {{ row.node_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="管理面 (GE)" width="180">
          <template #default="{ row }">
            <div class="plane-info">
              <span class="ip">{{ row.mgmt_ip || '-' }}</span>
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ row.status }}
              </el-tag>
            </div>
            <div class="bmc-info">BMC: {{ row.bmc_ip || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="控制面 (10GE)" width="150">
          <template #default="{ row }">
            <div class="plane-info">
              <span class="ip">{{ row.ctrl_ip || '-' }}</span>
              <el-tag :type="getStatusType(row.ctrl_status)" size="small">
                {{ row.ctrl_status || 'offline' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="数据面 (100GE)" width="180">
          <template #default="{ row }">
            <div class="plane-info">
              <span class="ip">{{ row.data_ip || '-' }}</span>
              <el-tag :type="getStatusType(row.data_status)" size="small">
                {{ row.data_status || 'offline' }}
              </el-tag>
            </div>
            <div class="protocol-info">{{ row.data_protocol || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="os_version" label="系统版本" width="120" />
        <el-table-column label="配置" width="150">
          <template #default="{ row }">
            <span>{{ row.cpu_cores }}核 / {{ row.memory_gb }}G / {{ row.disk_gb }}G</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showNodeDetail(row)">详情</el-button>
            <el-button size="small" @click="checkNetwork(row)">网络检查</el-button>
            <el-button size="small" type="warning" @click="showPowerDialog(row)">电源</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 节点详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="节点详情" width="600px">
      <el-descriptions :column="2" border v-if="selectedNode">
        <el-descriptions-item label="主机名">{{ selectedNode.hostname }}</el-descriptions-item>
        <el-descriptions-item label="节点类型">{{ selectedNode.node_type }}</el-descriptions-item>
        <el-descriptions-item label="整体状态">
          <el-tag :type="getStatusType(selectedNode.status)">{{ selectedNode.status }}</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="管理面IP">{{ selectedNode.mgmt_ip }}</el-descriptions-item>
        <el-descriptions-item label="BMC IP">{{ selectedNode.bmc_ip }}</el-descriptions-item>

        <el-descriptions-item label="控制面IP">{{ selectedNode.ctrl_ip }}</el-descriptions-item>
        <el-descriptions-item label="控制面状态">
          <el-tag :type="getStatusType(selectedNode.ctrl_status)">{{ selectedNode.ctrl_status }}</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="数据面IP">{{ selectedNode.data_ip }}</el-descriptions-item>
        <el-descriptions-item label="数据协议">{{ selectedNode.data_protocol }}</el-descriptions-item>

        <el-descriptions-item label="CPU">{{ selectedNode.cpu_cores }}核</el-descriptions-item>
        <el-descriptions-item label="内存">{{ selectedNode.memory_gb }}GB</el-descriptions-item>

        <el-descriptions-item label="系统版本">{{ selectedNode.os_version }}</el-descriptions-item>
        <el-descriptions-item label="最后更新">{{ formatDate(selectedNode.last_seen) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 电源控制对话框 -->
    <el-dialog v-model="powerDialogVisible" title="电源控制" width="400px">
      <div class="power-controls">
        <p>节点: {{ selectedNode?.hostname }}</p>
        <p>BMC: {{ selectedNode?.bmc_ip }}</p>
        <div class="power-buttons">
          <el-button type="success" @click="powerControl('on')">开机</el-button>
          <el-button type="danger" @click="powerControl('off')">关机</el-button>
          <el-button type="warning" @click="powerControl('reset')">重启</el-button>
          <el-button @click="powerControl('status')">查询状态</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 网络检查结果对话框 -->
    <el-dialog v-model="networkDialogVisible" title="三平面网络检查" width="500px">
      <div v-if="networkCheckResult" class="network-result">
        <div class="plane-check">
          <h4>管理面 (GE口)</h4>
          <p>IP: {{ networkCheckResult.planes.management.ip }}</p>
          <p>BMC IP: {{ networkCheckResult.planes.management.bmc_ip }}</p>
          <el-tag :type="networkCheckResult.planes.management.reachable ? 'success' : 'danger'">
            {{ networkCheckResult.planes.management.reachable ? '可达' : '不可达' }}
          </el-tag>
          <span v-if="networkCheckResult.planes.management.latency_ms">
            延迟: {{ networkCheckResult.planes.management.latency_ms }}ms
          </span>
        </div>

        <div class="plane-check">
          <h4>控制面 (10GE)</h4>
          <p>IP: {{ networkCheckResult.planes.control.ip }}</p>
          <el-tag :type="networkCheckResult.planes.control.reachable ? 'success' : 'danger'">
            {{ networkCheckResult.planes.control.reachable ? '可达' : '不可达' }}
          </el-tag>
          <span v-if="networkCheckResult.planes.control.latency_ms">
            延迟: {{ networkCheckResult.planes.control.latency_ms }}ms
          </span>
        </div>

        <div class="plane-check">
          <h4>数据面 (100GE)</h4>
          <p>IP: {{ networkCheckResult.planes.data.ip }}</p>
          <p>协议: {{ networkCheckResult.planes.data.protocol }}</p>
          <el-tag :type="networkCheckResult.planes.data.reachable ? 'success' : 'danger'">
            {{ networkCheckResult.planes.data.reachable ? '可达' : '不可达' }}
          </el-tag>
          <span v-if="networkCheckResult.planes.data.throughput_mbps">
            吞吐: {{ networkCheckResult.planes.data.throughput_mbps }}Mbps
          </span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const nodes = ref([])
const filterType = ref('')
const filterStatus = ref('')
const selectedNode = ref(null)

const detailDialogVisible = ref(false)
const powerDialogVisible = ref(false)
const networkDialogVisible = ref(false)
const networkCheckResult = ref(null)

const filteredNodes = computed(() => {
  let result = nodes.value
  if (filterType.value) {
    result = result.filter(n => n.node_type === filterType.value)
  }
  if (filterStatus.value) {
    result = result.filter(n => n.status === filterStatus.value)
  }
  return result
})

const getStatusType = (status) => {
  const types = {
    'online': 'success',
    'offline': 'danger',
    'warning': 'warning',
    'deploying': 'info',
    'error': 'danger'
  }
  return types[status] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const loadNodes = async () => {
  try {
    const response = await axios.get('/api/nodes')
    nodes.value = response.data
  } catch (e) {
    ElMessage.error('获取节点列表失败')
  }
}

const showNodeDetail = (node) => {
  selectedNode.value = node
  detailDialogVisible.value = true
}

const showPowerDialog = (node) => {
  selectedNode.value = node
  powerDialogVisible.value = true
}

const powerControl = async (action) => {
  if (!selectedNode.value) return
  try {
    const response = await axios.post(`/api/ipmi/nodes/${selectedNode.value.id}/power`, { action })
    ElMessage.success(`电源操作成功: ${response.data.power_status}`)
  } catch (e) {
    ElMessage.error('电源操作失败')
  }
}

const checkNetwork = async (node) => {
  selectedNode.value = node
  try {
    const response = await axios.post(`/api/network/check/${node.id}`)
    networkCheckResult.value = response.data
    networkDialogVisible.value = true
  } catch (e) {
    ElMessage.error('网络检查失败')
  }
}

onMounted(() => {
  loadNodes()
})
</script>

<style scoped>
.nodes-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.plane-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plane-info .ip {
  color: #fff;
}

.bmc-info, .protocol-info {
  color: #a0a0a0;
  font-size: 12px;
  margin-top: 4px;
}

.power-controls {
  text-align: center;
}

.power-controls p {
  color: #fff;
  margin: 10px 0;
}

.power-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.network-result {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.plane-check {
  padding: 15px;
  background: #0f3460;
  border-radius: 8px;
}

.plane-check h4 {
  color: #e94560;
  margin: 0 0 10px 0;
}

.plane-check p {
  color: #fff;
  margin: 5px 0;
}
</style>