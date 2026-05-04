# 集群配置、管理、诊断系统

鲲鹏 ARM64 + HNS 网卡，22 节点三平面物理隔离集群的配置、管理与诊断系统。

## 网络架构

三平面物理隔离，各平面由独立交换机承载：

| 平面 | 带宽 | 子网 | 用途 |
|------|------|------|------|
| 管理面 | GE | `172.16.0.0/24` | BMC/IPMI 带外管理 |
| 控制面 | 10GE | `172.16.3.0/24` | SSH / PXE 部署 / 心跳 |
| 数据面-DPDK1 | 100GE | `200.1.1.0/24` | Master eno2 接收 |
| 数据面-DPDK2 | 100GE | `200.1.2.0/24` | Master eno3 接收 |
| 数据面-RDMA1 | 100GE | `100.1.1.0/24` | Master/Slave/SubSwath RDMA |
| 数据面-RDMA2 | 100GE | `100.1.2.0/24` | Master/SubSwath/GStorage RDMA |

## 集群规模与角色

| 角色 | 数量 | 主机名规则 | 控制面 IP | 说明 |
|------|------|-----------|-----------|------|
| PXE Host | 1 | host-server | 172.16.3.10 | DHCP/TFTP/HTTP/API，100GE 上行至 10G 交换机 |
| Master | 6 | master-01~06 | 172.16.3.11~16 | DPDK 接收 + RDMA 计算控制，100G×4 |
| Slave | 12 | slave-01~12 | 172.16.3.51~62 | RDMA 计算 + NFS 客户端，100G×1 |
| SubSwath | 2 | subswath-01~02 | 172.16.3.170~171 | NFS Server（4×7.68T NVMe RAID10），100G×2 |
| GStorage | 1 | gstorage-01 | 172.16.3.172 | NFS Server（机械盘硬件 RAID50），100G×1 |

## 功能模块

### 1. PXE 自动化部署（v2）

- **IP 规划**：六子网固定方案，一键生成全角色 IP 表
- **nodes.json 管理**：22 节点 MAC→配置映射，支持在线编辑 MAC 地址
- **配置生成**：dhcpd.conf、grub.cfg（aarch64 UEFI）、RAID1 初始化脚本、PXE 启动脚本
- **分批部署**：第一批（SubSwath+GStorage）→ 第二批（Master）→ 第三批（Slave）
- **node-env API**：`GET /api/pxe/node-env?mac=<MAC>` 供 firstboot detect.sh 获取差异化配置

### 2. 集群管理

- 三平面网络状态监控
- BMC/IPMI 远程管理（ipmitool / Redfish）
- 定时巡检任务
- 告警规则引擎

### 3. 故障诊断

- 三平面拓扑可视化（D3.js）
- 日志收集与分析
- 故障点定位
- 诊断脚本库（业务诊断 + 硬件诊断）

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Swagger 文档: http://localhost:8000/docs
```

启动时自动完成：数据库初始化、列迁移、种子数据写入、`pxe_data/nodes.json` 预生成。

### 前端

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## 项目结构

```
clustermanager/
├── backend/
│   ├── api/
│   │   ├── pxe.py          # PXE 部署 API（v2）
│   │   ├── ipmi.py         # BMC/IPMI 管理
│   │   ├── nodes.py        # 节点 CRUD
│   │   ├── network.py      # 网络拓扑
│   │   ├── alerts.py       # 告警
│   │   ├── diagnose.py     # 故障诊断
│   │   └── patrol.py       # 巡检
│   ├── services/
│   │   └── pxe_service.py  # PXE 服务 v2（nodes.json / DHCP / GRUB 生成）
│   ├── models/
│   │   ├── node.py         # ORM 模型
│   │   └── seed.py         # 演示数据
│   ├── pxe_data/
│   │   └── nodes.json      # 节点配置清单（自动生成，需填入实际 MAC）
│   └── main.py             # 入口 + 迁移
└── frontend/src/
    └── views/
        └── PXEDeploy.vue   # PXE 部署页面（5 标签页）
```

## API 速查

| 接口 | 说明 |
|------|------|
| `POST /api/pxe/network-plan` | v2 六子网 IP 规划 |
| `GET  /api/pxe/nodes-json` | 获取 nodes.json |
| `POST /api/pxe/nodes-json` | 更新 nodes.json |
| `GET  /api/pxe/nodes-json/node-list` | 节点表格列表 |
| `PATCH /api/pxe/nodes-json/update-mac` | 替换节点 MAC |
| `GET  /api/pxe/node-env?mac=<MAC>` | firstboot 环境变量（纯文本） |
| `GET  /api/pxe/dhcp-config` | 生成 dhcpd.conf |
| `GET  /api/pxe/grub-config` | 生成 grub.cfg |
| `GET  /api/pxe/setup-raid1-script` | 生成 RAID1 初始化脚本 |
| `GET  /api/pxe/pxe-boot-script` | 生成 PXE 启动脚本 |

## 生产部署（OpenEuler ARM → Windows 浏览器访问）

### 架构

```
OpenEuler aarch64 服务器
  └── /opt/cluster-manager/
        ├── cluster-manager   ← PyInstaller 单目录可执行
        ├── static/           ← Vue 构建产物（由 FastAPI 直接提供）
        ├── pxe_data/         ← nodes.json（首次运行自动生成）
        └── cluster_manager.db← SQLite 数据库（首次运行自动创建）

Windows 桌面
  └── 浏览器访问 http://<arm-ip>:8000
