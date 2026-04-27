"""
三平面网络配置 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models.node import Node, NetworkLink, get_db
from pydantic import BaseModel


router = APIRouter()


class LinkCreate(BaseModel):
    """链路创建"""
    source_node_id: int
    target_node_id: int
    plane: str  # management/control/data_front/data_back
    protocol: str  # IPMI/TCP/DPDK/RDMA
    bandwidth: str  # GE/10GE/100GE


class LinkResponse(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    plane: str
    protocol: str
    bandwidth: str
    status: str
    latency_ms: Optional[float]
    packet_loss_rate: Optional[float]
    throughput_mbps: Optional[float]
    last_check: Optional[datetime]

    class Config:
        from_attributes = True


class NetworkStatusResponse(BaseModel):
    """三平面网络状态"""
    management: dict
    control: dict
    data_front: dict
    data_back: dict


@router.get("/links", response_model=List[LinkResponse])
def get_links(
    plane: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取网络链路列表"""
    query = db.query(NetworkLink)
    if plane:
        query = query.filter(NetworkLink.plane == plane)
    return query.all()


@router.post("/links", response_model=LinkResponse)
def create_link(link: LinkCreate, db: Session = Depends(get_db)):
    """创建网络链路"""
    # 验证节点存在
    source = db.query(Node).filter(Node.id == link.source_node_id).first()
    target = db.query(Node).filter(Node.id == link.target_node_id).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="源节点或目标节点不存在")

    db_link = NetworkLink(**link.dict())
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link


@router.get("/status")
def get_network_status(db: Session = Depends(get_db)):
    """获取三平面网络整体状态"""
    nodes = db.query(Node).all()
    links = db.query(NetworkLink).all()

    # 统计各平面状态
    management_nodes = sum(1 for n in nodes if n.bmc_ip and n.status == 'online')
    control_nodes = sum(1 for n in nodes if n.ctrl_ip and n.ctrl_status == 'online')
    data_nodes = sum(1 for n in nodes if n.data_ip and n.data_status == 'online')

    # 统计链路状态
    management_links = [l for l in links if l.plane == 'management']
    control_links = [l for l in links if l.plane == 'control']
    data_front_links = [l for l in links if l.plane == 'data_front']
    data_back_links = [l for l in links if l.plane == 'data_back']

    def calc_link_stats(link_list):
        if not link_list:
            return {"total": 0, "normal": 0, "degraded": 0, "down": 0, "avg_latency": 0}
        return {
            "total": len(link_list),
            "normal": sum(1 for l in link_list if l.status == 'normal'),
            "degraded": sum(1 for l in link_list if l.status == 'degraded'),
            "down": sum(1 for l in link_list if l.status == 'down'),
            "avg_latency": sum(l.latency_ms or 0 for l in link_list) / len(link_list) if link_list else 0
        }

    return {
        "management": {
            "nodes_online": management_nodes,
            "nodes_total": sum(1 for n in nodes if n.bmc_ip),
            "links": calc_link_stats(management_links),
            "description": "管理面 - GE口，IPMI/BMC管理"
        },
        "control": {
            "nodes_online": control_nodes,
            "nodes_total": sum(1 for n in nodes if n.ctrl_ip),
            "links": calc_link_stats(control_links),
            "description": "控制面 - 10GE，心跳/配置同步"
        },
        "data_front": {
            "nodes_online": sum(1 for n in nodes if n.node_type == 'master' and n.data_status == 'online'),
            "nodes_total": sum(1 for n in nodes if n.node_type == 'master'),
            "links": calc_link_stats(data_front_links),
            "description": "数据面前段 - 100GE，DPDK协议"
        },
        "data_back": {
            "nodes_online": sum(1 for n in nodes if n.node_type == 'slave' and n.data_status == 'online'),
            "nodes_total": sum(1 for n in nodes if n.node_type == 'slave'),
            "links": calc_link_stats(data_back_links),
            "description": "数据面后段 - 100GE，RDMA协议"
        }
    }


