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

> **PyInstaller 不支持跨平台编译**（无法在 Windows x86 上直接生成 Linux ARM 二进制）。  
> 提供两条路径，按场景选择：

### 方案对比

| | 部署包方案 | Docker 方案 |
|--|-----------|------------|
| 前提 | Node.js（Windows）+ Python（ARM） | Docker Desktop（Windows）+ Docker（ARM） |
| 构建位置 | 前端在 Windows，Python 在 ARM | 全部在 Windows（QEMU 模拟） |
| 产物 | ZIP 包 + Python 源码 | 容器镜像 |
| 隔离性 | venv 虚拟环境 | 容器级隔离 |
| 推荐场景 | 快速部署，无 Docker 环境 | 标准化分发，多服务器部署 |

---

### 方案一：部署包（推荐，无需 Docker）

```
Windows                              ARM 服务器
─────────────────────────────────    ──────────────────────────────────────
1. build.bat                         3. 解压 + deploy.sh
   npm run build  ──────────┐           unzip cluster-manager-deploy.zip
   打包成 ZIP     ──────────┤           ./deploy.sh
                            │           → pip install requirements.txt
                  scp ──────┘           → systemd 服务注册
2. cluster-manager-deploy.zip        4. 浏览器访问 http://<arm-ip>:8000
```

**Windows 端（构建）**：
```bat
build.bat
:: 产物: cluster-manager-deploy.zip
```

**传输到 ARM**：
```bash
scp cluster-manager-deploy.zip root@<arm-ip>:/opt/
```

**ARM 端（部署）**：
```bash
cd /opt
unzip cluster-manager-deploy.zip -d cluster-manager
cd cluster-manager
chmod +x deploy.sh
./deploy.sh
# → 自动 pip install + 注册 systemd 开机自启
```

---

### 方案二：Docker 多平台构建

**前提**：Windows 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，并启用 QEMU 多平台支持。

**Windows 端（构建 ARM64 镜像）**：
```powershell
# 首次使用需创建 buildx builder
docker buildx create --use --name arm-builder

# 构建 ARM64 镜像并推送（替换 your-registry）
docker buildx build --platform linux/arm64 `
    -t your-registry/cluster-manager:latest `
    --push .

# 或直接保存为 tar 传输
docker buildx build --platform linux/arm64 `
    -t cluster-manager:latest `
    -o type=docker,dest=cluster-manager-arm64.tar .
```

**ARM 端（运行）**：
```bash
# 方式 A：从镜像仓库拉取
docker compose up -d

# 方式 B：从 tar 导入
docker load < cluster-manager-arm64.tar
docker compose up -d
```

**数据持久化**（docker-compose.yml 已配置 volume `cluster_data`）：
```
/var/lib/docker/volumes/cluster_data/_data/
├── cluster_manager.db   ← SQLite 数据库
├── pxe_data/            ← nodes.json 等
└── static/              ← 已内嵌镜像，无需挂载
```

---

### 方案三：全部在 ARM 构建机上构建（推荐用于生产交付）

```bash
# 构建机（有 Node.js + Python + pip）
chmod +x build.sh && ./build.sh
# 产物: cluster-manager-linux-arm64.tar.gz（自包含，生产机无需安装任何依赖）

# 生产机（干净的 OpenEuler ARM，什么都不需要装）
scp cluster-manager-linux-arm64.tar.gz root@<prod-ip>:/opt/
ssh root@<prod-ip> 'cd /opt && tar -xzf cluster-manager-linux-arm64.tar.gz'

# 直接运行
ssh root@<prod-ip> '/opt/cluster-manager/start.sh'

# 或注册为开机自启服务
ssh root@<prod-ip> 'cd /opt/cluster-manager && sudo ./install-service.sh'
```

**产物目录结构**：
```
cluster-manager-linux-arm64.tar.gz
└── cluster-manager/
    ├── cluster-manager       ← 可执行文件（含 Python 运行时 + 全部依赖）
    ├── _internal/            ← PyInstaller 依赖库（自动加载，无需关心）
    ├── static/               ← Vue 前端（FastAPI 直接提供服务）
    ├── start.sh              ← 启动脚本
    └── install-service.sh    ← systemd 自启注册脚本
```

