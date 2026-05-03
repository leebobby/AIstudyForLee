"""
故障诊断 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import re

from models.node import Node, Log, FaultPoint, DPDKStats, RDMAStats, DiagScript, get_db
from pydantic import BaseModel
from services.diag_service import run_ssh_command, collect_node_logs


router = APIRouter()


class FaultPointResponse(BaseModel):
    id: int
    node_id: Optional[int]
    link_id: Optional[int]
    plane: str
    fault_type: str
    description: str
    severity: str
    related_logs: Optional[dict]
    suggestions: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class LogResponse(BaseModel):
    id: int
    node_id: Optional[int]
    log_type: str
    level: str
    message: str
    raw_content: Optional[str]
    collected_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DiagnosisResult(BaseModel):
    """诊断结果"""
    node_id: int
    hostname: str
    overall_status: str
    faults: List[FaultPointResponse]
    recent_logs: List[LogResponse]
    suggestions: List[str]


@router.get("/faults", response_model=List[FaultPointResponse])
def get_fault_points(
    plane: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取故障点列表"""
    query = db.query(FaultPoint)
    if plane:
        query = query.filter(FaultPoint.plane == plane)
    if severity:
        query = query.filter(FaultPoint.severity == severity)
    if status:
        query = query.filter(FaultPoint.status == status)
    return query.order_by(FaultPoint.created_at.desc()).all()


@router.get("/faults/{fault_id}", response_model=FaultPointResponse)
def get_fault_detail(fault_id: int, db: Session = Depends(get_db)):
    """获取故障点详情"""
    fault = db.query(FaultPoint).filter(FaultPoint.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障点不存在")
    return fault


@router.get("/nodes/{node_id}", response_model=DiagnosisResult)
def diagnose_node(node_id: int, db: Session = Depends(get_db)):
    """诊断指定节点"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 获取节点故障点
    faults = db.query(FaultPoint).filter(
        FaultPoint.node_id == node_id,
        FaultPoint.status == 'active'
    ).all()

    # 获取最近日志
    logs = db.query(Log).filter(Log.node_id == node_id).order_by(Log.created_at.desc()).limit(50).all()

    # 根据节点状态生成建议
    suggestions = []

    if node.status != 'online':
        suggestions.append("检查BMC连通性，确认IPMI服务正常")
        suggestions.append("通过BMC远程查看系统日志")

    if node.ctrl_status != 'online':
        suggestions.append("检查控制面10GE网络连通性")
        suggestions.append("确认心跳服务正常运行")

    if node.data_status != 'online':
        if node.node_type == 'master':
            suggestions.append("检查DPDK环境配置")
            suggestions.append("确认100GE网卡绑定正确")
            suggestions.append("查看DPDK收包统计")
        elif node.node_type == 'slave':
            suggestions.append("检查RDMA网卡状态")
            suggestions.append("确认RDMA连接配置正确")

    overall_status = "healthy"
    if faults:
        if any(f.severity == 'critical' for f in faults):
            overall_status = "critical"
        elif any(f.severity == 'warning' for f in faults):
            overall_status = "warning"
        else:
            overall_status = "info"

    return DiagnosisResult(
        node_id=node_id,
        hostname=node.hostname,
        overall_status=overall_status,
        faults=faults,
        recent_logs=logs,
        suggestions=suggestions
    )


@router.post("/nodes/{node_id}/collect-logs")
def collect_logs(node_id: int, db: Session = Depends(get_db)):
    """收集节点日志"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 模拟日志收集（实际需要SSH到节点收集）
    collected_logs = []

    log_types = ['syslog', 'kernel', 'dmesg']
    if node.node_type == 'master':
        log_types.append('dpdk')
    elif node.node_type == 'slave':
        log_types.append('rdma')

    # 模拟日志数据
    for log_type in log_types:
        log_entry = Log(
            node_id=node_id,
            log_type=log_type,
            level='info',
            message=f"{log_type} 日志收集完成",
            collected_at=datetime.utcnow()
        )
        db.add(log_entry)
        collected_logs.append(log_type)

    db.commit()

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "collected_types": collected_logs,
        "message": "日志收集完成"
    }


