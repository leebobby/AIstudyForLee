# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置 — Cluster Manager (OpenEuler aarch64)
# 构建命令：在 backend/ 目录下执行 pyinstaller cluster_manager.spec --clean

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Vue 构建产物（npm run build 后生成）
        ('static', 'static'),
    ],
    hiddenimports=[
        # uvicorn 协议/循环实现
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.off',
        'uvicorn.lifespan.on',
        # SQLAlchemy SQLite 方言
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'sqlalchemy.sql.default_comparator',
        # Pydantic v2
        'pydantic.deprecated.class_validators',
        'pydantic.deprecated.config',
        'pydantic.deprecated.tools',
        # aiohttp
        'aiohttp',
        'aiohttp.client',
        # paramiko（SSH 执行诊断脚本）
        'paramiko',
        'paramiko.transport',
        # 标准库
        'email.mime.multipart',
        'email.mime.text',
        '_sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'PIL',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cluster-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # aarch64 下 UPX 支持有限，关闭
    console=True,     # 保留控制台输出以便查看日志
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# onedir 模式：生成 dist/cluster-manager/ 目录（含二进制 + static/）
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='cluster-manager',
)
