"""
数据库初始化和模拟数据种子
"""

from datetime import datetime
from sqlalchemy.orm import Session

# 使用相对导入
from .node import (
    Node, NetworkLink, BMCInfo, Alert, PatrolRecord,
    PXEConfig, Log, FaultPoint, DPDKStats, RDMAStats, DiagScript,
    engine, SessionLocal
)


def _seed_diag_scripts(db: Session):
    """生成示例诊断脚本（业务诊断 + 硬件诊断）"""
    if db.query(DiagScript).count() > 0:
        return

    scripts = [
        # ── 业务诊断 ──────────────────────────────────
        DiagScript(script_tab="business", category="初始化",
                   name="集群初始化检查",
                   description="检查集群各节点初始化状态是否完成",
                   script_content="systemctl status cluster-init.service 2>/dev/null || echo '服务未找到，请确认初始化脚本已部署'",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="business", category="初始化",
                   name="节点环境预检",
                   description="检查节点依赖环境（hugepage、CPU隔离等）",
                   script_content="echo '=== HugePages ===' && cat /proc/meminfo | grep -i huge && echo && echo '=== CPU隔离 ===' && cat /sys/devices/system/cpu/isolated",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="business", category="初始化",
                   name="网卡驱动加载检查",
                   description="确认DPDK/RDMA驱动已正确加载",
                   script_content="lsmod | grep -E 'mlx|ixgbe|ice|dpdk' && echo OK || echo '驱动未找到'",
                   target_node_type="all", timeout=10),

        DiagScript(script_tab="business", category="检测流程",
                   name="数据流检测",
                   description="检测从传感器到Master的数据链路状态",
                   script_content="ping -c 4 -W 1 192.168.100.1 && echo '数据面链路正常' || echo '数据面链路异常'",
                   target_node_type="master", timeout=15),
        DiagScript(script_tab="business", category="检测流程",
                   name="心跳服务检测",
                   description="检查控制面心跳服务运行状态",
                   script_content="systemctl is-active heartbeat.service 2>/dev/null || ping -c 2 10.0.0.1",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="business", category="检测流程",
                   name="收包统计检测",
                   description="检查DPDK收包统计是否正常增长",
                   script_content="dpdk-proc-info --stats 2>/dev/null | head -30 || echo 'dpdk-proc-info未找到'",
                   target_node_type="master", timeout=15),

        DiagScript(script_tab="business", category="LT流程",
                   name="LT服务状态",
                   description="检查LT流程相关服务运行状态",
                   script_content="systemctl status lt-service.service 2>/dev/null | head -20 || echo 'LT服务未找到'",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="business", category="LT流程",
                   name="LT数据队列深度",
                   description="查看LT处理队列积压情况",
                   script_content="ls -la /var/lib/lt/queue/ 2>/dev/null | wc -l || echo '队列目录未找到'",
                   target_node_type="slave", timeout=10),
        DiagScript(script_tab="business", category="LT流程",
                   name="LT错误日志",
                   description="查看最近50条LT错误日志",
                   script_content="grep -i 'LT.*error\\|error.*LT' /var/log/messages 2>/dev/null | tail -50 || journalctl -u lt-service -n 50 --no-pager 2>/dev/null",
                   target_node_type="slave", timeout=15),

        DiagScript(script_tab="business", category="PDA流程",
                   name="PDA进程状态",
                   description="检查PDA处理进程是否运行",
                   script_content="pgrep -la pda 2>/dev/null || ps aux | grep pda | grep -v grep || echo 'PDA进程未运行'",
                   target_node_type="slave", timeout=10),
        DiagScript(script_tab="business", category="PDA流程",
                   name="PDA输出文件检查",
                   description="检查PDA输出目录及最新文件",
                   script_content="ls -lth /data/pda/output/ 2>/dev/null | head -10 || echo '输出目录未找到'",
                   target_node_type="slave", timeout=10),
        DiagScript(script_tab="business", category="PDA流程",
                   name="PDA内存占用",
                   description="查看PDA进程内存使用情况",
                   script_content="ps aux | awk 'NR==1 || /pda/' | grep -v grep",
                   target_node_type="slave", timeout=10),

        # ── 硬件诊断 ──────────────────────────────────
        DiagScript(script_tab="hardware", category="存储诊断",
                   name="磁盘使用情况",
                   description="显示各分区磁盘使用率",
                   script_content="df -h", target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="存储诊断",
                   name="磁盘IO统计",
                   description="采集3秒磁盘IO数据",
                   script_content="iostat -xz 1 3 2>/dev/null || echo 'iostat未安装 (yum install sysstat)'",
                   target_node_type="all", timeout=20),
        DiagScript(script_tab="hardware", category="存储诊断",
                   name="块设备列表",
                   description="列出所有块设备及挂载点",
                   script_content="lsblk -o NAME,SIZE,TYPE,MOUNTPOINT",
                   target_node_type="all", timeout=10),

        DiagScript(script_tab="hardware", category="设备诊断",
                   name="PCI设备列表",
                   description="列出所有PCI设备（含网卡）",
                   script_content="lspci | grep -iE 'ethernet|infiniband|mellanox|intel'",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="设备诊断",
                   name="CPU信息",
                   description="显示CPU型号和核心数",
                   script_content="lscpu | grep -E 'Model name|CPU\\(s\\)|Thread|Core|Socket'",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="设备诊断",
                   name="内存详情",
                   description="显示内存条详细信息",
                   script_content="dmidecode -t memory 2>/dev/null | grep -E 'Size|Type|Speed|Locator' | grep -v 'No Module'",
                   target_node_type="all", timeout=10),

        DiagScript(script_tab="hardware", category="网络诊断",
                   name="查看网络接口状态",
                   description="显示所有网络接口的链路状态",
                   script_content="ip link show", target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="网络诊断",
                   name="查看IP地址",
                   description="显示所有接口的IP地址配置",
                   script_content="ip addr show", target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="网络诊断",
                   name="检查RDMA设备",
                   description="查看RDMA网卡状态（Slave节点）",
                   script_content="ibstat 2>/dev/null || rdma link show 2>/dev/null || echo 'RDMA工具未找到'",
                   target_node_type="slave", timeout=15),
        DiagScript(script_tab="hardware", category="网络诊断",
                   name="检查DPDK绑定",
                   description="查看DPDK网卡绑定状态（Master节点）",
                   script_content="dpdk-devbind.py --status 2>/dev/null || echo 'DPDK工具未找到'",
                   target_node_type="master", timeout=15),
        DiagScript(script_tab="hardware", category="网络诊断",
                   name="网络连接统计",
                   description="显示TCP/UDP连接状态统计",
                   script_content="ss -s", target_node_type="all", timeout=10),

        DiagScript(script_tab="hardware", category="系统诊断",
                   name="系统负载概览",
                   description="显示CPU/内存/磁盘使用情况",
                   script_content="uptime && echo && free -h && echo && df -h",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="系统诊断",
                   name="CPU占用Top进程",
                   description="显示CPU占用最高的20个进程",
                   script_content="ps aux --sort=-%cpu | head -21",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="系统诊断",
                   name="内核错误日志",
                   description="从dmesg筛选错误和警告信息",
                   script_content="dmesg | grep -iE 'error|warn|fail|oops|panic' | tail -100",
                   target_node_type="all", timeout=15),
        DiagScript(script_tab="hardware", category="系统诊断",
                   name="系统服务状态",
                   description="列出所有失败的systemd服务",
                   script_content="systemctl --failed --no-legend",
                   target_node_type="all", timeout=10),
        DiagScript(script_tab="hardware", category="系统诊断",
                   name="最近系统日志",
                   description="查看最近200条系统日志",
                   script_content="journalctl -n 200 --no-pager 2>/dev/null || tail -200 /var/log/messages",
                   target_node_type="all", timeout=15),
    ]

    for s in scripts:
        db.add(s)
    db.commit()
    print(f"  - 已生成 {len(scripts)} 个示例诊断脚本（业务诊断 + 硬件诊断）")