@router.get("/topology-graph")
def get_topology_graph(db: Session = Depends(get_db)):
    """获取组网图数据（用于前端D3.js渲染）"""
    nodes = db.query(Node).all()
    links = db.query(NetworkLink).all()

    # 构建节点数据 - 添加虚拟管理站节点
    graph_nodes = []

    # 添加虚拟管理站节点（ID为"mgmt-station"）
    graph_nodes.append({
        "id": "mgmt-station",
        "name": "管理站",
        "type": "mgmt",
        "status": "online",
        "planes": {
            "management": {"ip": "192.168.1.1", "status": "online"},
            "control": {"ip": None, "status": "offline"},
            "data": {"ip": None, "status": "offline", "protocol": None}
        }
    })

    for node in nodes:
        graph_nodes.append({
            "id": str(node.id),
            "name": node.hostname,
            "type": node.node_type,
            "status": node.status,
            "planes": {
                "management": {
                    "ip": node.mgmt_ip,
                    "bmc_ip": node.bmc_ip,
                    "status": "online" if node.bmc_ip else "offline"
                },
                "control": {
                    "ip": node.ctrl_ip,
                    "status": node.ctrl_status or "offline"
                },
                "data": {
                    "ip": node.data_ip,
                    "status": node.data_status or "offline",
                    "protocol": node.data_protocol
                }
            }
        })

    # 构建链路数据 - 过滤无效链路并转换ID
    graph_links = []
    valid_node_ids = set(["mgmt-station"] + [str(n.id) for n in nodes])

    for link in links:
        source_id = str(link.source_node_id) if link.source_node_id else "mgmt-station"
        target_id = str(link.target_node_id)

        # 只添加有效链路（两端节点都存在）
        if source_id in valid_node_ids and target_id in valid_node_ids:
            graph_links.append({
                "source": source_id,
                "target": target_id,
                "plane": link.plane,
                "protocol": link.protocol,
                "bandwidth": link.bandwidth,
                "status": link.status,
                "latency": link.latency_ms,
                "packet_loss": link.packet_loss_rate
            })

    # 自动生成 Master-Slave 数据面链路（如果数据库中没有）
    masters = [n for n in nodes if n.node_type == 'master']
    slaves = [n for n in nodes if n.node_type == 'slave']
    sensors = [n for n in nodes if n.node_type == 'sensor']

    for master in masters:
        for slave in slaves:
            # 数据面后段链路 (Master -> Slave, RDMA)
            existing = any(
                l.source_node_id == master.id and
                l.target_node_id == slave.id and
                l.plane == 'data_back'
                for l in links
            )
            if not existing:
                graph_links.append({
                    "source": str(master.id),
                    "target": str(slave.id),
                    "plane": "data_back",
                    "protocol": "RDMA",
                    "bandwidth": "100GE",
                    "status": "normal" if master.data_status == 'online' and slave.data_status == 'online' else "down",
                    "latency": 0.1,
                    "packet_loss": 0
                })

    # 自动生成传感器到Master的数据面前段链路
    for sensor in sensors:
        for master in masters:
            existing = any(
                l.source_node_id == sensor.id and
                l.target_node_id == master.id and
                l.plane == 'data_front'
                for l in links
            )
            if not existing:
                graph_links.append({
                    "source": str(sensor.id),
                    "target": str(master.id),
                    "plane": "data_front",
                    "protocol": "DPDK",
                    "bandwidth": "100GE",
                    "status": "normal" if sensor.data_status == 'online' and master.data_status == 'online' else "down",
                    "latency": 0.1,
                    "packet_loss": 0
                })

    # 自动生成管理面链路（所有节点连接到管理站）
    for node in nodes:
        if node.bmc_ip:  # 有BMC IP的节点
            existing_mgmt = any(
                l.plane == 'management' and str(l.target_node_id) == str(node.id)
                for l in links
            )
            if not existing_mgmt:
                graph_links.append({
                    "source": "mgmt-station",
                    "target": str(node.id),
                    "plane": "management",
                    "protocol": "IPMI",
                    "bandwidth": "GE",
                    "status": "normal" if node.status == 'online' else "down",
                    "latency": 1.0,
                    "packet_loss": 0
                })

    return {
        "nodes": graph_nodes,
        "links": graph_links,
        "metadata": {
            "total_nodes": len(graph_nodes),
            "total_links": len(graph_links),
            "planes": ["management", "control", "data_front", "data_back"]
        }
    }


@router.post("/check/{node_id}")
def check_node_network(node_id: int, db: Session = Depends(get_db)):
    """检查节点三平面网络连通性"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 模拟网络检查结果
    results = {
        "node_id": node_id,
        "hostname": node.hostname,
        "planes": {
            "management": {
                "ip": node.mgmt_ip,
                "bmc_ip": node.bmc_ip,
                "reachable": node.bmc_ip is not None,
                "latency_ms": 1.2 if node.bmc_ip else None,
                "last_check": datetime.utcnow()
            },
            "control": {
                "ip": node.ctrl_ip,
                "reachable": node.ctrl_status == 'online',
                "latency_ms": 0.5 if node.ctrl_status == 'online' else None,
                "last_check": datetime.utcnow()
            },
            "data": {
                "ip": node.data_ip,
                "protocol": node.data_protocol,
                "reachable": node.data_status == 'online',
                "throughput_mbps": 8500 if node.data_status == 'online' else None,
                "last_check": datetime.utcnow()
            }
        },
        "overall_status": "online" if node.status == 'online' else "degraded"
    }

    return results