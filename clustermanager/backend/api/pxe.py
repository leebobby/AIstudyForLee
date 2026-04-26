"""
PXE部署 API
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.models.node import Node, PXEConfig, get_db
from pydantic import BaseModel


router = APIRouter()


class PXEConfigCreate(BaseModel):
    """PXE配置创建"""
    name: str
    mgmt_subnet: str  # 管理面子网 192.168.1.0/24
    ctrl_subnet: str  # 控制面子网 10.0.0.0/24
    data_subnet: str  # 数据面子网 192.168.100.0/24
    mgmt_gateway: Optional[str] = None
    ctrl_gateway: Optional[str] = None
    data_gateway: Optional[str] = None
    dns_servers: Optional[str] = "8.8.8.8,8.8.4.4"


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
    """三平面网络IP规划"""
    config_id: int
    master_count: int = 1
    slave_count: int
    mgmt_ip_start: str  # 管理面起始IP
    ctrl_ip_start: str  # 控制面起始IP
    data_ip_start: str  # 数据面起始IP


class DeployRequest(BaseModel):
    """部署请求"""
    node_id: int
    node_type: str  # master/slave
    mgmt_ip: str
    ctrl_ip: str
    data_ip: str
    hostname: Optional[str] = None


class DeployStatus(BaseModel):
    """部署状态"""
    node_id: int
    hostname: str
    status: str
    stage: str  # discovering/installing/configuring/completed/error
    progress: int
    message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@router.get("/configs", response_model=List[PXEConfigResponse])
def get_pxe_configs(db: Session = Depends(get_db)):
    """获取所有PXE配置"""
    return db.query(PXEConfig).all()


@router.post("/config", response_model=PXEConfigResponse)
def create_pxe_config(config: PXEConfigCreate, db: Session = Depends(get_db)):
    """创建PXE部署配置"""
    db_config = PXEConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


@router.post("/network-plan")
def plan_network_ips(
    request: NetworkPlanRequest,
    db: Session = Depends(get_db)
):
    """
    三平面网络IP规划
    根据节点数量自动分配三个平面的IP地址
    """
    config = db.query(PXEConfig).filter(PXEConfig.id == request.config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 解析起始IP
    def parse_ip_start(ip_start: str):
        parts = ip_start.split('.')
        base = '.'.join(parts[:3])
        start_num = int(parts[3])
        return base, start_num

    mgmt_base, mgmt_start = parse_ip_start(request.mgmt_ip_start)
    ctrl_base, ctrl_start = parse_ip_start(request.ctrl_ip_start)
    data_base, data_start = parse_ip_start(request.data_ip_start)

    total_nodes = request.master_count + request.slave_count
    plan = {
        "masters": [],
        "slaves": []
    }

    # 分配Master节点IP
    for i in range(request.master_count):
        idx = i + 1
        node_plan = {
            "hostname": f"master-{idx}",
            "node_type": "master",
            "mgmt_ip": f"{mgmt_base}.{mgmt_start + idx}",
            "ctrl_ip": f"{ctrl_base}.{ctrl_start + idx}",
            "data_ip": f"{data_base}.{data_start + idx}",
            "data_protocol": "DPDK",
            "bmc_ip": f"{mgmt_base}.{mgmt_start + idx + 100}"  # BMC IP偏移100
        }
        plan["masters"].append(node_plan)

    # 分配Slave节点IP
    for i in range(request.slave_count):
        idx = request.master_count + i + 1
        node_plan = {
            "hostname": f"slave-{i + 1}",
            "node_type": "slave",
            "mgmt_ip": f"{mgmt_base}.{mgmt_start + idx}",
            "ctrl_ip": f"{ctrl_base}.{ctrl_start + idx}",
            "data_ip": f"{data_base}.{data_start + idx}",
            "data_protocol": "RDMA",
            "bmc_ip": f"{mgmt_base}.{mgmt_start + idx + 100}"
        }
        plan["slaves"].append(node_plan)

    return {
        "config_id": request.config_id,
        "total_nodes": total_nodes,
        "mgmt_subnet": config.mgmt_subnet,
        "ctrl_subnet": config.ctrl_subnet,
        "data_subnet": config.data_subnet,
        "plan": plan
    }


@router.get("/status")
def get_deploy_status(db: Session = Depends(get_db)):
    """获取所有部署任务状态"""
    nodes = db.query(Node).filter(Node.status.in_(['deploying', 'installing', 'configuring'])).all()

    statuses = []
    for node in nodes:
        status = DeployStatus(
            node_id=node.id,
            hostname=node.hostname,
            status=node.status,
            stage=node.status,
            progress=50,  # 模拟进度
            message="正在部署...",
            started_at=node.created_at
        )
        statuses.append(status)

    return statuses


@router.post("/nodes/{node_id}/deploy")
async def deploy_node(
    node_id: int,
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    部署指定节点
    设置PXE启动并开始安装流程
    """
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 更新节点信息
    node.hostname = request.hostname or node.hostname
    node.node_type = request.node_type
    node.mgmt_ip = request.mgmt_ip
    node.ctrl_ip = request.ctrl_ip
    node.data_ip = request.data_ip
    node.data_protocol = "DPDK" if request.node_type == "master" else "RDMA"
    node.status = "deploying"

    db.commit()

    # 后台任务：实际部署流程
    # background_tasks.add_task(run_deployment, node_id, request)

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "status": "deploying",
        "message": "部署任务已启动，请等待完成",
        "network_config": {
            "management": request.mgmt_ip,
            "control": request.ctrl_ip,
            "data": request.data_ip
        }
    }


@router.post("/batch-deploy")
async def batch_deploy_nodes(
    nodes: List[DeployRequest],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量部署多个节点"""
    results = []

    for deploy_req in nodes:
        node = db.query(Node).filter(Node.id == deploy_req.node_id).first()
        if node:
            node.hostname = deploy_req.hostname or node.hostname
            node.node_type = deploy_req.node_type
            node.mgmt_ip = deploy_req.mgmt_ip
            node.ctrl_ip = deploy_req.ctrl_ip
            node.data_ip = deploy_req.data_ip
            node.data_protocol = "DPDK" if deploy_req.node_type == "master" else "RDMA"
            node.status = "deploying"

            results.append({
                "node_id": deploy_req.node_id,
                "hostname": node.hostname,
                "status": "deploying"
            })

    db.commit()

    return {
        "message": "批量部署已启动",
        "total_nodes": len(nodes),
        "results": results
    }


@router.get("/kickstart/{node_type}")
def get_kickstart_template(node_type: str):
    """
    获取 Kickstart 模板
    master: Master节点模板（DPDK配置）
    slave: Slave节点模板（RDMA配置）
    """
    if node_type not in ['master', 'slave']:
        raise HTTPException(status_code=400, detail="节点类型必须是 master 或 slave")

    # 返回模板内容摘要
    return {
        "node_type": node_type,
        "template_file": f"{node_type}.ks",
        "features": [
            "openEuler-ARM 基础系统",
            "三平面网络配置",
            "SSH服务配置",
            "DPDK环境" if node_type == "master" else "RDMA环境",
            "监控Agent安装"
        ]
    }