```

### 一键构建（在 ARM 机器上执行）

```bash
# 1. 克隆代码到 ARM 机器
git clone <repo> clustermanager && cd clustermanager

# 2. 构建（自动完成：前端 npm build → PyInstaller 打包）
chmod +x build.sh
./build.sh

# 3. 部署产物
cp -r backend/dist/cluster-manager /opt/cluster-manager

# 4a. 直接运行
/opt/cluster-manager/start.sh

# 4b. 或注册 systemd 服务（开机自启）
cp cluster-manager.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now cluster-manager
```

### 也可以在 x86 机器上交叉构建再传到 ARM（推荐 ARM 本地构建）

### 端口说明

| 场景 | 地址 |
|------|------|
| Windows 访问前端 | `http://<arm-ip>:8000` |
| API Swagger 文档 | `http://<arm-ip>:8000/docs` |
| 修改端口 | 设置环境变量 `CLUSTER_MANAGER_PORT=8080` |

---

## 变更记录

### 2026-05-05 — 生产部署打包支持（PyInstaller + 前端内嵌）

**背景**：将系统部署到 OpenEuler ARM 服务器，Windows 桌面通过浏览器访问。

**涉及文件**：
- `backend/config.py` — **新建**：统一路径解析，兼容开发模式和 PyInstaller 打包运行
- `backend/models/node.py` — DATABASE_URL 改用 `config.DATABASE_PATH`，路径跟随可执行文件
- `backend/services/pxe_service.py` — nodes.json 路径改用 `config.PXE_DATA_DIR`
- `backend/main.py` — 新增 Vue 静态文件挂载（SPA 路由 catch-all）+ `__main__` 入口
- `frontend/vite.config.js` — `build.outDir` 设为 `../backend/static`
- `backend/cluster_manager.spec` — **新建**：PyInstaller onedir 打包配置
- `build.sh` — **新建**：一键构建脚本（前端 build + PyInstaller）
- `cluster-manager.service` — **新建**：systemd 自启服务模板

**部署流程**：
1. `./build.sh` → 输出 `backend/dist/cluster-manager/`
2. 复制到 ARM 服务器 `/opt/cluster-manager/`
3. `./start.sh` 或 `systemctl enable --now cluster-manager`
4. Windows 浏览器访问 `http://<arm-ip>:8000`

---

### 2026-05-05 — PXE 模块 v2（对应部署方案 v2）

**背景**：依据新 SVG 组网图重新设计，从旧方案（23 节点、192.168.x.x）迁移到新方案（22 节点、172.16.x.x 三平面物理隔离）。

**涉及文件**：
- `backend/services/pxe_service.py` — 完整重写
- `backend/api/pxe.py` — 新增 v2 端点
- `backend/main.py` — 补充迁移列
- `backend/models/seed.py` — 更新默认 PXE 配置子网
- `frontend/src/views/PXEDeploy.vue` — 重构为 5 标签页

**主要变更**：

| 维度 | 旧值（v1） | 新值（v2） |
|------|-----------|-----------|
| 集群规模 | Master×7 等 | Master×6 + Slave×12 + SubSwath×2 + GStorage×1 |
| 管理面子网 | `192.168.x.x` | `172.16.0.0/24` |
| 控制面子网 | `10.0.0.x` | `172.16.3.0/24` |
| 数据面 | 单子网 | DPDK-1/2 + RDMA-1/2 四个 100GE 子网 |
| 系统盘 | 各角色不同 | 全角色统一 2×960G 硬件 RAID1 → `/dev/sda` |
| SubSwath 数据盘 | 无 | 4×7.68T NVMe 软件 RAID10（mdadm） |
| GStorage 数据盘 | 无 | 机械盘硬件 RAID50（BMC 预配置） |
| 部署方式 | Kickstart | base.tar.zst + firstboot 差异化注入 |
| 引导配置 | pxelinux | grubaa64.efi（aarch64 UEFI） |
| 节点配置载体 | 数据库字段 | `pxe_data/nodes.json`（MAC→配置映射） |

**新增后端端点**（均挂载在 `/api/pxe/`）：

- `POST /network-plan` — 六子网 IP 规划（支持四角色数量参数）
- `GET/POST /nodes-json` — nodes.json 读写
- `GET /nodes-json/node-list` — 前端表格展示用节点列表
- `PATCH /nodes-json/update-mac` — 在线替换节点 MAC 地址
- `GET /node-env?mac=` — 返回 shell 变量文本，firstboot detect.sh 调用
- `GET /dhcp-config` — 生成 dhcpd.conf（含 ARM64 UEFI class 规则）
- `GET /grub-config` — 生成 grub.cfg（`pxe_server=172.16.3.10`）
- `GET /setup-raid1-script` — 批量 Redfish 建 RAID1 脚本
- `GET /pxe-boot-script` — 批量 ipmitool PXE 启动脚本

**前端重构**（`PXEDeploy.vue`）：

| 标签页 | 内容 |
|--------|------|
| IP 规划 | v2 六子网规划，四角色分表，一键应用到 nodes.json |
| 节点配置 | 22 节点表格，MAC 在线编辑（替换占位符） |
| 配置生成 | dhcpd.conf / grub.cfg / RAID1 脚本 / PXE 脚本，一键生成 + 复制 |
| 分批部署 | 三批卡片（存储→Master→Slave），含耗时估计和就绪验证命令 |
| 状态监控 | BMC 扫描、单节点部署、部署任务进度 |
