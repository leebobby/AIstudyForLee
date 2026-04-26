<template>
  <div class="pxe-deploy">
    <!-- BMC发现区域 -->
    <el-card class="discover-card">
      <template #header>
        <div class="card-header">
          <span>节点发现 (BMC扫描)</span>
          <el-button type="primary" @click="showDiscoverDialog">
            <el-icon><Search /></el-icon>
            扫描BMC
          </el-button>
        </div>
      </template>

      <el-table :data="discoveredNodes" stripe>
        <el-table-column prop="bmc_ip" label="BMC IP" width="150" />
        <el-table-column prop="bmc_mac" label="BMC MAC" width="150" />
        <el-table-column prop="hostname" label="主机名" width="150" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showDeployDialog(row)">
              部署
            </el-button>
            <el-button size="small" @click="checkBMCInfo(row)">
              BMC信息
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- PXE配置区域 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>三平面网络配置</span>
          <el-button type="primary" @click="showConfigDialog">
            <el-icon><Setting /></el-icon>
            新建配置
          </el-button>
        </div>
      </template>

      <el-table :data="pxeConfigs" stripe>
        <el-table-column prop="name" label="配置名称" width="150" />
        <el-table-column prop="mgmt_subnet" label="管理面子网" width="150" />
        <el-table-column prop="ctrl_subnet" label="控制面子网" width="150" />
        <el-table-column prop="data_subnet" label="数据面子网" width="150" />
        <el-table-column prop="created_at" label="创建时间">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="useConfig(row)">
              使用
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 部署任务状态 -->
    <el-card class="deploy-status-card">
      <template #header>
        <div class="card-header">
          <span>部署任务状态</span>
          <el-button @click="refreshDeployStatus">
            <el-icon><Refresh /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>

      <el-table :data="deployTasks" stripe>
        <el-table-column prop="hostname" label="主机名" width="150" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="stage" label="阶段">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="row.status === 'completed' ? 'success' : ''"
            />
            <span class="stage-text">{{ row.stage }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="cancelDeploy(row)">
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- BMC发现对话框 -->
    <el-dialog v-model="discoverDialogVisible" title="BMC节点发现" width="500px">
      <el-form :model="discoverForm" label-width="100px">
        <el-form-item label="子网范围">
          <el-input v-model="discoverForm.subnet" placeholder="例如: 192.168.1.0/24" />
        </el-form-item>
        <el-form-item label="超时时间">
          <el-input-number v-model="discoverForm.timeout" :min="1" :max="60" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="discoverDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startDiscover" :loading="discovering">
          开始扫描
        </el-button>
      </template>
    </el-dialog>

    <!-- 部署配置对话框 -->
    <el-dialog v-model="deployDialogVisible" title="节点部署配置" width="600px">
      <el-form :model="deployForm" label-width="120px">
        <el-form-item label="节点ID">
          <el-input v-model="deployForm.node_id" disabled />
        </el-form-item>
        <el-form-item label="主机名">
          <el-input v-model="deployForm.hostname" placeholder="例如: master-1" />
        </el-form-item>
        <el-form-item label="节点类型">
          <el-radio-group v-model="deployForm.node_type">
            <el-radio label="master">Master节点</el-radio>
            <el-radio label="slave">Slave节点</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-divider>三平面网络配置</el-divider>

        <el-form-item label="管理面IP (GE)">
          <el-input v-model="deployForm.mgmt_ip" placeholder="例如: 192.168.1.10" />
        </el-form-item>
        <el-form-item label="控制面IP (10GE)">
          <el-input v-model="deployForm.ctrl_ip" placeholder="例如: 10.0.0.10" />
        </el-form-item>
        <el-form-item label="数据面IP (100GE)">
          <el-input v-model="deployForm.data_ip" placeholder="例如: 192.168.100.10" />
        </el-form-item>

        <el-alert v-if="deployForm.node_type === 'master'" type="info" :closable="false">
          Master节点将配置DPDK协议用于数据接收
        </el-alert>
        <el-alert v-if="deployForm.node_type === 'slave'" type="info" :closable="false">
          Slave节点将配置RDMA协议用于数据接收
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startDeploy" :loading="deploying">
          开始部署
        </el-button>
      </template>
    </el-dialog>

    <!-- PXE配置创建对话框 -->
    <el-dialog v-model="configDialogVisible" title="创建PXE配置" width="600px">
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="配置名称">
          <el-input v-model="configForm.name" placeholder="例如: default-config" />
        </el-form-item>

        <el-divider>三平面子网配置</el-divider>

        <el-form-item label="管理面子网">
          <el-input v-model="configForm.mgmt_subnet" placeholder="例如: 192.168.1.0/24" />
        </el-form-item>
        <el-form-item label="管理面网关">
          <el-input v-model="configForm.mgmt_gateway" placeholder="例如: 192.168.1.1" />
        </el-form-item>

        <el-form-item label="控制面子网">
          <el-input v-model="configForm.ctrl_subnet" placeholder="例如: 10.0.0.0/24" />
        </el-form-item>
        <el-form-item label="控制面网关">
          <el-input v-model="configForm.ctrl_gateway" placeholder="例如: 10.0.0.1" />
        </el-form-item>

        <el-form-item label="数据面子网">
          <el-input v-model="configForm.data_subnet" placeholder="例如: 192.168.100.0/24" />
        </el-form-item>
        <el-form-item label="数据面网关">
          <el-input v-model="configForm.data_gateway" placeholder="例如: 192.168.100.1" />
        </el-form-item>

        <el-form-item label="DNS服务器">
          <el-input v-model="configForm.dns_servers" placeholder="例如: 8.8.8.8,8.8.4.4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createConfig" :loading="creating">
          创建配置
        </el-button>
      </template>
    </el-dialog>

    <!-- IP规划对话框 -->
    <el-dialog v-model="planDialogVisible" title="IP地址规划" width="80%">
      <el-form :model="planForm" label-width="120px">
        <el-form-item label="PXE配置">
          <el-select v-model="planForm.config_id">
            <el-option v-for="config in pxeConfigs" :key="config.id" :label="config.name" :value="config.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Master数量">
          <el-input-number v-model="planForm.master_count" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="Slave数量">
          <el-input-number v-model="planForm.slave_count" :min="1" :max="50" />
        </el-form-item>
        <el-form-item label="管理面起始IP">
          <el-input v-model="planForm.mgmt_ip_start" placeholder="192.168.1.11" />
        </el-form-item>
        <el-form-item label="控制面起始IP">
          <el-input v-model="planForm.ctrl_ip_start" placeholder="10.0.0.11" />
        </el-form-item>
        <el-form-item label="数据面起始IP">
          <el-input v-model="planForm.data_ip_start" placeholder="192.168.100.11" />
        </el-form-item>
      </el-form>

      <el-button type="primary" @click="generatePlan" :loading="planning">生成规划</el-button>

      <div v-if="ipPlan" class="ip-plan-result">
        <el-divider>规划结果</el-divider>

        <h4>Master节点</h4>
        <el-table :data="ipPlan.masters" stripe size="small">
          <el-table-column prop="hostname" label="主机名" />
          <el-table-column prop="mgmt_ip" label="管理面IP" />
          <el-table-column prop="ctrl_ip" label="控制面IP" />
          <el-table-column prop="data_ip" label="数据面IP" />
          <el-table-column prop="data_protocol" label="数据协议" />
        </el-table>

        <h4>Slave节点</h4>
        <el-table :data="ipPlan.slaves" stripe size="small">
          <el-table-column prop="hostname" label="主机名" />
          <el-table-column prop="mgmt_ip" label="管理面IP" />
          <el-table-column prop="ctrl_ip" label="控制面IP" />
          <el-table-column prop="data_ip" label="数据面IP" />
          <el-table-column prop="data_protocol" label="数据协议" />
        </el-table>

        <el-button type="success" @click="batchDeploy" style="margin-top: 20px">
          批量部署所有节点
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 数据
const discoveredNodes = ref([])
const pxeConfigs = ref([])
const deployTasks = ref([])

// 对话框状态
const discoverDialogVisible = ref(false)
const deployDialogVisible = ref(false)
const configDialogVisible = ref(false)
const planDialogVisible = ref(false)

// 加载状态
const discovering = ref(false)
const deploying = ref(false)
const creating = ref(false)
const planning = ref(false)

// 表单
const discoverForm = ref({
  subnet: '192.168.1.0/24',
  timeout: 5
})

const deployForm = ref({
  node_id: 0,
  hostname: '',
  node_type: 'master',
  mgmt_ip: '',
  ctrl_ip: '',
  data_ip: ''
})

const configForm = ref({
  name: '',
  mgmt_subnet: '',
  ctrl_subnet: '',
  data_subnet: '',
  mgmt_gateway: '',
  ctrl_gateway: '',
  data_gateway: '',
  dns_servers: '8.8.8.8,8.8.4.4'
})

const planForm = ref({
  config_id: 0,
  master_count: 1,
  slave_count: 10,
  mgmt_ip_start: '192.168.1.11',
  ctrl_ip_start: '10.0.0.11',
  data_ip_start: '192.168.100.11'
})

const ipPlan = ref(null)

// 方法
const getStatusType = (status) => {
  const types = {
    'online': 'success',
    'discovered': 'info',
    'deploying': 'warning',
    'installing': 'warning',
    'completed': 'success',
    'error': 'danger',
    'offline': 'danger'
  }
  return types[status] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}

const showDiscoverDialog = () => {
  discoverDialogVisible.value = true
}

const startDiscover = async () => {
  discovering.value = true
  try {
    const response = await axios.post('/api/ipmi/discover', discoverForm.value)
    ElMessage.success(`发现 ${response.data.discovered_count} 个BMC节点`)
    discoveredNodes.value = response.data.nodes || []
    discoverDialogVisible.value = false
  } catch (e) {
    ElMessage.error('BMC扫描失败: ' + e.message)
  } finally {
    discovering.value = false
  }
}

const showDeployDialog = (row) => {
  deployForm.value = {
    node_id: row.id || 0,
    hostname: row.hostname || '',
    node_type: 'slave',
    mgmt_ip: row.mgmt_ip || '',
    ctrl_ip: '',
    data_ip: ''
  }
  deployDialogVisible.value = true
}

const startDeploy = async () => {
  deploying.value = true
  try {
    const response = await axios.post(`/api/pxe/nodes/${deployForm.value.node_id}/deploy`, deployForm.value)
    ElMessage.success('部署任务已启动')
    deployDialogVisible.value = false
    refreshDeployStatus()
  } catch (e) {
    ElMessage.error('部署启动失败: ' + e.message)
  } finally {
    deploying.value = false
  }
}

const showConfigDialog = () => {
  configDialogVisible.value = true
}

const createConfig = async () => {
  creating.value = true
  try {
    const response = await axios.post('/api/pxe/config', configForm.value)
    ElMessage.success('PXE配置已创建')
    pxeConfigs.value.push(response.data)
    configDialogVisible.value = false
  } catch (e) {
    ElMessage.error('配置创建失败: ' + e.message)
  } finally {
    creating.value = false
  }
}

const useConfig = (config) => {
  planForm.value.config_id = config.id
  planDialogVisible.value = true
}

const generatePlan = async () => {
  planning.value = true
  try {
    const response = await axios.post('/api/pxe/network-plan', planForm.value)
    ipPlan.value = response.data.plan
    ElMessage.success('IP规划已生成')
  } catch (e) {
    ElMessage.error('规划生成失败: ' + e.message)
  } finally {
    planning.value = false
  }
}

const batchDeploy = async () => {
  if (!ipPlan.value) return

  const nodes = []
  for (const master of ipPlan.value.masters) {
    nodes.push({
      node_id: 0, // 需要先创建节点
      hostname: master.hostname,
      node_type: 'master',
      mgmt_ip: master.mgmt_ip,
      ctrl_ip: master.ctrl_ip,
      data_ip: master.data_ip
    })
  }
  for (const slave of ipPlan.value.slaves) {
    nodes.push({
      node_id: 0,
      hostname: slave.hostname,
      node_type: 'slave',
      mgmt_ip: slave.mgmt_ip,
      ctrl_ip: slave.ctrl_ip,
      data_ip: slave.data_ip
    })
  }

  try {
    await axios.post('/api/pxe/batch-deploy', nodes)
    ElMessage.success('批量部署已启动')
    planDialogVisible.value = false
    refreshDeployStatus()
  } catch (e) {
    ElMessage.error('批量部署失败: ' + e.message)
  }
}

const refreshDeployStatus = async () => {
  try {
    const response = await axios.get('/api/pxe/status')
    deployTasks.value = response.data
  } catch (e) {
    console.error('获取部署状态失败', e)
  }
}

const checkBMCInfo = async (row) => {
  try {
    const response = await axios.get(`/api/ipmi/nodes/${row.id}/info`)
    ElMessage.info(`BMC温度: ${response.data.temperature}°C, 风扇: ${response.data.fan_speed} RPM`)
  } catch (e) {
    ElMessage.error('获取BMC信息失败')
  }
}

const cancelDeploy = (row) => {
  ElMessage.warning('取消部署功能待实现')
}

const loadData = async () => {
  try {
    const [nodesRes, configsRes, statusRes] = await Promise.all([
      axios.get('/api/nodes'),
      axios.get('/api/pxe/configs'),
      axios.get('/api/pxe/status')
    ])
    discoveredNodes.value = nodesRes.data
    pxeConfigs.value = configsRes.data
    deployTasks.value = statusRes.data
  } catch (e) {
    console.error('数据加载失败', e)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.pxe-deploy {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.discover-card, .config-card, .deploy-status-card {
  margin-bottom: 0;
}

.stage-text {
  margin-left: 10px;
  color: #a0a0a0;
  font-size: 12px;
}

.ip-plan-result {
  margin-top: 20px;
}

.ip-plan-result h4 {
  color: #fff;
  margin: 15px 0 10px 0;
}
</style>