<template>
  <div class="network-map">
    <!-- 平面选择器 -->
    <div class="plane-selector">
      <el-radio-group v-model="currentPlane" @change="updateTopology">
        <el-radio-button label="all">全部视图</el-radio-button>
        <el-radio-button label="management">管理面 (GE)</el-radio-button>
        <el-radio-button label="control">控制面 (10GE)</el-radio-button>
        <el-radio-button label="data_front">数据面前段 (DPDK)</el-radio-button>
        <el-radio-button label="data_back">数据面后段 (RDMA)</el-radio-button>
      </el-radio-group>

      <div class="legend">
        <span class="legend-item">
          <span class="dot normal"></span>正常
        </span>
        <span class="legend-item">
          <span class="dot warning"></span>告警
        </span>
        <span class="legend-item">
          <span class="dot fault"></span>故障
        </span>
        <span class="legend-item">
          <span class="dot offline"></span>离线
        </span>
      </div>
    </div>

    <!-- 拓扑图 -->
    <el-card class="topology-card">
      <div ref="topologyContainer" class="topology-container">
        <!-- D3.js 将在此渲染拓扑图 -->
      </div>
    </el-card>

    <!-- 故障详情面板 -->
    <el-card v-if="selectedElement" class="detail-panel">
      <template #header>
        <div class="card-header">
          <span>{{ selectedElement.type === 'node' ? '节点详情' : '链路详情' }}</span>
          <el-button size="small" @click="selectedElement = null">关闭</el-button>
        </div>
      </template>

      <div v-if="selectedElement.type === 'node'" class="node-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="主机名">{{ selectedElement.data.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedElement.data.type }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedElement.data.status)">
              {{ selectedElement.data.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="plane-details">
          <h4>三平面状态</h4>
          <div class="plane-row">
            <span class="plane-label">管理面</span>
            <span class="plane-ip">{{ selectedElement.data.planes?.management?.ip }}</span>
            <el-tag :type="selectedElement.data.planes?.management?.status === 'online' ? 'success' : 'danger'" size="small">
              {{ selectedElement.data.planes?.management?.status }}
            </el-tag>
          </div>
          <div class="plane-row">
            <span class="plane-label">控制面</span>
            <span class="plane-ip">{{ selectedElement.data.planes?.control?.ip }}</span>
            <el-tag :type="selectedElement.data.planes?.control?.status === 'online' ? 'success' : 'danger'" size="small">
              {{ selectedElement.data.planes?.control?.status }}
            </el-tag>
          </div>
          <div class="plane-row">
            <span class="plane-label">数据面</span>
            <span class="plane-ip">{{ selectedElement.data.planes?.data?.ip }}</span>
            <el-tag :type="selectedElement.data.planes?.data?.status === 'online' ? 'success' : 'danger'" size="small">
              {{ selectedElement.data.planes?.data?.status }}
            </el-tag>
            <span class="protocol">{{ selectedElement.data.planes?.data?.protocol }}</span>
          </div>
        </div>

        <div class="action-buttons">
          <el-button type="primary" @click="diagnoseNode">诊断分析</el-button>
          <el-button @click="collectLogs">收集日志</el-button>
          <el-button type="warning" @click="showPowerControl">电源控制</el-button>
        </div>
      </div>

      <div v-if="selectedElement.type === 'link'" class="link-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="源节点">{{ selectedElement.data.source }}</el-descriptions-item>
          <el-descriptions-item label="目标节点">{{ selectedElement.data.target }}</el-descriptions-item>
          <el-descriptions-item label="平面">{{ selectedElement.data.plane }}</el-descriptions-item>
          <el-descriptions-item label="协议">{{ selectedElement.data.protocol }}</el-descriptions-item>
          <el-descriptions-item label="带宽">{{ selectedElement.data.bandwidth }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getLinkStatusType(selectedElement.data.status)">
              {{ selectedElement.data.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="延迟">{{ selectedElement.data.latency }}ms</el-descriptions-item>
          <el-descriptions-item label="丢包率">{{ selectedElement.data.packet_loss }}%</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <!-- 网络状态统计 -->
    <el-card class="stats-card">
      <template #header>
        <span>三平面网络统计</span>
      </template>

      <div class="stats-grid">
        <div class="stat-item">
          <h5>管理面 (GE)</h5>
          <p>在线节点: {{ networkStatus.management?.nodes_online }}/{{ networkStatus.management?.nodes_total }}</p>
          <p>链路正常: {{ networkStatus.management?.links?.normal }}/{{ networkStatus.management?.links?.total }}</p>
          <el-progress
            :percentage="calcPercentage(networkStatus.management?.nodes_online, networkStatus.management?.nodes_total)"
            :color="#67c23a"
          />
        </div>

        <div class="stat-item">
          <h5>控制面 (10GE)</h5>
          <p>在线节点: {{ networkStatus.control?.nodes_online }}/{{ networkStatus.control?.nodes_total }}</p>
          <p>平均延迟: {{ networkStatus.control?.links?.avg_latency?.toFixed(2) }}ms</p>
          <el-progress
            :percentage="calcPercentage(networkStatus.control?.nodes_online, networkStatus.control?.nodes_total)"
            :color="#409eff"
          />
        </div>

        <div class="stat-item">
          <h5>数据面前段 (DPDK)</h5>
          <p>Master在线: {{ networkStatus.data_front?.nodes_online }}/{{ networkStatus.data_front?.nodes_total }}</p>
          <p>{{ networkStatus.data_front?.description }}</p>
          <el-progress
            :percentage="calcPercentage(networkStatus.data_front?.nodes_online, networkStatus.data_front?.nodes_total)"
            :color="#e94560"
          />
        </div>

        <div class="stat-item">
          <h5>数据面后段 (RDMA)</h5>
          <p>Slave在线: {{ networkStatus.data_back?.nodes_online }}/{{ networkStatus.data_back?.nodes_total }}</p>
          <p>{{ networkStatus.data_back?.description }}</p>
          <el-progress
            :percentage="calcPercentage(networkStatus.data_back?.nodes_online, networkStatus.data_back?.nodes_total)"
            :color="#f56c6c"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as d3 from 'd3'

const topologyContainer = ref(null)
const currentPlane = ref('all')
const selectedElement = ref(null)
const topologyData = ref({ nodes: [], links: [] })
const networkStatus = ref({})

let svg = null
let simulation = null

const getStatusType = (status) => {
  const types = {
    'online': 'success',
    'normal': 'success',
    'offline': 'danger',
    'down': 'danger',
    'warning': 'warning',
    'degraded': 'warning',
    'error': 'danger'
  }
  return types[status] || 'info'
}

const getLinkStatusType = (status) => {
  const types = {
    'normal': 'success',
    'degraded': 'warning',
    'down': 'danger'
  }
  return types[status] || 'info'
}

const calcPercentage = (online, total) => {
  if (!total || total === 0) return 0
  return Math.round((online / total) * 100)
}

const loadTopology = async () => {
  try {
    const response = await axios.get('/api/network/topology-graph')
    topologyData.value = response.data
    renderTopology()
  } catch (e) {
    ElMessage.error('获取拓扑数据失败')
  }
}

const loadNetworkStatus = async () => {
  try {
    const response = await axios.get('/api/network/status')
    networkStatus.value = response.data
  } catch (e) {
    console.error('获取网络状态失败', e)
  }
}

const getNodeColor = (status) => {
  const colors = {
    'online': '#67c23a',
    'normal': '#67c23a',
    'offline': '#909399',
    'warning': '#e6a23c',
    'error': '#f56c6c',
    'degraded': '#e6a23c'
  }
  return colors[status] || '#409eff'
}

const getLinkColor = (plane) => {
  const colors = {
    'management': '#67c23a',
    'control': '#409eff',
    'data_front': '#e94560',
    'data_back': '#f56c6c'
  }
  return colors[plane] || '#909399'
}

const renderTopology = () => {
  if (!topologyContainer.value) return

  const width = topologyContainer.value.clientWidth
  const height = 500

  // 清除旧图
  d3.select(topologyContainer.value).selectAll('*').remove()

  // 创建SVG
  svg = d3.select(topologyContainer.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .style('background', '#1a1a2e')

  // 过滤数据
  let nodes = topologyData.value.nodes
  let links = topologyData.value.links

  if (currentPlane.value !== 'all') {
    links = links.filter(l => l.plane === currentPlane.value || l.plane.includes(currentPlane.value.split('_')[0]))
  }

  // 创建力导向图
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(150))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(40))

  // 绘制链路
  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', d => getLinkColor(d.plane))
    .attr('stroke-width', d => d.bandwidth === '100GE' ? 4 : d.bandwidth === '10GE' ? 2 : 1)
    .attr('stroke-opacity', 0.6)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      selectedElement.value = { type: 'link', data: d }
    })

  // 添加链路标签
  link.append('title')
    .text(d => `${d.protocol} - ${d.bandwidth}`)

  // 绘制节点
  const node = svg.append('g')
    .selectAll('g')
    .data(nodes)
    .enter()
    .append('g')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )
    .on('click', (event, d) => {
      selectedElement.value = { type: 'node', data: d }
    })

  // 节点圆形
  node.append('circle')
    .attr('r', 25)
    .attr('fill', d => getNodeColor(d.status))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)

  // 节点标签
  node.append('text')
    .text(d => d.name)
    .attr('text-anchor', 'middle')
    .attr('dy', 35)
    .attr('fill', '#fff')
    .attr('font-size', '12px')

  // 节点类型标签
  node.append('text')
    .text(d => d.type?.substring(0, 1).toUpperCase())
    .attr('text-anchor', 'middle')
    .attr('dy', 4)
    .attr('fill', '#fff')
    .attr('font-size', '14px')
    .attr('font-weight', 'bold')

  // 更新位置
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  }

  function dragged(event) {
    event.subject.fx = event.x
    event.subject.fy = event.y
  }

  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  }
}

