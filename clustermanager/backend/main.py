"""
Cluster Manager - FastAPI 主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text

from models.node import init_db, engine
from models.seed import seed_demo_data
from api import nodes, pxe, ipmi, network, alerts, diagnose, patrol


def _run_migrations():
    """简单列迁移：为已存在的表添加新列"""
    migrations = [
        "ALTER TABLE diag_scripts ADD COLUMN script_tab VARCHAR(20) DEFAULT 'hardware'",
        # v2: PXE 节点新增字段
        "ALTER TABLE nodes ADD COLUMN rdma_nics VARCHAR(100)",
        "ALTER TABLE nodes ADD COLUMN rdma_ips  VARCHAR(200)",
        "ALTER TABLE nodes ADD COLUMN dpdk_nics VARCHAR(100)",
        "ALTER TABLE nodes ADD COLUMN dpdk_ips  VARCHAR(200)",
        "ALTER TABLE nodes ADD COLUMN hugepages_1g INTEGER DEFAULT 0",
        "ALTER TABLE nodes ADD COLUMN system_disk VARCHAR(50)",
        "ALTER TABLE nodes ADD COLUMN data_disks  VARCHAR(200)",
        "ALTER TABLE nodes ADD COLUMN data_raid_level VARCHAR(20)",
        "ALTER TABLE nodes ADD COLUMN nfs_mounts  TEXT",
        "ALTER TABLE nodes ADD COLUMN nfs_export_ip VARCHAR(45)",
        "ALTER TABLE nodes ADD COLUMN nfs_exports  VARCHAR(200)",
        "ALTER TABLE nodes ADD COLUMN extra_pkgs   VARCHAR(200)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # 列已存在则忽略

    # 确保 nodes.json 存储目录存在，并预生成默认配置
    from services.pxe_service import pxe_service_v2
    pxe_service_v2.read_nodes_json()  # 首次调用会写入默认模板


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _run_migrations()
    seed_demo_data()
    yield


app = FastAPI(
    title="Cluster Manager",
    description="集群配置、管理、诊断系统 - 支持三平面网络架构",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(nodes.router, prefix="/api/nodes", tags=["节点管理"])
app.include_router(pxe.router, prefix="/api/pxe", tags=["PXE部署"])
app.include_router(ipmi.router, prefix="/api/ipmi", tags=["IPMI/BMC"])
app.include_router(network.router, prefix="/api/network", tags=["网络配置"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["告警管理"])
app.include_router(diagnose.router, prefix="/api/diagnose", tags=["故障诊断"])
app.include_router(patrol.router, prefix="/api/patrol", tags=["巡检管理"])


@app.get("/")
async def root():
    return {"message": "Cluster Manager API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}