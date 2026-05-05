<template>
  <div class="nodes-view">
    <!-- 节点列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点列表 (三平面网络)</span>
          <div class="header-actions">
            <el-select v-model="filterType" placeholder="节点类型" clearable style="width: 130px">
              <el-option label="Master" value="master" />
              <el-option label="Slave" value="slave" />
              <el-option label="SubSwath" value="subswath" />
              <el-option label="GStorage" value="gstorage" />
              <el-option label="Sensor" value="sensor" />
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
            <el-button type="success" @click="openAdd">
              <el-icon><Plus /></el-icon>
              新增节点
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredNodes" stripe>
        <el-table-column prop="hostname" label="主机名" width="130" />
        <el-table-column label="类型 / 角色" width="110">
          <template #default="{ row }">
            <el-tag :type="nodeTypeTag(row.node_type)" size="small">{{ row.node_type }}</el-tag>
            <div v-if="row.role" class="role-text">{{ row.role }}</div>
          </template>
        </el-table-column>
        <el-table-column label="管理面 (GE)" width="180">
          <template #default="{ row }">
            <div class="plane-info">
              <span class="ip">{{ row.mgmt_ip || '-' }}</span>
              <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
            </div>
            <div class="sub-info">BMC: {{ row.bmc_ip || '-' }}</div>
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
            <div class="sub-info">{{ row.data_protocol || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="os_version" label="系统版本" width="130" />
        <el-table-column label="配置" width="150">
          <template #default="{ row }">
            <span>{{ row.cpu_cores || '-' }}核 / {{ row.memory_gb || '-' }}G / {{ row.disk_gb || '-' }}G</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" @click="checkNetwork(row)">网络检查</el-button>
            <el-button size="small" type="warning" @click="showPowerDialog(row)">电源</el-button>
            <el-button size="small" type="danger" @click="deleteNode(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑节点对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="editMode === 'add' ? '新增节点' : '编辑节点'"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="110px" size="default">

        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="主机名" prop="hostname">
              <el-input v-model="editForm.hostname" placeholder="如 master-01" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="节点类型" prop="node_type">
              <el-select v-model="editForm.node_type" style="width:100%">
                <el-option label="Master" value="master" />
                <el-option label="Slave" value="slave" />
                <el-option label="SubSwath" value="subswath" />
                <el-option label="GStorage" value="gstorage" />
                <el-option label="Sensor" value="sensor" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="角色">
              <el-input v-model="editForm.role" placeholder="可选，如 compute" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">管理面 (GE)</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="管理面 IP">
              <el-input v-model="editForm.mgmt_ip" placeholder="172.16.0.x" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="管理面 MAC">
              <el-input v-model="editForm.mgmt_mac" placeholder="aa:bb:cc:dd:ee:ff" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="BMC IP">
              <el-input v-model="editForm.bmc_ip" placeholder="172.16.0.x" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="BMC MAC">
              <el-input v-model="editForm.bmc_mac" placeholder="aa:bb:cc:dd:ee:ff" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">控制面 (10GE)</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="控制面 IP">
              <el-input v-model="editForm.ctrl_ip" placeholder="172.16.3.x" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="控制面 MAC">
              <el-input v-model="editForm.ctrl_mac" placeholder="aa:bb:cc:dd:ee:ff" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">数据面 (100GE)</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="数据面 IP">
              <el-input v-model="editForm.data_ip" placeholder="200.1.1.x / 100.1.1.x" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据面 MAC">
              <el-input v-model="editForm.data_mac" placeholder="aa:bb:cc:dd:ee:ff" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="数据协议">
              <el-select v-model="editForm.data_protocol" clearable style="width:100%">
                <el-option label="DPDK" value="DPDK" />
                <el-option label="RDMA" value="RDMA" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">硬件信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="系统版本">
              <el-input v-model="editForm.os_version" placeholder="OpenEuler 22.03" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="CPU 核数">
              <el-input-number v-model="editForm.cpu_cores" :min="1" :precision="0" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="内存 (GB)">
              <el-input-number v-model="editForm.memory_gb" :min="1" :precision="0" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="磁盘 (GB)">
              <el-input-number v-model="editForm.disk_gb" :min="1" :precision="0" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveNode" :loading="saving">保存</el-button>
      </template>
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
import { Refresh, Plus } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const nodes = ref([])
const filterType = ref('')
const filterStatus = ref('')
const selectedNode = ref(null)

const powerDialogVisible = ref(false)
const networkDialogVisible = ref(false)
const networkCheckResult = ref(null)

// ── 新增/编辑 ─────────────────────────────────────────────────
const editDialogVisible = ref(false)
const editMode = ref('add')
const editFormRef = ref(null)
const saving = ref(false)

const emptyForm = () => ({
  hostname: '',
  node_type: 'slave',
  role: '',
  mgmt_ip: '',
  mgmt_mac: '',
  bmc_ip: '',
  bmc_mac: '',
  ctrl_ip: '',
  ctrl_mac: '',
  data_ip: '',
  data_mac: '',
  data_protocol: '',
  os_version: '',
  cpu_cores: null,
  memory_gb: null,
  disk_gb: null,
})

const editForm = ref(emptyForm())

const editRules = {
  hostname: [{ required: true, message: '请输入主机名', trigger: 'blur' }],
  node_type: [{ required: true, message: '请选择节点类型', trigger: 'change' }],
}

const openAdd = () => {
  editMode.value = 'add'
  editForm.value = emptyForm()
  editDialogVisible.value = true
}

const openEdit = (node) => {
  editMode.value = 'edit'
  editForm.value = { ...node }
  editDialogVisible.value = true
}

const saveNode = async () => {
  try {
    await editFormRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = { ...editForm.value }
    // 清理空字符串为 null，避免覆盖已有数据
    Object.keys(payload).forEach(k => {
      if (payload[k] === '') payload[k] = null
    })
    if (editMode.value === 'add') {
      await axios.post('/api/nodes', payload)
      ElMessage.success('节点已新增')
    } else {
      await axios.put(`/api/nodes/${editForm.value.id}`, payload)
      ElMessage.success('节点已更新')
    }
    editDialogVisible.value = false
    loadNodes()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const deleteNode = async (node) => {
  try {
    await ElMessageBox.confirm(
      `确认删除节点 "${node.hostname}"？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await axios.delete(`/api/nodes/${node.id}`)
    ElMessage.success('节点已删除')
    loadNodes()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

// ── 筛选 ──────────────────────────────────────────────────────
const filteredNodes = computed(() => {
  let result = nodes.value
  if (filterType.value) result = result.filter(n => n.node_type === filterType.value)
  if (filterStatus.value) result = result.filter(n => n.status === filterStatus.value)
  return result
})

// ── 样式辅助 ──────────────────────────────────────────────────
const nodeTypeTag = (type) => {
  const map = { master: 'danger', slave: 'info', subswath: 'warning', gstorage: 'success', sensor: '' }
  return map[type] ?? 'info'
}

const getStatusType = (status) => {
  const map = { online: 'success', offline: 'danger', warning: 'warning', deploying: 'info', error: 'danger' }
  return map[status] ?? 'info'
}

// ── 数据加载 ──────────────────────────────────────────────────
const loadNodes = async () => {
  try {
    const response = await axios.get('/api/nodes')
    nodes.value = response.data
  } catch (e) {
    ElMessage.error('获取节点列表失败')
  }
}

// ── 电源控制 ──────────────────────────────────────────────────
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

// ── 网络检查 ──────────────────────────────────────────────────
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
  gap: 8px;
}

.plane-info .ip {
  color: #fff;
  font-size: 13px;
}

.sub-info {
  color: #a0a0a0;
  font-size: 12px;
  margin-top: 4px;
}

.role-text {
  color: #a0a0a0;
  font-size: 11px;
  margin-top: 3px;
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
