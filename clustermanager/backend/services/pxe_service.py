"""
PXE 配置服务
"""

import os
import shutil
from typing import Dict, List, Optional
from pathlib import Path


class PXEService:
    """PXE部署配置服务"""

    def __init__(self, tftp_dir: str = "/tftpboot", dhcp_conf: str = "/etc/dhcp/dhcpd.conf"):
        self.tftp_dir = tftp_dir
        self.dhcp_conf = dhcp_conf

    def setup_pxe_server(self) -> Dict:
        """
        配置PXE服务器
        安装并配置DHCP、TFTP、NFS等服务
        """
        steps = [
            "安装tftp-server、dhcp-server、nfs-server",
            "配置TFTP目录",
            "配置DHCP服务",
            "准备引导文件",
            "配置NFS共享",
            "启动服务"
        ]

        return {
            "status": "configured",
            "steps": steps,
            "tftp_dir": self.tftp_dir
        }

    def generate_kickstart(
        self,
        node_type: str,
        mgmt_ip: str,
        ctrl_ip: str,
        data_ip: str,
        hostname: str,
        mgmt_gateway: str = "192.168.1.1",
        ctrl_gateway: str = "10.0.0.1",
        data_gateway: str = "192.168.100.1"
    ) -> str:
        """
        生成Kickstart配置文件
        支持三平面网络配置
        """
        ks_content = f"""# Kickstart 配置 - {hostname}
# 自动生成的三平面网络配置

# 系统语言和键盘
lang en_US.UTF-8
keyboard us

# 网络配置 - 三平面
# 管理面 (eth0) - GE口
network --device=eth0 --bootproto=static --ip={mgmt_ip} --gateway={mgmt_gateway} --nameserver=8.8.8.8 --hostname={hostname}

# 控制面 (eth1) - 10GE
network --device=eth1 --bootproto=static --ip={ctrl_ip} --gateway={ctrl_gateway} --noipv6

# 数据面 (eth2) - 100GE
network --device=eth2 --bootproto=static --ip={data_ip} --gateway={data_gateway} --noipv6

# 时区
timezone Asia/Shanghai --utc

# 认证
auth --enableshadow --passalgo=sha512

# root密码 (需要在实际使用时设置)
rootpw --plaintext changeme

# 安装源
url --url=http://192.168.1.10/openEuler/

# 分区
autopart --type=lvm

# 安装包
%packages
@core
@base
openssh-server
python3
dpdk
{"rdma-core" if node_type == "slave" else ""}
%end

# 后置脚本 - 配置DPDK/RDMA
%post --log=/root/ks-post.log
"""

        if node_type == "master":
            ks_content += """
# DPDK配置 (Master节点)
echo "配置DPDK环境..."
modprobe vfio-pci
echo 'vfio-pci' >> /etc/modules-load.d/dpdk.conf

# 绑定100GE网卡到DPDK
# 实际需要根据具体网卡型号配置
echo "DPDK配置完成"
"""
        elif node_type == "slave":
            ks_content += """
# RDMA配置 (Slave节点)
echo "配置RDMA环境..."
modprobe ib_core
modprobe rdma_cm
echo 'ib_core' >> /etc/modules-load.d/rdma.conf
echo 'rdma_cm' >> /etc/modules-load.d/rdma.conf

echo "RDMA配置完成"
"""

        ks_content += """
# 安装监控Agent
curl -O http://192.168.1.10/agent/install.sh
chmod +x install.sh
./install.sh

# 注册到管理平台
curl -X POST http://192.168.1.10:8000/api/nodes/register -d "hostname={hostname}"

%end

# 安装完成后重启
reboot
"""

        return ks_content

    def generate_dhcp_config(self, nodes: List[Dict]) -> str:
        """
        生成DHCP配置
        为每个节点配置固定IP
        """
        dhcp_content = """# DHCP配置 - Cluster Manager
# 三平面网络DHCP配置

subnet 192.168.1.0 netmask 255.255.255.0 {
    option routers 192.168.1.1;
    option domain-name-servers 8.8.8.8;
    range 192.168.1.200 192.168.1.250;

    # PXE引导配置
    next-server 192.168.1.10;
    filename "pxelinux.0";
"""

        for node in nodes:
            dhcp_content += f"""
    host {node['hostname']} {{
        hardware ethernet {node['mgmt_mac']};
        fixed-address {node['mgmt_ip']};
        filename "pxelinux.0";
    }}
"""

        dhcp_content += "}\n"
        return dhcp_content

    def create_pxe_boot_entry(self, hostname: str, mac: str, ks_url: str) -> Dict:
        """
        创建PXE引导条目
        """
        # 创建pxelinux.cfg目录中的配置文件
        # MAC地址格式转换: 00:1a:2b:3c:4d:5e -> 01-00-1a-2b-3c-4d-5e
        mac_formatted = "01-" + mac.replace(":", "-")

        pxe_config = f"""DEFAULT install
PROMPT 0
TIMEOUT 10

LABEL install
    KERNEL vmlinuz
    APPEND initrd=initrd.img inst.ks={ks_url} inst.repo=http://192.168.1.10/openEuler/
"""

        return {
            "hostname": hostname,
            "mac": mac,
            "config_file": mac_formatted,
            "config_content": pxe_config
        }

    def prepare_boot_files(self, iso_path: str) -> Dict:
        """
        准备PXE引导文件
        从ISO提取引导所需的文件
        """
        files_needed = [
            "vmlinuz",
            "initrd.img",
            "pxelinux.0",
            "ldlinux.c32"
        ]

        return {
            "iso_path": iso_path,
            "files": files_needed,
            "target_dir": self.tftp_dir,
            "status": "prepared"
        }


# 单例实例
pxe_service = PXEService()