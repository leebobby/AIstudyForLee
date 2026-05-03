"""
SSH诊断服务 - 远程命令执行 & 日志采集
"""

import os
from datetime import datetime
from typing import List, Dict

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


def _require_paramiko():
    if not PARAMIKO_AVAILABLE:
        raise RuntimeError("paramiko 未安装，请运行: pip install paramiko")


def _make_client(host: str, port: int, username: str, password: str) -> "paramiko.SSHClient":
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host, port=port,
        username=username, password=password,
        timeout=10, banner_timeout=30,
        allow_agent=False, look_for_keys=False
    )
    return client


def run_ssh_command(
    host: str, port: int, username: str, password: str,
    command: str, timeout: int = 30
) -> Dict:
    """SSH执行命令，返回 stdout/stderr/exit_code"""
    _require_paramiko()
    client = None
    try:
        client = _make_client(host, port, username, password)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        # 截断超长输出，避免前端渲染卡顿
        max_len = 50000
        if len(out) > max_len:
            out = out[:max_len] + f"\n\n[输出已截断，共 {len(out)} 字节]"
        return {
            "success": exit_code == 0,
            "stdout": out,
            "stderr": err[:5000] if err else "",
            "exit_code": exit_code
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1
        }
    finally:
        if client:
            client.close()


def collect_node_logs(
    host: str, port: int, username: str, password: str,
    log_paths: List[str], target_dir: str, node_name: str
) -> Dict:
    """
    从OpenEuler节点采集日志文件到Windows目录。

    log_paths 规则:
      - 以 "/" 开头 → SFTP 直接下载文件
      - 其他 → 作为 shell 命令执行，输出保存为 .log 文件
        (例: "dmesg", "journalctl --no-pager -n 2000")
    """
    _require_paramiko()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    node_dir = os.path.join(target_dir, node_name, timestamp)

    client = None
    file_results = []

    try:
        os.makedirs(node_dir, exist_ok=True)
        client = _make_client(host, port, username, password)
        sftp = client.open_sftp()

        for log_path in log_paths:
            if log_path.startswith('/'):
                # SFTP 文件下载
                filename = os.path.basename(log_path) or log_path.replace('/', '_').strip('_')
                local_path = os.path.join(node_dir, filename)
                try:
                    sftp.get(log_path, local_path)
                    size = os.path.getsize(local_path)
                    file_results.append({
                        "path": log_path,
                        "status": "success",
                        "local": local_path,
                        "size_kb": round(size / 1024, 1)
                    })
                except FileNotFoundError:
                    file_results.append({"path": log_path, "status": "not_found"})
                except PermissionError:
                    # 权限不足时尝试 sudo cat 读取
                    try:
                        _, stdout, stderr = client.exec_command(
                            f"sudo cat {log_path} 2>/dev/null", timeout=30
                        )
                        content = stdout.read().decode('utf-8', errors='replace')
                        with open(local_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        file_results.append({
                            "path": log_path,
                            "status": "success_sudo",
                            "local": local_path
                        })
                    except Exception as e2:
                        file_results.append({
                            "path": log_path, "status": "permission_denied",
                            "error": str(e2)
                        })
                except Exception as e:
                    file_results.append({"path": log_path, "status": "error", "error": str(e)})
            else:
                # 命令执行，保存输出
                safe_name = log_path.split()[0].replace('/', '_').strip('_') + '.log'
                local_path = os.path.join(node_dir, safe_name)
                try:
                    _, stdout, stderr = client.exec_command(log_path, timeout=60)
                    content = stdout.read().decode('utf-8', errors='replace')
                    err_content = stderr.read().decode('utf-8', errors='replace')
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        if err_content:
                            f.write(f"\n--- stderr ---\n{err_content}")
                    file_results.append({
                        "path": log_path,
                        "status": "success",
                        "local": local_path,
                        "size_kb": round(os.path.getsize(local_path) / 1024, 1)
                    })
                except Exception as e:
                    file_results.append({"path": log_path, "status": "error", "error": str(e)})

        sftp.close()
        return {
            "success": True,
            "node": node_name,
            "host": host,
            "target_dir": node_dir,
            "files": file_results
        }

    except Exception as e:
        return {
            "success": False,
            "node": node_name,
            "host": host,
            "error": str(e),
            "files": file_results
        }
    finally:
        if client:
            client.close()