const updateTopology = () => {
  renderTopology()
}

const diagnoseNode = async () => {
  if (!selectedElement.value) return
  try {
    const response = await axios.get(`/api/diagnose/nodes/${selectedElement.value.data.id}`)
    ElMessage.success('诊断分析完成')
    // 可以跳转到诊断页面查看详情
  } catch (e) {
    ElMessage.error('诊断分析失败')
  }
}

const collectLogs = async () => {
  if (!selectedElement.value) return
  try {
    await axios.post(`/api/diagnose/nodes/${selectedElement.value.data.id}/collect-logs`)
    ElMessage.success('日志收集已启动')
  } catch (e) {
    ElMessage.error('日志收集失败')
  }
}

const showPowerControl = () => {
  ElMessage.info('请在节点管理页面进行电源控制')
}

watch(currentPlane, () => {
  renderTopology()
})

onMounted(() => {
  loadTopology()
  loadNetworkStatus()

  // 窗口大小变化时重新渲染
  window.addEventListener('resize', renderTopology)
})

onUnmounted(() => {
  window.removeEventListener('resize', renderTopology)
  if (simulation) simulation.stop()
})
</script>

<style scoped>
.network-map {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.plane-selector {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.legend {
  display: flex;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #fff;
  font-size: 12px;
}

.legend-item .dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.normal { background: #67c23a; }
.dot.warning { background: #e6a23c; }
.dot.fault { background: #f56c6c; }
.dot.offline { background: #909399; }

.topology-card {
  min-height: 550px;
}

.topology-container {
  width: 100%;
  height: 500px;
}

.detail-panel {
  position: fixed;
  right: 20px;
  top: 100px;
  width: 400px;
  z-index: 100;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plane-details {
  margin-top: 20px;
}

.plane-details h4 {
  color: #e94560;
  margin: 0 0 10px 0;
}

.plane-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
}

.plane-label {
  color: #a0a0a0;
  width: 60px;
}

.plane-ip {
  color: #fff;
}

.protocol {
  color: #e94560;
  font-size: 12px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.stats-card {
  margin-top: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-item {
  padding: 15px;
  background: #0f3460;
  border-radius: 8px;
}

.stat-item h5 {
  color: #fff;
  margin: 0 0 10px 0;
  font-size: 14px;
}

.stat-item p {
  color: #a0a0a0;
  margin: 5px 0;
  font-size: 12px;
}
</style>