@router.get("/logs", response_model=List[LogResponse])
def get_logs(
    node_id: Optional[int] = None,
    log_type: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """查询日志"""
    query = db.query(Log)
    if node_id:
        query = query.filter(Log.node_id == node_id)
    if log_type:
        query = query.filter(Log.log_type == log_type)
    if level:
        query = query.filter(Log.level == level)
    return query.order_by(Log.created_at.desc()).limit(limit).all()


@router.post("/analyze")
def analyze_all_nodes(db: Session = Depends(get_db)):
    """分析所有节点，发现故障"""
    nodes = db.query(Node).all()
    found_faults = []

    for node in nodes:
        # 检查节点状态并创建故障点

        if node.status == 'offline':
            existing = db.query(FaultPoint).filter(
                FaultPoint.node_id == node.id,
                FaultPoint.fault_type == 'node_offline',
                FaultPoint.status == 'active'
            ).first()

            if not existing:
                fault = FaultPoint(
                    node_id=node.id,
                    plane='管理面',
                    fault_type='node_offline',
                    description=f"节点 {node.hostname} 完全离线",
                    severity='critical',
                    suggestions="1. 检查BMC电源状态\n2. 检查管理面网络\n3. 通过IPMI重启节点"
                )
                db.add(fault)
                found_faults.append({
                    "node_id": node.id,
                    "hostname": node.hostname,
                    "fault_type": "node_offline",
                    "plane": "管理面"
                })

        if node.ctrl_status == 'offline' and node.status == 'online':
            existing = db.query(FaultPoint).filter(
                FaultPoint.node_id == node.id,
                FaultPoint.fault_type == 'control_plane_down',
                FaultPoint.status == 'active'
            ).first()

            if not existing:
                fault = FaultPoint(
                    node_id=node.id,
                    plane='控制面',
                    fault_type='control_plane_down',
                    description=f"节点 {node.hostname} 控制面断开",
                    severity='warning',
                    suggestions="1. 检查10GE网卡状态\n2. 检查心跳服务\n3. 检查控制面网络配置"
                )
                db.add(fault)
                found_faults.append({
                    "node_id": node.id,
                    "hostname": node.hostname,
                    "fault_type": "control_plane_down",
                    "plane": "控制面"
                })

        if node.data_status == 'offline' and node.status == 'online':
            existing = db.query(FaultPoint).filter(
                FaultPoint.node_id == node.id,
                FaultPoint.fault_type == 'data_plane_down',
                FaultPoint.status == 'active'
            ).first()

            if not existing:
                protocol = node.data_protocol or "unknown"
                fault = FaultPoint(
                    node_id=node.id,
                    plane='数据面',
                    fault_type='data_plane_down',
                    description=f"节点 {node.hostname} 数据面断开 ({protocol})",
                    severity='critical',
                    suggestions=f"1. 检查100GE网卡状态\n2. 检查{protocol}配置\n3. 检查数据面网络连接"
                )
                db.add(fault)
                found_faults.append({
                    "node_id": node.id,
                    "hostname": node.hostname,
                    "fault_type": "data_plane_down",
                    "plane": "数据面"
                })

    db.commit()

    return {
        "message": "故障分析完成",
        "nodes_analyzed": len(nodes),
        "faults_found": len(found_faults),
        "faults": found_faults
    }


@router.get("/dpdk-stats/{node_id}")
def get_dpdk_stats(node_id: int, db: Session = Depends(get_db)):
    """获取DPDK统计（Master节点）"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.node_type != 'master':
        raise HTTPException(status_code=400, detail="该节点不是Master节点")

    stats = db.query(DPDKStats).filter(DPDKStats.node_id == node_id).order_by(
        DPDKStats.collection_time.desc()
    ).limit(10).all()

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "data_ip": node.data_ip,
        "stats": stats
    }


@router.get("/rdma-stats/{node_id}")
def get_rdma_stats(node_id: int, db: Session = Depends(get_db)):
    """获取RDMA统计（Slave节点）"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if node.node_type != 'slave':
        raise HTTPException(status_code=400, detail="该节点不是Slave节点")

    stats = db.query(RDMAStats).filter(RDMAStats.node_id == node_id).order_by(
        RDMAStats.collection_time.desc()
    ).limit(10).all()

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "data_ip": node.data_ip,
        "stats": stats
    }


@router.post("/faults/{fault_id}/resolve")
def resolve_fault(fault_id: int, db: Session = Depends(get_db)):
    """标记故障已解决"""
    fault = db.query(FaultPoint).filter(FaultPoint.id == fault_id).first()
    if not fault:
        raise HTTPException(status_code=404, detail="故障点不存在")

    fault.status = 'resolved'
    db.commit()

    return {"message": "故障已标记为解决", "fault_id": fault_id}