def seed_demo_data():
    """生成演示数据"""
    db: Session = SessionLocal()

    try:
        # 检查是否已有数据
        if db.query(Node).count() > 0:
            print("数据库已有数据，跳过节点数据生成")
            _seed_diag_scripts(db)
            return

        # 创建Master节点
        master = Node(
            hostname="master-1",
            node_type="master",
            role="主控节点",
            # 管理面
            mgmt_ip="192.168.1.10",
            mgmt_mac="00:1a:2b:3c:4d:10",
            bmc_ip="192.168.1.110",
            bmc_mac="00:1a:2b:3c:4d:aa",
            # 控制面
            ctrl_ip="10.0.0.10",
            ctrl_mac="00:1a:2b:3c:4e:10",
            ctrl_status="online",
            # 数据面
            data_ip="192.168.100.10",
            data_mac="00:1a:2b:3c:4f:10",
            data_status="online",
            data_protocol="DPDK",
            # 整体
            status="online",
            os_version="openEuler 22.03 LTS",
            cpu_cores=64,
            memory_gb=128,
            disk_gb=1000,
            created_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            last_mgmt_seen=datetime.utcnow(),
            last_ctrl_seen=datetime.utcnow(),
            last_data_seen=datetime.utcnow()
        )
        db.add(master)

        # 创建Slave节点
        slaves = []
        for i in range(1, 6):
            slave = Node(
                hostname=f"slave-{i}",
                node_type="slave",
                role="数据处理节点",
                # 管理面
                mgmt_ip=f"192.168.1.{11+i}",
                mgmt_mac=f"00:1a:2b:3c:4d:{11+i:02d}",
                bmc_ip=f"192.168.1.{111+i}",
                bmc_mac=f"00:1a:2b:3c:4d:{111+i:02x}",
                # 控制面
                ctrl_ip=f"10.0.0.{11+i}",
                ctrl_mac=f"00:1a:2b:3c:4e:{11+i:02d}",
                ctrl_status="online" if i < 4 else "offline",
                # 数据面
                data_ip=f"192.168.100.{11+i}",
                data_mac=f"00:1a:2b:3c:4f:{11+i:02d}",
                data_status="online" if i < 4 else "offline",
                data_protocol="RDMA",
                # 整体
                status="online" if i < 4 else "offline",
                os_version="openEuler 22.03 LTS",
                cpu_cores=64,
                memory_gb=256,
                disk_gb=2000,
                created_at=datetime.utcnow(),
                last_seen=datetime.utcnow() if i < 4 else None
            )
            db.add(slave)
            slaves.append(slave)

        # 创建传感器节点
        sensor = Node(
            hostname="sensor-array-1",
            node_type="sensor",
            role="数据采集阵列",
            # 数据面 (仅数据面)
            data_ip="192.168.100.1",
            data_mac="00:1a:2b:3c:4f:01",
            data_status="online",
            data_protocol="raw",
            # 整体
            status="online",
            created_at=datetime.utcnow()
        )
        db.add(sensor)

        db.commit()

        # 创建网络链路
        # 数据面前段: 传感器 -> Master (DPDK)
        link1 = NetworkLink(
            source_node_id=sensor.id,
            target_node_id=master.id,
            plane="data_front",
            protocol="DPDK",
            bandwidth="100GE",
            status="normal",
            latency_ms=0.1,
            packet_loss_rate=0.0001,
            throughput_mbps=8500,
            last_check=datetime.utcnow()
        )
        db.add(link1)

        # 数据面后段: Master -> Slave (RDMA)
        for slave in slaves[:3]:  # 只为在线的slave创建链路
            link = NetworkLink(
                source_node_id=master.id,
                target_node_id=slave.id,
                plane="data_back",
                protocol="RDMA",
                bandwidth="100GE",
                status="normal",
                latency_ms=0.1,
                packet_loss_rate=0.00005,
                throughput_mbps=8200,
                last_check=datetime.utcnow()
            )
            db.add(link)

        # 控制面链路: Master <-> Slave
        for slave in slaves:
            link = NetworkLink(
                source_node_id=master.id,
                target_node_id=slave.id,
                plane="control",
                protocol="TCP",
                bandwidth="10GE",
                status="normal" if slave.status == "online" else "down",
                latency_ms=0.5,
                packet_loss_rate=0,
                throughput_mbps=100,
                last_check=datetime.utcnow()
            )
            db.add(link)

        # 创建BMC信息
        for node in [master] + slaves:
            bmc = BMCInfo(
                node_id=node.id,
                bmc_model="iKVM",
                bmc_version="2.0.5",
                power_status="on",
                temperature=45 + node.id,
                fan_speed=3200,
                last_update=datetime.utcnow()
            )
            db.add(bmc)

        # 创建PXE配置
        pxe_config = PXEConfig(
            name="v2-kunpeng-22nodes",
            mgmt_subnet="172.16.0.0/24",
            ctrl_subnet="172.16.3.0/24",
            data_subnet="100.1.0.0/16",
            mgmt_gateway=None,
            ctrl_gateway="172.16.3.1",
            data_gateway=None,
            dns_servers="172.16.3.10",
            created_at=datetime.utcnow()
        )
        db.add(pxe_config)

        # 创建一些告警
        alert1 = Alert(
            node_id=slaves[3].id,  # offline的slave
            plane="数据面",
            alert_type="node_offline",
            severity="critical",
            message=f"节点 {slaves[3].hostname} 数据面离线",
            status="active",
            created_at=datetime.utcnow()
        )
        db.add(alert1)

        alert2 = Alert(
            node_id=slaves[4].id,
            plane="控制面",
            alert_type="control_plane_down",
            severity="warning",
            message=f"节点 {slaves[4].hostname} 控制面断开",
            status="active",
            created_at=datetime.utcnow()
        )
        db.add(alert2)

        # 创建DPDK统计
        dpdk_stat = DPDKStats(
            node_id=master.id,
            rx_packets=1000000,
            rx_bytes=1500000000,
            rx_dropped=10,
            rx_errors=0,
            throughput_mbps=8500,
            collection_time=datetime.utcnow()
        )
        db.add(dpdk_stat)

        # 创建RDMA统计
        for slave in slaves[:3]:
            rdma_stat = RDMAStats(
                node_id=slave.id,
                tx_packets=900000,
                tx_bytes=1400000000,
                tx_dropped=5,
                tx_errors=0,
                throughput_mbps=8200,
                collection_time=datetime.utcnow()
            )
            db.add(rdma_stat)

        db.commit()

        _seed_diag_scripts(db)

        print("演示数据已生成:")
        print(f"  - 1 Master节点 (master-1)")
        print(f"  - 5 Slave节点 (slave-1 到 slave-5)")
        print(f"  - 1 传感器节点")
        print(f"  - 网络链路已创建")
        print(f"  - 2 个活跃告警")

    except Exception as e:
        print(f"生成数据失败: {e}")
        db.rollback()
    finally:
        db.close()


def init_db_with_seed():
    """初始化数据库并生成种子数据"""
    from .node import Base
    Base.metadata.create_all(bind=engine)
    seed_demo_data()


if __name__ == "__main__":
    init_db_with_seed()