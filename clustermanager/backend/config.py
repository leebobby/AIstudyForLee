"""
运行时路径解析 — 同时兼容：
  1. 开发模式  : python main.py（__file__ 在 backend/）
  2. PyInstaller: ./cluster-manager（sys.executable 在部署目录）
"""

import os
import sys


def _base_dir() -> str:
    if getattr(sys, 'frozen', False):
        # PyInstaller onedir: sys.executable = <deploy_dir>/cluster-manager
        return os.path.dirname(sys.executable)
    # 开发模式: 此文件位于 backend/
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR     = _base_dir()
DATABASE_PATH = os.path.join(BASE_DIR, 'cluster_manager.db')
PXE_DATA_DIR  = os.path.join(BASE_DIR, 'pxe_data')
STATIC_DIR    = os.path.join(BASE_DIR, 'static')
