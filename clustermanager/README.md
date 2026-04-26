# 集群配置、管理、诊断系统

支持三平面网络架构的集群管理系统

## 网络架构

- **管理面 (GE口)**: IPMI/BMC管理，PXE部署，运维管理
- **控制面 (10GE)**: 小数据量传输，心跳检测，配置同步
- **数据面 (100GE)**: 高速数据传输
  - 前段: 传感器 → Master (DPDK协议)
  - 后段: Master → Slave (RDMA协议)

## 功能模块

### 1. PXE自动化部署
- BMC节点发现与注册
- 三平面网络IP规划
- Kickstart模板生成
- 批量部署管理

### 2. 集群管理
- 三平面网络状态监控
- BMC/IPMI远程管理
- 定时巡检任务
- 告警规则引擎

### 3. 故障诊断
- 三平面拓扑可视化 (D3.js)
- 日志收集与分析
- 故障点定位
- 诊断建议生成

## 快速启动

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### PXE服务配置

```bash
cd pxe
chmod +x pxe_setup.sh
sudo ./pxe_setup.sh
```

## API文档

启动后端后访问: http://localhost:8000/docs

## 项目结构

```
clustermanager/
├── backend/           # FastAPI后端
│   ├── api/           # API路由
│   ├── services/      # 业务服务
│   ├── models/        # 数据模型
│   └── main.py        # 入口文件
├── frontend/          # Vue 3前端
│   └── src/
│       ├── views/     # 页面组件
│       └── router/    # 路由配置
├── pxe/               # PXE部署脚本
│   ├── kickstart/     # Kickstart模板
│   └ scripts/         # DPDK/RDMA配置脚本
└── agent/             # 监控Agent(待实现)
```

## 数据库

使用 SQLite (可切换到 PostgreSQL)

初始化数据库会在启动时自动完成