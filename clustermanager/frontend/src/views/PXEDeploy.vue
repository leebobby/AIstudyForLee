<template>
  <div class="pxe-deploy">
    <el-tabs v-model="activeTab" type="border-card">

      <!-- ══════════════════════════════════════════════════════════
           Tab 1: IP 规划
           ══════════════════════════════════════════════════════════ -->
      <el-tab-pane label="IP 规划" name="planning">
        <el-card shadow="never">
          <template #header>
            <span>v2 六子网 IP 规划</span>
          </template>

          <!-- 子网说明 -->
          <el-alert type="info" :closable="false" style="margin-bottom:16px">
            <template #title>
              管理面 BMC: <b>172.16.0.0/24</b> &nbsp;|&nbsp;
              控制面 10GE: <b>172.16.3.0/24</b> &nbsp;|&nbsp;
              DPDK-1: <b>200.1.1.0/24</b> &nbsp;|&nbsp;
              DPDK-2: <b>200.1.2.0/24</b> &nbsp;|&nbsp;
              RDMA-1: <b>100.1.1.0/24</b> &nbsp;|&nbsp;
              RDMA-2: <b>100.1.2.0/24</b>
            </template>
          </el-alert>

          <!-- 节点数量 -->
          <el-form :model="planForm" inline label-width="110px">
            <el-form-item label="Master 数量">
              <el-input-number v-model="planForm.master_count" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="Slave 数量">
              <el-input-number v-model="planForm.slave_count" :min="1" :max="50" />
            </el-form-item>
            <el-form-item label="SubSwath 数量">
              <el-input-number v-model="planForm.subswath_count" :min="1" :max="8" />
            </el-form-item>
            <el-form-item label="GStorage 数量">
              <el-input-number v-model="planForm.gstorage_count" :min="1" :max="4" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generatePlan" :loading="planning">
                生成规划
              </el-button>
              <el-button
                type="success"
                :disabled="!ipPlanResult"
                @click="applyPlanToNodesJson"
                :loading="applyingPlan"
              >
                应用到 nodes.json
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 规划结果 -->
        <template v-if="ipPlanResult">
          <el-alert
            type="success"
            :title="`共 ${ipPlanResult.total_nodes} 个节点（含 PXE Host）`"
            :closable="false"
            style="margin:12px 0"
          />

          <!-- PXE Host -->
          <el-card shadow="never" style="margin-bottom:12px">
            <template #header><span class="role-tag role-host">PXE Host ×1</span></template>
            <el-table :data="ipPlanResult.plan.pxe_host" size="small" stripe>
              <el-table-column prop="hostname"  label="主机名"    width="140" />
              <el-table-column prop="bmc_ip"    label="BMC IP"   width="140" />
              <el-table-column prop="ctrl_ip"   label="控制面 IP" width="140" />
              <el-table-column prop="note"      label="说明" />
            </el-table>
          </el-card>

          <!-- Master -->
          <el-card shadow="never" style="margin-bottom:12px">
            <template #header>
              <span class="role-tag role-master">Master ×{{ ipPlanResult.plan.masters.length }}</span>
            </template>
            <el-table :data="ipPlanResult.plan.masters" size="small" stripe>
              <el-table-column prop="hostname"  label="主机名"     width="120" />
              <el-table-column prop="bmc_ip"    label="BMC IP"    width="130" />
              <el-table-column prop="ctrl_ip"   label="控制面"     width="130" />
              <el-table-column prop="dpdk1_ip"  label="DPDK-1"    width="120" />
              <el-table-column prop="dpdk2_ip"  label="DPDK-2"    width="120" />
              <el-table-column prop="rdma1_ip"  label="RDMA-1"    width="120" />
              <el-table-column prop="rdma2_ip"  label="RDMA-2"    width="120" />
              <el-table-column prop="hugepages_1g" label="大页(×1G)" width="90" />
            </el-table>
          </el-card>

          <!-- Slave -->
          <el-card shadow="never" style="margin-bottom:12px">
            <template #header>
              <span class="role-tag role-slave">Slave ×{{ ipPlanResult.plan.slaves.length }}</span>
            </template>
            <el-table :data="ipPlanResult.plan.slaves" size="small" stripe>
              <el-table-column prop="hostname" label="主机名"   width="120" />
              <el-table-column prop="bmc_ip"   label="BMC IP"  width="140" />
              <el-table-column prop="ctrl_ip"  label="控制面"  width="140" />
              <el-table-column prop="rdma1_ip" label="RDMA-1"  width="140" />
              <el-table-column prop="nics"     label="网口分配" />
            </el-table>
          </el-card>

          <!-- SubSwath -->
          <el-card shadow="never" style="margin-bottom:12px">
            <template #header>
              <span class="role-tag role-subswath">SubSwath ×{{ ipPlanResult.plan.subswaths.length }}</span>
            </template>
            <el-table :data="ipPlanResult.plan.subswaths" size="small" stripe>
              <el-table-column prop="hostname"    label="主机名"   width="130" />
              <el-table-column prop="bmc_ip"      label="BMC IP"  width="140" />
              <el-table-column prop="ctrl_ip"     label="控制面"  width="140" />
              <el-table-column prop="rdma1_ip"    label="RDMA-1"  width="140" />
              <el-table-column prop="rdma2_ip"    label="RDMA-2"  width="140" />
              <el-table-column prop="data_disks"  label="数据盘"  width="140" />
              <el-table-column prop="data_raid"   label="RAID 方案" />
            </el-table>
          </el-card>

          <!-- GStorage -->
          <el-card shadow="never">
            <template #header>
              <span class="role-tag role-gstorage">GStorage ×{{ ipPlanResult.plan.gstorages.length }}</span>
            </template>
            <el-table :data="ipPlanResult.plan.gstorages" size="small" stripe>
              <el-table-column prop="hostname"   label="主机名"   width="130" />
              <el-table-column prop="bmc_ip"     label="BMC IP"  width="140" />
              <el-table-column prop="ctrl_ip"    label="控制面"  width="140" />
              <el-table-column prop="rdma2_ip"   label="RDMA-2"  width="140" />
              <el-table-column prop="data_disks" label="数据盘"  width="140" />
              <el-table-column prop="data_raid"  label="RAID 方案" />
            </el-table>
          </el-card>
        </template>
      </el-tab-pane>

      <!-- ══════════════════════════════════════════════════════════
           Tab 2: 节点配置 (nodes.json)
           ══════════════════════════════════════════════════════════ -->
      <el-tab-pane label="节点配置" name="nodes">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>nodes.json — 节点 MAC 与配置映射（{{ nodeList.length }} 个节点）</span>
              <div>
                <el-button size="small" @click="loadNodeList">
                  <el-icon><Refresh /></el-icon> 刷新
                </el-button>
                <el-button size="small" type="warning" @click="resetToTemplate">
                  重置为模板 MAC
                </el-button>
              </div>
            </div>
          </template>

          <el-alert type="warning" :closable="false" style="margin-bottom:12px">
            <template #title>
              表中 MAC 为占位符，请点击编辑替换为实际硬件 MAC（通过 <code>ip link show</code> 获取）
            </template>
          </el-alert>

          <el-table :data="nodeList" size="small" stripe row-key="mac">
            <el-table-column prop="hostname" label="主机名" width="130" fixed />
            <el-table-column label="角色" width="100">
              <template #default="{ row }">
                <el-tag :type="roleTagType(row.role)" size="small">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="MAC 地址" width="170">
              <template #default="{ row }">
                <span class="mac-text">{{ row.mac }}</span>
                <el-button
                  link
                  size="small"
                  style="margin-left:4px"
                  @click="openMacEdit(row)"
                >编辑</el-button>
              </template>
            </el-table-column>
            <el-table-column prop="bmc_ip"   label="BMC IP"  width="130" />
            <el-table-column prop="ctrl_ip"  label="控制面 IP" width="130" />
            <el-table-column label="RDMA IP" width="200">
              <template #default="{ row }">
                <span>{{ row.rdma_ips }}</span>
              </template>
            </el-table-column>
            <el-table-column label="DPDK IP" width="220">
              <template #default="{ row }">
                <span v-if="row.dpdk_ips">{{ row.dpdk_ips }}</span>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>
            <el-table-column label="数据盘 / RAID" min-width="160">
              <template #default="{ row }">
                <span v-if="row.data_disks">
                  {{ row.data_disks }}
                  <el-tag v-if="row.data_raid_level" type="warning" size="small" style="margin-left:4px">
                    {{ row.data_raid_level.toUpperCase() }}
                  </el-tag>
                </span>
                <span v-else class="text-muted">无数据盘</span>
              </template>
            </el-table-column>
            <el-table-column label="大页" width="70">
              <template #default="{ row }">
                <span v-if="row.hugepages_1g && row.hugepages_1g !== '0'">
                  {{ row.hugepages_1g }}G
                </span>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- MAC 编辑对话框 -->
        <el-dialog v-model="macEditVisible" title="修改节点 MAC 地址" width="480px">
          <el-form label-width="100px">
            <el-form-item label="主机名">
              <el-input :value="macEditRow.hostname" disabled />
            </el-form-item>
            <el-form-item label="当前 MAC">
              <el-input :value="macEditRow.mac" disabled />
            </el-form-item>
            <el-form-item label="新 MAC">
              <el-input
                v-model="macEditNew"
                placeholder="例: 00:11:22:33:44:55"
                clearable
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="macEditVisible = false">取消</el-button>
            <el-button type="primary" @click="saveMacEdit" :loading="savingMac">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- ══════════════════════════════════════════════════════════
           Tab 3: 配置文件生成
           ══════════════════════════════════════════════════════════ -->
      <el-tab-pane label="配置生成" name="configs">
        <el-row :gutter="16">
          <!-- DHCP 配置 -->
          <el-col :span="12">
            <el-card shadow="never" style="margin-bottom:16px">
              <template #header>
                <div class="card-header">
                  <span>dhcpd.conf（控制面 172.16.3.0/24）</span>
                  <div>
                    <el-button size="small" @click="fetchDhcpConfig" :loading="loadingDhcp">生成</el-button>
                    <el-button size="small" @click="copyText(dhcpConfig)" :disabled="!dhcpConfig">复制</el-button>
                  </div>
                </div>
              </template>
              <el-alert type="info" :closable="false" style="margin-bottom:8px">
                <template #title>
                  保存至 <code>/etc/dhcp/dhcpd.conf</code>，
                  并在 <code>/etc/sysconfig/dhcpd</code> 中设置
                  <code>DHCPDARGS=eno3</code>（100GE 物理接口）
                </template>
              </el-alert>
              <el-input
                v-model="dhcpConfig"
                type="textarea"
                :rows="18"
                class="code-textarea"
                placeholder="点击「生成」按钮获取配置..."
              />
            </el-card>
          </el-col>

          <!-- GRUB 配置 -->
          <el-col :span="12">
            <el-card shadow="never" style="margin-bottom:16px">
              <template #header>
                <div class="card-header">
                  <span>grub.cfg（aarch64 UEFI 引导）</span>
                  <div>
                    <el-button size="small" @click="fetchGrubConfig" :loading="loadingGrub">生成</el-button>
                    <el-button size="small" @click="copyText(grubConfig)" :disabled="!grubConfig">复制</el-button>
                  </div>
                </div>
              </template>
              <el-alert type="info" :closable="false" style="margin-bottom:8px">
                <template #title>
                  保存至 <code>/var/lib/tftpboot/grub.cfg</code>
                </template>
              </el-alert>
              <el-input
                v-model="grubConfig"
                type="textarea"
                :rows="18"
                class="code-textarea"
                placeholder="点击「生成」按钮获取配置..."
              />
            </el-card>
          </el-col>

          <!-- RAID1 初始化脚本 -->
          <el-col :span="12">
            <el-card shadow="never" style="margin-bottom:16px">
              <template #header>
                <div class="card-header">
                  <span>setup-raid1.sh（iBMC Redfish 批量建 RAID1）</span>
                  <div>
                    <el-button size="small" @click="fetchRaid1Script" :loading="loadingRaid1">生成</el-button>
                    <el-button size="small" @click="copyText(raid1Script)" :disabled="!raid1Script">复制</el-button>
                  </div>
                </div>
              </template>
              <el-alert type="warning" :closable="false" style="margin-bottom:8px">
                <template #title>
                  部署前在 PXE Host 执行，为所有节点创建 2×960G RAID1 系统盘
                </template>
              </el-alert>
              <el-input
                v-model="raid1Script"
                type="textarea"
                :rows="14"
                class="code-textarea"
                placeholder="点击「生成」按钮获取脚本..."
              />
            </el-card>
          </el-col>

          <!-- PXE 引导脚本 -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <div class="card-header">
                  <span>set-pxe-boot.sh（ipmitool 批量设置 PXE 启动）</span>
                  <div>
                    <el-button size="small" @click="fetchPxeBootScript" :loading="loadingPxeBoot">生成</el-button>
                    <el-button size="small" @click="copyText(pxeBootScript)" :disabled="!pxeBootScript">复制</el-button>
                  </div>
                </div>
              </template>
              <el-alert type="info" :closable="false" style="margin-bottom:8px">
                <template #title>
                  每批部署前执行，设置目标节点下次从 PXE 启动
                </template>
              </el-alert>
              <el-input
                v-model="pxeBootScript"
                type="textarea"
                :rows="14"
                class="code-textarea"
                placeholder="点击「生成」按钮获取脚本..."
              />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- ══════════════════════════════════════════════════════════
           Tab 4: 分批部署
           ══════════════════════════════════════════════════════════ -->
      <el-tab-pane label="分批部署" name="deploy">
        <el-alert type="warning" :closable="false" style="margin-bottom:16px">
          <template #title>
            <b>部署顺序：第一批 → 等待 NFS 就绪 → 第二批 → 等待大页就绪 → 第三批</b>
          </template>
          <div style="margin-top:6px;font-size:13px;color:#b0b0b0">
            Slave firstboot 会轮询 NFS Server，Server 就绪前不会挂载。
            Master firstboot 会自动 reboot 一次（大页/驱动生效）。
          </div>
        </el-alert>

        <el-row :gutter="16">
          <!-- 第一批: SubSwath + GStorage -->
          <el-col :span="8">
            <el-card shadow="never" class="wave-card">
              <template #header>
                <div class="wave-header">
                  <el-tag type="warning" size="large">第一批</el-tag>
                  <span>NFS Server（SubSwath + GStorage）</span>
                </div>
              </template>
              <div class="wave-nodes">
                <div
                  v-for="node in waveNodes(1)"
                  :key="node.mac"
                  class="wave-node-item"
                >
                  <el-tag :type="roleTagType(node.role)" size="small">{{ node.role }}</el-tag>
                  <span class="node-name">{{ node.hostname }}</span>
                  <span class="node-bmc">{{ node.bmc_ip }}</span>
                </div>
              </div>
              <div class="wave-meta">
                <el-icon><Clock /></el-icon> 预计 ~20 min（含 NVMe RAID10 初始化）
              </div>
              <el-divider />
              <div class="wave-check">
                <b>就绪验证：</b>
                <code>showmount -e 100.1.1.170</code><br>
                <code>showmount -e 100.1.1.171</code><br>
                <code>showmount -e 100.1.2.172</code>
              </div>
              <el-button
                type="warning"
                style="margin-top:12px;width:100%"
                @click="triggerWaveDeploy(1)"
                :loading="deployingWave === 1"
              >
                触发第一批部署
              </el-button>
            </el-card>
          </el-col>

          <!-- 第二批: Master -->
          <el-col :span="8">
            <el-card shadow="never" class="wave-card">
              <template #header>
                <div class="wave-header">
                  <el-tag type="success" size="large">第二批</el-tag>
                  <span>Master（DPDK + RDMA 计算控制）</span>
                </div>
              </template>
              <div class="wave-nodes">
                <div
                  v-for="node in waveNodes(2)"
                  :key="node.mac"
                  class="wave-node-item"
                >
                  <el-tag type="success" size="small">master</el-tag>
                  <span class="node-name">{{ node.hostname }}</span>
                  <span class="node-bmc">{{ node.bmc_ip }}</span>
                </div>
              </div>
              <div class="wave-meta">
                <el-icon><Clock /></el-icon> 预计 ~25 min（含大页 reboot）
              </div>
              <el-divider />
              <div class="wave-check">
                <b>就绪验证：</b>
                <code>grep HugePages_Total /proc/meminfo</code>
                <div style="color:#6c6c6c;font-size:12px">期望 100 个 1G 大页</div>
              </div>
              <el-button
                type="success"
                style="margin-top:12px;width:100%"
                @click="triggerWaveDeploy(2)"
                :loading="deployingWave === 2"
              >
                触发第二批部署
              </el-button>
            </el-card>
          </el-col>

          <!-- 第三批: Slave -->
          <el-col :span="8">
            <el-card shadow="never" class="wave-card">
              <template #header>
                <div class="wave-header">
                  <el-tag type="primary" size="large">第三批</el-tag>
                  <span>Slave（RDMA 计算 + NFS 客户端）</span>
                </div>
              </template>
              <div class="wave-nodes">
                <div
                  v-for="node in waveNodes(3)"
                  :key="node.mac"
                  class="wave-node-item"
                >
                  <el-tag type="primary" size="small">slave</el-tag>
                  <span class="node-name">{{ node.hostname }}</span>
                  <span class="node-bmc">{{ node.bmc_ip }}</span>
                </div>
              </div>
              <div class="wave-meta">
                <el-icon><Clock /></el-icon> 预计 ~20 min（含 NFS 挂载等待）
              </div>
              <el-divider />
              <div class="wave-check">
                <b>就绪验证：</b>
                <code>df -h | grep -E "swath|global"</code>
              </div>
              <el-button
                type="primary"
                style="margin-top:12px;width:100%"
                @click="triggerWaveDeploy(3)"
                :loading="deployingWave === 3"
              >
                触发第三批部署
              </el-button>
            </el-card>
          </el-col>
        </el-row>

        <!-- node-env API 说明 -->
        <el-card shadow="never" style="margin-top:16px">
          <template #header><span>firstboot node-env API</span></template>
          <el-alert type="info" :closable="false">
            <template #title>节点 firstboot 阶段调用以下接口获取配置（detect.sh）</template>
          </el-alert>
          <pre class="code-block">curl -sf http://172.16.3.10:8000/api/pxe/node-env?mac=&lt;10GE_MAC&gt; \
     -o /etc/node-role/env</pre>
          <el-form inline style="margin-top:12px">
            <el-form-item label="查询 MAC">
              <el-input v-model="queryMac" placeholder="aa:bb:cc:11:00:01" style="width:200px" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="queryNodeEnv" :loading="queryingEnv">查询环境变量</el-button>
            </el-form-item>
          </el-form>
          <el-input
            v-if="nodeEnvResult"
            v-model="nodeEnvResult"
            type="textarea"
            :rows="12"
            class="code-textarea"
          />
        </el-card>
      </el-tab-pane>

      <!-- ══════════════════════════════════════════════════════════
           Tab 5: 状态监控
           ══════════════════════════════════════════════════════════ -->
      <el-tab-pane label="状态监控" name="status">
        <!-- BMC 节点发现 -->
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header>
            <div class="card-header">
              <span>节点发现（BMC 扫描）</span>
              <el-button type="primary" size="small" @click="discoverDialogVisible = true">
                <el-icon><Search /></el-icon> 扫描 BMC
              </el-button>
            </div>
          </template>
          <el-table :data="discoveredNodes" stripe size="small">
            <el-table-column prop="bmc_ip"    label="BMC IP"   width="140" />
            <el-table-column prop="bmc_mac"   label="BMC MAC"  width="160" />
            <el-table-column prop="hostname"  label="主机名"   width="140" />
            <el-table-column prop="status"    label="状态"     width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="showDeployDialog(row)">部署</el-button>
                <el-button size="small" @click="checkBMCInfo(row)">BMC 信息</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 部署任务状态 -->
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>部署任务状态</span>
              <el-button size="small" @click="refreshDeployStatus">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <el-empty v-if="deployTasks.length === 0" description="暂无进行中的部署任务" :image-size="60" />
          <el-table v-else :data="deployTasks" stripe size="small">
            <el-table-column prop="hostname" label="主机名"  width="140" />
            <el-table-column prop="status"   label="状态"   width="120">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="stage"    label="阶段"   width="300">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :status="row.status === 'completed' ? 'success' : ''" />
                <span class="stage-text">{{ row.stage }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="message"  label="消息" />
          </el-table>
        </el-card>
      </el-tab-pane>

    </el-tabs>

    <!-- ── BMC 发现对话框 ─────────────────────────────────────────────── -->
    <el-dialog v-model="discoverDialogVisible" title="BMC 节点发现" width="460px">
      <el-form :model="discoverForm" label-width="100px">
        <el-form-item label="子网范围">
          <el-input v-model="discoverForm.subnet" placeholder="例如: 172.16.0.0/24" />
        </el-form-item>
        <el-form-item label="超时时间(s)">
          <el-input-number v-model="discoverForm.timeout" :min="1" :max="60" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="discoverDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startDiscover" :loading="discovering">开始扫描</el-button>
      </template>
    </el-dialog>

    <!-- ── 单节点部署对话框 ───────────────────────────────────────────── -->
    <el-dialog v-model="deployDialogVisible" title="节点部署配置" width="560px">
      <el-form :model="deployForm" label-width="120px">
        <el-form-item label="主机名">
          <el-input v-model="deployForm.hostname" placeholder="例如: master-01" />
        </el-form-item>
        <el-form-item label="节点类型">
          <el-radio-group v-model="deployForm.node_type">
            <el-radio label="master">Master</el-radio>
            <el-radio label="slave">Slave</el-radio>
            <el-radio label="subswath">SubSwath</el-radio>
            <el-radio label="gstorage">GStorage</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-divider>三平面网络</el-divider>
        <el-form-item label="BMC IP (GE)">
          <el-input v-model="deployForm.mgmt_ip" placeholder="172.16.0.11" />
        </el-form-item>
        <el-form-item label="控制面 (10GE)">
          <el-input v-model="deployForm.ctrl_ip" placeholder="172.16.3.11" />
        </el-form-item>
        <el-form-item label="数据面 (100GE)">
          <el-input v-model="deployForm.data_ip" placeholder="100.1.1.11" />
        </el-form-item>
        <el-alert
          v-if="deployForm.node_type === 'master'"
          type="info" :closable="false"
          title="Master: DPDK 接收 + RDMA 计算控制，需 100G×4 和大页内存"
        />
        <el-alert
          v-if="deployForm.node_type === 'subswath'"
          type="warning" :closable="false"
          title="SubSwath: NFS Server，firstboot 将创建 4×NVMe 软件 RAID10"
        />
      </el-form>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startDeploy" :loading="deploying">开始部署</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, Clock } from '@element-plus/icons-vue'

// ── 全局状态 ──────────────────────────────────────────────────────────────────
const activeTab = ref('planning')

// ── Tab1: IP 规划 ─────────────────────────────────────────────────────────────
const planForm = ref({ master_count: 6, slave_count: 12, subswath_count: 2, gstorage_count: 1 })
const ipPlanResult = ref(null)
const planning = ref(false)
const applyingPlan = ref(false)

async function generatePlan() {
  planning.value = true
  try {
    const res = await axios.post('/api/pxe/network-plan', planForm.value)
    ipPlanResult.value = res.data
    ElMessage.success(`规划已生成，共 ${res.data.total_nodes} 个节点`)
  } catch (e) {
    ElMessage.error('规划生成失败: ' + e.message)
  } finally {
    planning.value = false
  }
}

async function applyPlanToNodesJson() {
  try {
    await ElMessageBox.confirm(
      '将用规划结果（含模板 MAC）覆盖当前 nodes.json，实际部署前需手动替换 MAC 地址。确认继续？',
      '确认覆盖',
      { type: 'warning' }
    )
  } catch {
    return
  }
  applyingPlan.value = true
  try {
    // 先获取现有 nodes.json 模板（已有完整字段），再刷新节点列表
    const res = await axios.get('/api/pxe/nodes-json')
    await axios.post('/api/pxe/nodes-json', res.data)
    ElMessage.success('nodes.json 已重置为规划模板')
    await loadNodeList()
    activeTab.value = 'nodes'
  } catch (e) {
    ElMessage.error('应用失败: ' + e.message)
  } finally {
    applyingPlan.value = false
  }
}

// ── Tab2: 节点配置 ────────────────────────────────────────────────────────────
const nodeList = ref([])
const macEditVisible = ref(false)
const macEditRow = ref({})
const macEditNew = ref('')
const savingMac = ref(false)

async function loadNodeList() {
  try {
    const res = await axios.get('/api/pxe/nodes-json/node-list')
    nodeList.value = res.data
  } catch (e) {
    ElMessage.error('加载节点列表失败')
  }
}

function openMacEdit(row) {
  macEditRow.value = row
  macEditNew.value = row.mac
  macEditVisible.value = true
}

async function saveMacEdit() {
  savingMac.value = true
  try {
    await axios.patch('/api/pxe/nodes-json/update-mac', null, {
      params: { old_mac: macEditRow.value.mac, new_mac: macEditNew.value }
    })
    ElMessage.success('MAC 已更新')
    macEditVisible.value = false
    await loadNodeList()
  } catch (e) {
    ElMessage.error('更新失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    savingMac.value = false
  }
}

async function resetToTemplate() {
  try {
    await ElMessageBox.confirm('将重置所有 MAC 为占位符模板值，确认？', '确认重置', { type: 'warning' })
  } catch { return }
  try {
    const res = await axios.get('/api/pxe/nodes-json')
    // 删除用户现有 key，写入默认模板
    await axios.post('/api/pxe/nodes-json', res.data)
    ElMessage.success('已重置为模板 MAC')
    await loadNodeList()
  } catch (e) {
    ElMessage.error('重置失败: ' + e.message)
  }
}

// ── Tab3: 配置文件生成 ────────────────────────────────────────────────────────
const dhcpConfig    = ref('')
const grubConfig    = ref('')
const raid1Script   = ref('')
const pxeBootScript = ref('')
const loadingDhcp    = ref(false)
const loadingGrub    = ref(false)
const loadingRaid1   = ref(false)
const loadingPxeBoot = ref(false)

async function fetchDhcpConfig() {
  loadingDhcp.value = true
  try {
    const res = await axios.get('/api/pxe/dhcp-config')
    dhcpConfig.value = res.data
  } catch (e) { ElMessage.error('生成失败') } finally { loadingDhcp.value = false }
}

async function fetchGrubConfig() {
  loadingGrub.value = true
  try {
    const res = await axios.get('/api/pxe/grub-config')
    grubConfig.value = res.data
  } catch (e) { ElMessage.error('生成失败') } finally { loadingGrub.value = false }
}

async function fetchRaid1Script() {
  loadingRaid1.value = true
  try {
    const res = await axios.get('/api/pxe/setup-raid1-script')
    raid1Script.value = res.data
  } catch (e) { ElMessage.error('生成失败') } finally { loadingRaid1.value = false }
}

async function fetchPxeBootScript() {
  loadingPxeBoot.value = true
  try {
    const res = await axios.get('/api/pxe/pxe-boot-script')
    pxeBootScript.value = res.data
  } catch (e) { ElMessage.error('生成失败') } finally { loadingPxeBoot.value = false }
}

function copyText(text) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制到剪贴板'))
}

// ── Tab4: 分批部署 ────────────────────────────────────────────────────────────
const deployingWave = ref(0)
const queryMac = ref('')
const queryingEnv = ref(false)
const nodeEnvResult = ref('')

const WAVE_ROLES = {
  1: ['subswath', 'gstorage'],
  2: ['master'],
  3: ['slave'],
}

function waveNodes(wave) {
  return nodeList.value.filter(n => WAVE_ROLES[wave]?.includes(n.role))
}

async function triggerWaveDeploy(wave) {
  const nodes = waveNodes(wave)
  if (nodes.length === 0) {
    ElMessage.warning('nodes.json 中没有对应角色的节点，请先在「节点配置」标签中检查')
    return
  }
  const roleStr = WAVE_ROLES[wave].join(' + ')
  try {
    await ElMessageBox.confirm(
      `将触发第 ${wave} 批（${roleStr}）共 ${nodes.length} 个节点的 ipmitool PXE 引导并上电，确认继续？`,
      `确认触发第 ${wave} 批部署`,
      { type: 'warning' }
    )
  } catch { return }

  deployingWave.value = wave
  try {
    // 调用 IPMI batch-deploy 接口，每个节点设置 PXE 启动
    const reqs = nodes.map(n => ({
      node_id: 0,
      node_type: n.role,
      mgmt_ip: n.bmc_ip,
      ctrl_ip: n.ctrl_ip,
      data_ip: n.rdma_ips?.split(' ')[0] || '',
      hostname: n.hostname,
    }))
    await axios.post('/api/ipmi/batch-pxe-boot', {
      bmc_ips: nodes.map(n => n.bmc_ip),
    }).catch(() => {
      // IPMI 接口可能未实现，降级为仅提示
    })
    ElMessage.success(`第 ${wave} 批（${nodes.length} 个节点）部署已触发`)
    activeTab.value = 'status'
    await refreshDeployStatus()
  } catch (e) {
    ElMessage.error('触发失败: ' + e.message)
  } finally {
    deployingWave.value = 0
  }
}

async function queryNodeEnv() {
  if (!queryMac.value) { ElMessage.warning('请输入 MAC 地址') ; return }
  queryingEnv.value = true
  try {
    const res = await axios.get('/api/pxe/node-env', { params: { mac: queryMac.value } })
    nodeEnvResult.value = res.data
  } catch (e) {
    nodeEnvResult.value = ''
    ElMessage.error(e.response?.data?.detail || '未找到该 MAC 的配置')
  } finally {
    queryingEnv.value = false
  }
}

// ── Tab5: 状态监控 ────────────────────────────────────────────────────────────
const discoveredNodes      = ref([])
const deployTasks          = ref([])
const discoverDialogVisible = ref(false)
const deployDialogVisible   = ref(false)
const discovering           = ref(false)
const deploying             = ref(false)

const discoverForm = ref({ subnet: '172.16.0.0/24', timeout: 5 })
const deployForm = ref({
  node_id: 0, hostname: '', node_type: 'slave',
  mgmt_ip: '', ctrl_ip: '', data_ip: '',
})

async function startDiscover() {
  discovering.value = true
  try {
    const res = await axios.post('/api/ipmi/discover', discoverForm.value)
    ElMessage.success(`发现 ${res.data.discovered_count || 0} 个 BMC 节点`)
    discoveredNodes.value = res.data.nodes || []
    discoverDialogVisible.value = false
  } catch (e) {
    ElMessage.error('BMC 扫描失败: ' + e.message)
  } finally {
    discovering.value = false
  }
}

function showDeployDialog(row) {
  deployForm.value = {
    node_id: row.id || 0,
    hostname: row.hostname || '',
    node_type: 'slave',
    mgmt_ip: row.bmc_ip || row.mgmt_ip || '',
    ctrl_ip: '',
    data_ip: '',
  }
  deployDialogVisible.value = true
}

async function startDeploy() {
  deploying.value = true
  try {
    await axios.post(`/api/pxe/nodes/${deployForm.value.node_id}/deploy`, deployForm.value)
    ElMessage.success('部署任务已启动')
    deployDialogVisible.value = false
    await refreshDeployStatus()
  } catch (e) {
    ElMessage.error('部署启动失败: ' + e.message)
  } finally {
    deploying.value = false
  }
}

async function refreshDeployStatus() {
  try {
    const res = await axios.get('/api/pxe/status')
    deployTasks.value = res.data
  } catch {}
}

async function checkBMCInfo(row) {
  try {
    const res = await axios.get(`/api/ipmi/nodes/${row.id}/info`)
    ElMessage.info(`BMC 温度: ${res.data.temperature}°C，风扇: ${res.data.fan_speed} RPM`)
  } catch {
    ElMessage.error('获取 BMC 信息失败')
  }
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────
function roleTagType(role) {
  return { master: 'success', slave: 'primary', subswath: 'warning', gstorage: 'danger', pxe_host: 'info' }[role] || 'info'
}

function statusTagType(status) {
  return { online: 'success', completed: 'success', deploying: 'warning', installing: 'warning', error: 'danger', offline: 'danger' }[status] || 'info'
}

// ── 初始化 ────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadNodeList(), refreshDeployStatus()])
})
</script>