# ─────────────────────────────────────────────
#  诊断脚本 CRUD
# ─────────────────────────────────────────────

class DiagScriptCreate(BaseModel):
    name: str
    description: Optional[str] = ''
    category: str = '通用诊断'
    script_content: str
    target_node_type: str = 'all'
    timeout: int = 30
    enabled: bool = True


class DiagScriptResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    script_content: str
    target_node_type: str
    timeout: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/scripts", response_model=List[DiagScriptResponse])
def list_scripts(category: Optional[str] = None, db: Session = Depends(get_db)):
    """获取诊断脚本列表"""
    q = db.query(DiagScript)
    if category:
        q = q.filter(DiagScript.category == category)
    return q.order_by(DiagScript.category, DiagScript.name).all()


@router.post("/scripts", response_model=DiagScriptResponse)
def create_script(data: DiagScriptCreate, db: Session = Depends(get_db)):
    """新建诊断脚本"""
    script = DiagScript(**data.model_dump())
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@router.put("/scripts/{script_id}", response_model=DiagScriptResponse)
def update_script(script_id: int, data: DiagScriptCreate, db: Session = Depends(get_db)):
    """更新诊断脚本"""
    script = db.query(DiagScript).filter(DiagScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    for k, v in data.model_dump().items():
        setattr(script, k, v)
    script.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(script)
    return script


@router.delete("/scripts/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    """删除诊断脚本"""
    script = db.query(DiagScript).filter(DiagScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")
    db.delete(script)
    db.commit()
    return {"message": "删除成功", "script_id": script_id}


class ScriptRunRequest(BaseModel):
    node_ids: List[int]
    ssh_user: str
    ssh_password: str
    ssh_port: int = 22


@router.post("/scripts/{script_id}/run")
def run_script(script_id: int, req: ScriptRunRequest, db: Session = Depends(get_db)):
    """在指定节点上执行诊断脚本"""
    script = db.query(DiagScript).filter(DiagScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="脚本不存在")

    nodes = db.query(Node).filter(Node.id.in_(req.node_ids)).all()
    if not nodes:
        raise HTTPException(status_code=400, detail="未找到指定节点")

    results = []
    for node in nodes:
        host = node.mgmt_ip
        if not host:
            results.append({
                "node_id": node.id,
                "hostname": node.hostname,
                "success": False,
                "stdout": "",
                "stderr": "节点无管理面IP",
                "exit_code": -1
            })
            continue

        result = run_ssh_command(
            host=host,
            port=req.ssh_port,
            username=req.ssh_user,
            password=req.ssh_password,
            command=script.script_content,
            timeout=script.timeout
        )
        results.append({
            "node_id": node.id,
            "hostname": node.hostname,
            **result
        })

    return {
        "script_id": script_id,
        "script_name": script.name,
        "results": results
    }


# ─────────────────────────────────────────────
#  一键日志采集
# ─────────────────────────────────────────────

class LogCollectRequest(BaseModel):
    node_ids: List[int]
    ssh_user: str
    ssh_password: str
    ssh_port: int = 22
    log_paths: List[str]
    target_dir: str


@router.post("/log-collect")
def collect_logs_to_windows(req: LogCollectRequest, db: Session = Depends(get_db)):
    """
    SSH采集OpenEuler节点日志到Windows目录。

    log_paths:
      - "/var/log/messages" 等路径 → SFTP直接下载
      - "dmesg", "journalctl ..." 等命令 → 执行后保存输出
    """
    if not req.log_paths:
        raise HTTPException(status_code=400, detail="请至少选择一项日志")
    if not req.target_dir:
        raise HTTPException(status_code=400, detail="请指定目标目录")

    nodes = db.query(Node).filter(Node.id.in_(req.node_ids)).all()
    if not nodes:
        raise HTTPException(status_code=400, detail="未找到指定节点")

    results = []
    for node in nodes:
        host = node.mgmt_ip
        if not host:
            results.append({
                "node": node.hostname,
                "host": "",
                "success": False,
                "error": "节点无管理面IP",
                "files": []
            })
            continue

        result = collect_node_logs(
            host=host,
            port=req.ssh_port,
            username=req.ssh_user,
            password=req.ssh_password,
            log_paths=req.log_paths,
            target_dir=req.target_dir,
            node_name=node.hostname
        )
        results.append(result)

    total_success = sum(1 for r in results if r["success"])
    return {
        "message": f"采集完成: {total_success}/{len(results)} 个节点成功",
        "results": results
    }