---

### 端口与环境变量

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `CLUSTER_MANAGER_HOST` | `0.0.0.0` | 监听地址 |
| `CLUSTER_MANAGER_PORT` | `8000` | 监听端口 |
| `CLUSTER_MANAGER_DATA` | 程序目录 | 数据目录（DB + pxe_data），Docker 必须设置 |

| 访问地址 | 说明 |
|----------|------|
| `http://<arm-ip>:8000` | 前端界面 |
| `http://<arm-ip>:8000/docs` | API Swagger 文档 |

---

## 变更记录

### 2026-05-05 — 节点管理页支持手动新增/编辑/删除节点

**背景**：已完成 PXE 部署的集群可直接通过 UI 手动录入节点信息，无需再走 PXE 流程，实现组网图和后续监控功能。

**涉及文件**：
- `backend/api/nodes.py` — `NodeCreate` 补充 `os_version / cpu_cores / memory_gb / disk_gb`；`NodeUpdate` 补全所有 MAC 字段和 `data_protocol`（原缺失）
- `frontend/src/views/Nodes.vue` — 重写，新增以下能力：

**前端变更详情**：

| 变更点 | 说明 |
|--------|------|
| 新增节点按钮 | 表头右侧新增"新增节点"按钮，打开空白表单 |
| 编辑/删除按钮 | 操作列新增"编辑"（主色）和"删除"（红色）按钮，删除带二次确认弹窗 |
| 新增/编辑对话框 | 700px 宽，按五个区块组织：基本信息 / 管理面 / 控制面 / 数据面 / 硬件信息 |
| 节点类型扩展 | 筛选下拉和表单选项新增 SubSwath、GStorage、Sensor |
| 角色副标题 | 类型列在 Tag 下方显示 `role` 字段内容 |
| 类型色彩区分 | Master=红、Slave=蓝、SubSwath=橙、GStorage=绿 |
| 空值处理 | 保存时空字符串自动转 `null`，避免覆盖已有数据 |

---

### 2026-05-05 — build.sh 改为生产自包含包（无需在生产机安装依赖）

**背景**：生产机应该零依赖，直接解压运行，不允许执行 pip install。

**涉及文件**：
- `build.sh` — 重写：PyInstaller 打包 + 手动复制 `static/` + 输出 `tar.gz`
- `backend/cluster_manager.spec` — 移除 `datas` 中的 `static/`（改为 build.sh 手动复制，避免 `sys._MEIPASS` 路径混淆）

**生产机部署步骤**（三行命令）：
```bash
tar -xzf cluster-manager-linux-arm64.tar.gz
./cluster-manager/start.sh          # 直接运行
# 或
./cluster-manager/install-service.sh # 注册开机自启
```

---

### 2026-05-05 — 跨平台部署支持（Windows 构建 → Linux ARM 部署）

**背景**：PyInstaller 不支持交叉编译，需提供可在 Windows 上构建、Linux ARM 上部署的方案。

**涉及文件**：
- `backend/config.py` — 新增 `CLUSTER_MANAGER_DATA` 环境变量支持（Docker 数据目录）
- `build.bat` — **新建**：Windows 一键构建脚本（前端 build + 打包 ZIP）
- `deploy.sh` — **新建**：Linux ARM 部署脚本（pip install + systemd 注册）
- `Dockerfile` — **新建**：多阶段构建，支持 `linux/arm64` 和 `linux/amd64`
- `docker-compose.yml` — **新建**：Docker 部署配置，volume 持久化数据
- `.dockerignore` — **新建**：排除 node_modules 等大文件

**三种部署路径**：
1. **Windows build.bat → ZIP → ARM deploy.sh**（推荐，无需 Docker）
2. **Windows docker buildx → ARM docker compose**（标准化，需 Docker）
3. **ARM 本地 build.sh**（最简单，全部在 ARM 上完成）

---

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
