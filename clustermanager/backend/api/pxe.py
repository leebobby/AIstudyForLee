"""
PXE 部署 API v2 - 鲲鹏集群 22 节点三平面部署
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.node import Node, PXEConfig, get_db
from pydantic import BaseModel
from services.pxe_service import pxe_service_v2


router = APIRouter()


# ── Pydantic 模型 ─────────────────────────────────────────────────────────────

class PXEConfigCreate(BaseModel):
    name: str
    mgmt_subnet: str = "172.16.0.0/24"
    ctrl_subnet: str = "172.16.3.0/24"
    data_subnet: str = "100.1.0.0/16"
    mgmt_gateway: Optional[str] = None
    ctrl_gateway: Optional[str] = "172.16.3.1"
    data_gateway: Optional[str] = None
    dns_servers: Optional[str] = "172.16.3.10"


class PXEConfigResponse(BaseModel):
    id: int
    name: str
    mgmt_subnet: str
    ctrl_subnet: str
    data_subnet: str
    mgmt_gateway: Optional[str]
    ctrl_gateway: Optional[str]
    data_gateway: Optional[str]
    dns_servers: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NetworkPlanRequest(BaseModel):
    """v2 IP 规划请求（固定六子网，仅需确认各角色数量）"""
    master_count: int = 6
    slave_count: int = 12
    subswath_count: int = 2
    gstorage_count: int = 1


class DeployRequest(BaseModel):
    node_id: int
    node_type: str  # master / slave / subswath / gstorage
    mgmt_ip: str
    ctrl_ip: str
    data_ip: str
    hostname: Optional[str] = None


class DeployStatus(BaseModel):
    node_id: int
    hostname: str
    status: str
    stage: str
    progress: int
    message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime] = None


# ── 既有端点（保持兼容）──────────────────────────────────────────────────────

@router.get("/configs", response_model=List[PXEConfigResponse])
def get_pxe_configs(db: Session = Depends(get_db)):
    """获取所有 PXE 配置"""
    return db.query(PXEConfig).all()


@router.post("/config", response_model=PXEConfigResponse)
def create_pxe_config(config: PXEConfigCreate, db: Session = Depends(get_db)):
    """创建 PXE 部署配置"""
    db_config = PXEConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


@router.get("/status")
def get_deploy_status(db: Session = Depends(get_db)):
    """获取正在部署的节点状态"""
    nodes = db.query(Node).filter(
        Node.status.in_(["deploying", "installing", "configuring"])
    ).all()
    return [
        DeployStatus(
            node_id=node.id,
            hostname=node.hostname,
            status=node.status,
            stage=node.status,
            progress=50,
            message="正在部署...",
            started_at=node.created_at,
        )
        for node in nodes
    ]


@router.post("/nodes/{node_id}/deploy")
async def deploy_node(
    node_id: int,
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """部署指定节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    node.hostname = request.hostname or node.hostname
    node.node_type = request.node_type
    node.mgmt_ip = request.mgmt_ip
    node.ctrl_ip = request.ctrl_ip
    node.data_ip = request.data_ip
    node.data_protocol = "DPDK" if request.node_type == "master" else "RDMA"
    node.status = "deploying"
    db.commit()

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "status": "deploying",
        "message": "部署任务已启动，请等待完成",
        "network_config": {
            "management_bmc": request.mgmt_ip,
            "control_10ge": request.ctrl_ip,
            "data_100ge": request.data_ip,
        },
    }


