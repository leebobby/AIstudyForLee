"""
桌面版启动器 — 后台启动 FastAPI/uvicorn，前台用 pywebview 打开原生窗口。

打包后双击 cluster-manager.exe 不会出现浏览器，而是一个标题为
"Cluster Manager" 的原生窗口（Windows 10/11 使用 Edge WebView2 渲染）。

开发模式: python desktop.py
服务模式: python main.py   (仍可作为纯后端运行)
"""

import os
import sys
import time
import socket
import threading
import urllib.request


# ── 冻结模式下把日志重定向到文件（console=False 时仍可排查问题）─────────
def _setup_logging():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        log_path = os.path.join(base, "cluster_manager.log")
        try:
            f = open(log_path, "a", encoding="utf-8", buffering=1)
            sys.stdout = f
            sys.stderr = f
        except Exception:
            pass


_setup_logging()

import webview
import uvicorn
from main import app

HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("CLUSTER_MANAGER_PORT", "8000"))


def _port_available(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((HOST, port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _pick_port(start: int) -> int:
    for p in range(start, start + 50):
        if _port_available(p):
            return p
    return start


def _wait_for_server(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).close()
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _run_server(port: int):
    uvicorn.run(app, host=HOST, port=port, log_level="info")


def main():
    port = _pick_port(DEFAULT_PORT)
    print(f"[desktop] starting backend on http://{HOST}:{port}")
    threading.Thread(target=_run_server, args=(port,), daemon=True).start()

    base_url = f"http://{HOST}:{port}"
    if not _wait_for_server(f"{base_url}/api/health"):
        print(f"[desktop][error] backend failed to start at {base_url}", file=sys.stderr)
        sys.exit(1)

    print(f"[desktop] opening webview window -> {base_url}")
    webview.create_window(
        title="Cluster Manager",
        url=base_url,
        width=1400,
        height=900,
        min_size=(1024, 700),
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