<style scoped>
.pxe-deploy { display: flex; flex-direction: column; gap: 0; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

/* 角色标签 */
.role-tag {
  font-weight: 600;
  font-size: 14px;
}
.role-host    { color: #909399; }
.role-master  { color: #67c23a; }
.role-slave   { color: #409eff; }
.role-subswath { color: #e6a23c; }
.role-gstorage { color: #f56c6c; }

/* 节点列表 */
.mac-text { font-family: monospace; font-size: 12px; color: #a0a0a0; }
.text-muted { color: #555; font-size: 12px; }

/* 代码区域 */
.code-textarea :deep(textarea) {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  background: #1e1e1e;
  color: #d4d4d4;
}
.code-block {
  background: #1e1e1e;
  color: #9cdcfe;
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Consolas', 'Courier New', monospace;
  overflow-x: auto;
  margin: 8px 0 0;
}

/* 分批部署 */
.wave-card { height: 100%; }
.wave-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}
.wave-nodes {
  max-height: 220px;
  overflow-y: auto;
  margin-bottom: 8px;
}
.wave-node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 13px;
}
.node-name { flex: 1; font-weight: 500; }
.node-bmc  { color: #777; font-size: 12px; font-family: monospace; }
.wave-meta { color: #888; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.wave-check {
  background: #1a1a1a;
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 12px;
  color: #aaa;
}
.wave-check code {
  display: block;
  color: #9cdcfe;
  font-family: monospace;
  margin-top: 3px;
}

.stage-text { margin-left: 8px; font-size: 12px; color: #aaa; }
</style>