@router.post("/batch-deploy")
async def batch_deploy_nodes(
    nodes: List[DeployRequest],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """批量部署多个节点"""
    results = []
    for req in nodes:
        node = db.query(Node).filter(Node.id == req.node_id).first()
        if node:
            node.hostname = req.hostname or node.hostname
            node.node_type = req.node_type
            node.mgmt_ip = req.mgmt_ip
            node.ctrl_ip = req.ctrl_ip
            node.data_ip = req.data_ip
            node.data_protocol = "DPDK" if req.node_type == "master" else "RDMA"
            node.status = "deploying"
            results.append({
                "node_id": req.node_id,
                "hostname": node.hostname,
                "status": "deploying",
            })
    db.commit()
    return {"message": "批量部署已启动", "total_nodes": len(nodes), "results": results}


@router.get("/kickstart/{node_type}")
def get_kickstart_template(node_type: str):
    """v2 改用 firstboot 差异化注入，此接口返回各角色特性说明"""
    role_features = {
        "master":   ["100G×4 DPDK+RDMA", "大页内存 100×1G", "无数据盘"],
        "slave":    ["100G×1 RDMA 计算", "NFS 客户端三路挂载"],
        "subswath": ["100G×2 双平面独立 IP", "4×7.68T NVMe 软件 RAID10", "NFS Server 导出"],
        "gstorage": ["100G×1 RDMA-2", "硬件 RAID50（BMC 预配置）", "NFS Server 归档"],
    }
    if node_type not in role_features:
        raise HTTPException(status_code=400, detail="node_type 必须为 master/slave/subswath/gstorage")
    return {
        "node_type": node_type,
        "deployment_method": "firstboot 差异化注入（base.tar.zst + nodes.json）",
        "features": role_features[node_type],
    }


# ── v2 新增端点 ───────────────────────────────────────────────────────────────

@router.post("/network-plan")
def plan_network_ips(request: NetworkPlanRequest):
    """
    v2 六子网 IP 规划
    管理面 172.16.0.0/24 | 控制面 172.16.3.0/24 |
    DPDK-1 200.1.1.0/24 | DPDK-2 200.1.2.0/24 |
    RDMA-1 100.1.1.0/24 | RDMA-2 100.1.2.0/24
    """
    return pxe_service_v2.generate_ip_plan(
        master_count=request.master_count,
        slave_count=request.slave_count,
        subswath_count=request.subswath_count,
        gstorage_count=request.gstorage_count,
    )


@router.get("/nodes-json")
def get_nodes_json():
    """获取当前 nodes.json（节点配置清单）"""
    return pxe_service_v2.read_nodes_json()


@router.post("/nodes-json")
def update_nodes_json(data: Dict[str, Any]):
    """更新 nodes.json（保存 MAC→配置 映射）"""
    pxe_service_v2.write_nodes_json(data)
    node_count = sum(1 for k in data if not k.startswith("_"))
    return {"message": "nodes.json 已更新", "node_count": node_count}


@router.get("/nodes-json/node-list")
def get_node_list():
    """获取节点列表（供前端表格展示）"""
    return pxe_service_v2.get_node_list()


@router.patch("/nodes-json/update-mac")
def update_node_mac(old_mac: str, new_mac: str):
    """更新节点 MAC 地址（用实际硬件 MAC 替换占位符）"""
    data = pxe_service_v2.read_nodes_json()
    old_mac = old_mac.lower()
    new_mac = new_mac.lower()
    if old_mac not in data:
        raise HTTPException(status_code=404, detail=f"MAC {old_mac} 不在 nodes.json 中")
    if old_mac == new_mac:
        return {"message": "MAC 未变化"}
    data[new_mac] = data.pop(old_mac)
    pxe_service_v2.write_nodes_json(data)
    return {"message": f"MAC 已从 {old_mac} 更新为 {new_mac}"}


@router.get("/node-env", response_class=PlainTextResponse)
def get_node_env(mac: str = Query(..., description="节点 10GE 控制面网卡 MAC 地址")):
    """
    返回节点 shell 环境变量文本（firstboot detect.sh 使用）。

    用法（在节点上执行）：
        curl -sf http://172.16.3.10:8000/api/pxe/node-env?mac=aa:bb:cc:11:00:01 \\
             -o /etc/node-role/env
    """
    env_text = pxe_service_v2.get_node_env_vars(mac.lower())
    if env_text is None:
        raise HTTPException(status_code=404, detail=f"MAC {mac} 未在 nodes.json 中配置")
    return env_text


@router.get("/dhcp-config", response_class=PlainTextResponse)
def get_dhcp_config():
    """生成 dhcpd.conf（基于当前 nodes.json，监听控制面 172.16.3.0/24）"""
    return pxe_service_v2.generate_dhcpd_conf()


@router.get("/grub-config", response_class=PlainTextResponse)
def get_grub_config():
    """生成 aarch64 UEFI grub.cfg（部署至 /var/lib/tftpboot/grub.cfg）"""
    return pxe_service_v2.generate_grub_cfg()


@router.get("/setup-raid1-script", response_class=PlainTextResponse)
def get_setup_raid1_script():
    """生成批量创建 RAID1 系统盘的 Redfish 脚本（部署前在 PXE Host 执行）"""
    return pxe_service_v2.generate_setup_raid1_script()


@router.get("/pxe-boot-script", response_class=PlainTextResponse)
def get_pxe_boot_script():
    """生成 ipmitool 批量设置 PXE 启动的脚本"""
    return pxe_service_v2.generate_pxe_boot_script()
