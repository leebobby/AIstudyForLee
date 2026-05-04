"""
PXE 配置服务 v2 - 鲲鹏 ARM64 + HNS 集群 22 节点三平面部署
管理面 GE: 172.16.0.0/24 | 控制面 10GE: 172.16.3.0/24 | 数据面 100GE: 多子网
"""

import json
from typing import Dict, List, Optional
from pathlib import Path

DEFAULT_NODES_JSON_PATH = Path(__file__).parent.parent / "pxe_data" / "nodes.json"


class PXEServiceV2:
    """PXE 部署配置服务 v2"""

    def __init__(self, nodes_json_path: str = None):
        self.nodes_json_path = Path(nodes_json_path) if nodes_json_path else DEFAULT_NODES_JSON_PATH
        self.nodes_json_path.parent.mkdir(parents=True, exist_ok=True)

    # ── nodes.json 管理 ──────────────────────────────────────────────────────

    def read_nodes_json(self) -> Dict:
        if not self.nodes_json_path.exists():
            data = self._default_nodes_json()
            self.write_nodes_json(data)
            return data
        with open(self.nodes_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_nodes_json(self, data: Dict) -> None:
        with open(self.nodes_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _default_nodes_json(self) -> Dict:
        """22 节点默认模板（MAC 为占位符，需替换为实际硬件 MAC）"""
        nodes: Dict = {
            "_comment": "鲲鹏集群 nodes.json v2 - 22节点，基于新组网图",
            "_hardware": "全角色系统盘统一为 2×960G 硬件 RAID1 -> /dev/sda",
        }

        # Master ×6: BMC 172.16.0.11-16 | ctrl 172.16.3.11-16
        for i in range(1, 7):
            mac = f"aa:bb:cc:11:00:{i:02x}"
            nodes[mac] = {
                "hostname_new": f"master-{i:02d}",
                "role": "master",
                "ctrl_nic": "eno1",
                "ctrl_ip": f"172.16.3.{10 + i}/24",
                "ctrl_gw": "172.16.3.1",
                "dpdk_nics": "eno2 eno3",
                "dpdk_ips": f"200.1.1.{10 + i}/24 200.1.2.{30 + i}/24",
                "rdma_nics": "eno4 eno5",
                "rdma_ips": f"100.1.1.{10 + i}/24 100.1.2.{30 + i}/24",
                "hugepages_1g": "100",
                "system_disk": "/dev/sda",
                "data_disks": "",
                "dirs": "/data /dpdk-data",
                "bmc_ip": f"172.16.0.{10 + i}",
            }

        # Slave ×12: BMC 172.16.0.51-62 | ctrl 172.16.3.51-62
        nfs_mounts = (
            "100.1.1.170:/data/export:/mnt/swath1,"
            "100.1.1.171:/data/export:/mnt/swath2,"
            "100.1.2.172:/data/export:/mnt/global"
        )
        for i in range(1, 13):
            mac = f"aa:bb:cc:22:00:{i:02x}"
            nodes[mac] = {
                "hostname_new": f"slave-{i:02d}",
                "role": "slave",
                "ctrl_nic": "eno1",
                "ctrl_ip": f"172.16.3.{50 + i}/24",
                "ctrl_gw": "172.16.3.1",
                "rdma_nics": "eno2",
                "rdma_ips": f"100.1.1.{50 + i}/24",
                "nfs_mounts": nfs_mounts,
                "hugepages_1g": "0",
                "system_disk": "/dev/sda",
                "data_disks": "",
                "dirs": "/data",
                "bmc_ip": f"172.16.0.{50 + i}",
            }

        # SubSwath ×2: BMC 172.16.0.170-171 | ctrl 172.16.3.170-171
        for i in range(1, 3):
            mac = f"aa:bb:cc:33:00:{i:02x}"
            nodes[mac] = {
                "hostname_new": f"subswath-{i:02d}",
                "role": "subswath",
                "ctrl_nic": "eno1",
                "ctrl_ip": f"172.16.3.{169 + i}/24",
                "ctrl_gw": "172.16.3.1",
                "rdma_nics": "eno2 eno3",
                "rdma_ips": f"100.1.1.{169 + i}/24 100.1.2.{169 + i}/24",
                "nfs_export_ip": f"100.1.1.{169 + i}",
                "nfs_exports": "/data/export",
                "hugepages_1g": "0",
                "system_disk": "/dev/sda",
                "data_disks": "/dev/nvme0n1 /dev/nvme1n1 /dev/nvme2n1 /dev/nvme3n1",
                "data_raid_level": "raid10",
                "dirs": "/data/export",
                "extra_pkgs": "nfs-utils mdadm",
                "bmc_ip": f"172.16.0.{169 + i}",
            }

        # GStorage ×1: BMC 172.16.0.172 | ctrl 172.16.3.172
        nodes["aa:bb:cc:44:00:01"] = {
            "hostname_new": "gstorage-01",
            "role": "gstorage",
            "ctrl_nic": "eno1",
            "ctrl_ip": "172.16.3.172/24",
            "ctrl_gw": "172.16.3.1",
            "rdma_nics": "eno2",
            "rdma_ips": "100.1.2.172/24",
            "nfs_export_ip": "100.1.2.172",
            "nfs_exports": "/data/export",
            "hugepages_1g": "0",
            "system_disk": "/dev/sda",
            "data_disks": "/dev/sdb",
            "dirs": "/data/export",
            "extra_pkgs": "nfs-utils",
            "bmc_ip": "172.16.0.172",
        }

        return nodes

    # ── firstboot 节点环境变量 ────────────────────────────────────────────────

    def get_node_env_vars(self, mac: str, nodes_json: Dict = None) -> Optional[str]:
        """
        根据 MAC 返回节点 shell 环境变量文本（firstboot detect.sh 调用）。
        返回 None 表示 MAC 未注册。
        """
        if nodes_json is None:
            nodes_json = self.read_nodes_json()

        node = nodes_json.get(mac.lower())
        if not node:
            return None

        pairs = [
            ("ROLE",             node.get("role", "")),
            ("HOSTNAME_NEW",     node.get("hostname_new", "")),
            ("CTRL_NIC",         node.get("ctrl_nic", "")),
            ("CTRL_IP",          node.get("ctrl_ip", "")),
            ("CTRL_GW",          node.get("ctrl_gw", "")),
            ("DPDK_NICS",        node.get("dpdk_nics", "")),
            ("DPDK_IPS",         node.get("dpdk_ips", "")),
            ("RDMA_NICS",        node.get("rdma_nics", "")),
            ("RDMA_IPS",         node.get("rdma_ips", "")),
            ("HUGEPAGES_1G",     node.get("hugepages_1g", "0")),
            ("SYSTEM_DISK",      node.get("system_disk", "/dev/sda")),
            ("DATA_DISKS",       node.get("data_disks", "")),
            ("DATA_RAID_LEVEL",  node.get("data_raid_level", "")),
            ("NFS_MOUNTS",       node.get("nfs_mounts", "")),
            ("NFS_EXPORT_IP",    node.get("nfs_export_ip", "")),
            ("NFS_EXPORTS",      node.get("nfs_exports", "")),
            ("DIRS",             node.get("dirs", "")),
            ("EXTRA_PKGS",       node.get("extra_pkgs", "")),
        ]
        return "".join(f"{k}={v}\n" for k, v in pairs)

    # ── DHCP 配置生成 ────────────────────────────────────────────────────────

    def generate_dhcpd_conf(self, nodes_json: Dict = None) -> str:
        if nodes_json is None:
            nodes_json = self.read_nodes_json()

        host_lines = []
        for mac, node in nodes_json.items():
            if mac.startswith("_"):
                continue
            ctrl_ip = node.get("ctrl_ip", "").split("/")[0]
            hostname = node.get("hostname_new", "")
            if ctrl_ip and hostname:
                host_lines.append(
                    f"host {hostname} {{ hardware ethernet {mac}; fixed-address {ctrl_ip}; }}"
                )

        hosts_block = "\n".join(host_lines)
        return f"""option domain-name-servers 172.16.3.10;
default-lease-time 600;
max-lease-time 7200;
authoritative;

# ARM64 UEFI PXE 客户端识别
class "aarch64-uefi" {{
    match if substring(option vendor-class-identifier, 0, 21)
               = "PXEClient:Arch:00011";
    filename "grubaa64.efi";
}}

# 控制面子网（节点 PXE 引导）
subnet 172.16.3.0 netmask 255.255.255.0 {{
    range 172.16.3.100 172.16.3.110;
    option routers 172.16.3.1;
    next-server 172.16.3.10;
}}

# ── 固定 IP 绑定 ──
{hosts_block}
"""

    # ── GRUB 配置生成 ────────────────────────────────────────────────────────

    def generate_grub_cfg(self) -> str:
        return """set default=0
set timeout=15

menuentry 'Deploy Base Image (aarch64)' {
    linux  /vmlinuz-aa64 \\
           ip=dhcp \\
           pxe_server=172.16.3.10 \\
           console=ttyAMA0,115200 \\
           quiet
    initrd /initrd-aa64.img
}

menuentry 'Boot from local disk' { exit }
"""

    # ── RAID1 批量初始化脚本 ──────────────────────────────────────────────────

    def generate_setup_raid1_script(self, nodes_json: Dict = None) -> str:
        if nodes_json is None:
            nodes_json = self.read_nodes_json()

        bmc_comments: List[str] = []
        for mac, node in nodes_json.items():
            if mac.startswith("_"):
                continue
            bmc_ip = node.get("bmc_ip", "")
            hostname = node.get("hostname_new", "")
            if bmc_ip:
                bmc_comments.append(f"  {bmc_ip}  # {hostname}")

        ips_list = "\n".join(bmc_comments)
        return f"""#!/bin/bash
# 批量为所有节点创建 RAID1 系统盘（Redfish API）
# 执行前请确认 IBMC_PASS 已正确设置

IBMC_IPS=(
{ips_list}
)
IBMC_USER=Administrator
IBMC_PASS='your_password'

for ip in "${{IBMC_IPS[@]}}"; do
    echo "=== Creating RAID1 on $ip ==="
    curl -k -u "$IBMC_USER:$IBMC_PASS" \\
         -H 'Content-Type: application/json' \\
         -X POST "https://$ip/redfish/v1/Systems/1/Storages/RAIDStorage0/Volumes" \\
         -d '{{
           "Name": "SystemRAID1",
           "RAIDType": "RAID1",
           "CapacityBytes": -1,
           "Drives": [
             {{"@odata.id": "/redfish/v1/Chassis/1/Drives/HDDPlaneDisk0"}},
             {{"@odata.id": "/redfish/v1/Chassis/1/Drives/HDDPlaneDisk1"}}
           ]
         }}'
    echo
done
"""

    # ── PXE 引导启动脚本 ─────────────────────────────────────────────────────

    def generate_pxe_boot_script(self, nodes_json: Dict = None) -> str:
        if nodes_json is None:
            nodes_json = self.read_nodes_json()

        lines = []
        for mac, node in nodes_json.items():
            if mac.startswith("_"):
                continue
            bmc_ip = node.get("bmc_ip", "")
            hostname = node.get("hostname_new", "")
            if bmc_ip:
                lines.append(f'\necho "Setting PXE boot: {hostname} ({bmc_ip})"')
                lines.append(
                    f'ipmitool -I lanplus -H {bmc_ip} -U "$IBMC_USER" -P "$IBMC_PASS"'
                    " chassis bootdev pxe options=efiboot"
                )
                lines.append(
                    f'ipmitool -I lanplus -H {bmc_ip} -U "$IBMC_USER" -P "$IBMC_PASS"'
                    " chassis power cycle"
                )

        body = "\n".join(lines)
        return f"""#!/bin/bash
# 批量设置 PXE 启动并重启节点
IBMC_USER=Administrator
IBMC_PASS=your_password
{body}
"""

    # ── IP 规划 ──────────────────────────────────────────────────────────────

    def generate_ip_plan(
        self,
        master_count: int = 6,
        slave_count: int = 12,
        subswath_count: int = 2,
        gstorage_count: int = 1,
    ) -> Dict:
        """
        v2 三平面 IP 规划（六子网固定网段）：
          管理面 BMC  : 172.16.0.x
          控制面 10GE : 172.16.3.x
          DPDK-1      : 200.1.1.x  (Master eno2)
          DPDK-2      : 200.1.2.x  (Master eno3)
          RDMA-1      : 100.1.1.x  (Master eno4 / Slave eno2 / SubSwath eno2)
          RDMA-2      : 100.1.2.x  (Master eno5 / SubSwath eno3 / GStorage eno2)
        """
        plan: Dict = {
            "pxe_host": [],
            "masters": [],
            "slaves": [],
            "subswaths": [],
            "gstorages": [],
        }

        plan["pxe_host"].append({
            "hostname": "host-server",
            "role": "pxe_host",
            "bmc_ip": "172.16.0.10",
            "ctrl_ip": "172.16.3.10",
            "note": "100GE 上行至 10G 交换机 100GE 上行口",
        })

        for i in range(1, master_count + 1):
            plan["masters"].append({
                "hostname": f"master-{i:02d}",
                "role": "master",
                "bmc_ip": f"172.16.0.{10 + i}",
                "ctrl_ip": f"172.16.3.{10 + i}",
                "dpdk1_ip": f"200.1.1.{10 + i}",
                "dpdk2_ip": f"200.1.2.{30 + i}",
                "rdma1_ip": f"100.1.1.{10 + i}",
                "rdma2_ip": f"100.1.2.{30 + i}",
                "hugepages_1g": 100,
                "system_disk": "/dev/sda",
                "nics": "eno1(ctrl) eno2(dpdk1) eno3(dpdk2) eno4(rdma1) eno5(rdma2)",
            })

        for i in range(1, slave_count + 1):
            plan["slaves"].append({
                "hostname": f"slave-{i:02d}",
                "role": "slave",
                "bmc_ip": f"172.16.0.{50 + i}",
                "ctrl_ip": f"172.16.3.{50 + i}",
                "rdma1_ip": f"100.1.1.{50 + i}",
                "system_disk": "/dev/sda",
                "nics": "eno1(ctrl) eno2(rdma1)",
            })

        for i in range(1, subswath_count + 1):
            plan["subswaths"].append({
                "hostname": f"subswath-{i:02d}",
                "role": "subswath",
                "bmc_ip": f"172.16.0.{169 + i}",
                "ctrl_ip": f"172.16.3.{169 + i}",
                "rdma1_ip": f"100.1.1.{169 + i}",
                "rdma2_ip": f"100.1.2.{169 + i}",
                "data_disks": "4×7.68T NVMe",
                "data_raid": "软件 RAID10 (mdadm)",
                "system_disk": "/dev/sda",
                "nics": "eno1(ctrl) eno2(rdma1) eno3(rdma2)",
            })

        for i in range(1, gstorage_count + 1):
            plan["gstorages"].append({
                "hostname": f"gstorage-{i:02d}",
                "role": "gstorage",
                "bmc_ip": f"172.16.0.{171 + i}",
                "ctrl_ip": f"172.16.3.{171 + i}",
                "rdma2_ip": f"100.1.2.{171 + i}",
                "data_disks": "N×机械硬盘",
                "data_raid": "硬件 RAID50 (BMC 预配置)",
                "system_disk": "/dev/sda",
                "nics": "eno1(ctrl) eno2(rdma2)",
            })

        total = 1 + master_count + slave_count + subswath_count + gstorage_count
        return {
            "total_nodes": total,
            "subnets": {
                "mgmt_bmc_ge":    "172.16.0.0/24",
                "ctrl_10ge":      "172.16.3.0/24",
                "dpdk1_100ge":    "200.1.1.0/24",
                "dpdk2_100ge":    "200.1.2.0/24",
                "rdma1_100ge":    "100.1.1.0/24",
                "rdma2_100ge":    "100.1.2.0/24",
            },
            "plan": plan,
        }

    # ── 节点列表（表格展示用）────────────────────────────────────────────────

    def get_node_list(self) -> List[Dict]:
        nodes_json = self.read_nodes_json()
        role_order = {"pxe_host": 0, "master": 1, "slave": 2, "subswath": 3, "gstorage": 4}
        result = []
        for mac, node in nodes_json.items():
            if mac.startswith("_"):
                continue
            result.append({
                "mac":              mac,
                "hostname":         node.get("hostname_new", ""),
                "role":             node.get("role", ""),
                "ctrl_ip":          node.get("ctrl_ip", "").split("/")[0],
                "bmc_ip":           node.get("bmc_ip", ""),
                "rdma_nics":        node.get("rdma_nics", ""),
                "rdma_ips":         node.get("rdma_ips", ""),
                "dpdk_nics":        node.get("dpdk_nics", ""),
                "dpdk_ips":         node.get("dpdk_ips", ""),
                "system_disk":      node.get("system_disk", "/dev/sda"),
                "data_disks":       node.get("data_disks", ""),
                "data_raid_level":  node.get("data_raid_level", ""),
                "hugepages_1g":     node.get("hugepages_1g", "0"),
                "nfs_export_ip":    node.get("nfs_export_ip", ""),
                "nfs_mounts":       node.get("nfs_mounts", ""),
            })
        result.sort(key=lambda x: (role_order.get(x["role"], 99), x["hostname"]))
        return result


pxe_service_v2 = PXEServiceV2()
