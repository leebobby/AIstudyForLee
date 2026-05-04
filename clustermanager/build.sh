#!/bin/bash
# ============================================================
# Cluster Manager — 一键构建脚本
# 运行环境：OpenEuler / CentOS aarch64 (或同架构 Linux)
# 构建产物：backend/dist/cluster-manager/
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_DIR="$SCRIPT_DIR/backend"
DIST_DIR="$BACKEND_DIR/dist/cluster-manager"

echo "========================================"
echo " Cluster Manager 构建脚本"
echo " 工作目录: $SCRIPT_DIR"
echo "========================================"

# ── 步骤 1：构建前端 ─────────────────────────────────────────
echo ""
echo "[1/4] 安装前端依赖并构建..."
cd "$FRONTEND_DIR"
npm install --prefer-offline 2>/dev/null || npm install
npm run build
echo "  -> 前端已构建到 backend/static/"

# ── 步骤 2：安装 Python 依赖 ─────────────────────────────────
echo ""
echo "[2/4] 安装 Python 依赖..."
cd "$BACKEND_DIR"
pip install -r requirements.txt -q
pip install pyinstaller -q
echo "  -> Python 依赖安装完成"

# ── 步骤 3：PyInstaller 打包 ─────────────────────────────────
echo ""
echo "[3/4] PyInstaller 打包后端..."
cd "$BACKEND_DIR"
pyinstaller cluster_manager.spec --clean --noconfirm
echo "  -> 打包完成: $DIST_DIR"

# ── 步骤 4：整理发布目录 ─────────────────────────────────────
echo ""
echo "[4/4] 整理发布目录..."

# 写入启动脚本（让运维直接用 ./start.sh 启动）
cat > "$DIST_DIR/start.sh" << 'EOF'
#!/bin/bash
# Cluster Manager 启动脚本
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="${CLUSTER_MANAGER_HOST:-0.0.0.0}"
PORT="${CLUSTER_MANAGER_PORT:-8000}"

echo "Starting Cluster Manager on $HOST:$PORT ..."
echo "Frontend: http://$(hostname -I | awk '{print $1}'):$PORT"
echo "API Docs: http://$(hostname -I | awk '{print $1}'):$PORT/docs"
echo ""

./cluster-manager
EOF
chmod +x "$DIST_DIR/start.sh"

# 写入 systemd service 模板
cat > "$DIST_DIR/cluster-manager.service" << 'SVCEOF'
[Unit]
Description=Cluster Manager Service
After=network.target

[Service]
Type=simple
# 修改为实际部署路径
WorkingDirectory=/opt/cluster-manager
ExecStart=/opt/cluster-manager/cluster-manager
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
# 可选：以非 root 用户运行
# User=cluster
# Group=cluster

[Install]
WantedBy=multi-user.target
SVCEOF

echo "  -> start.sh 和 cluster-manager.service 已写入发布目录"

# ── 构建完成摘要 ─────────────────────────────────────────────
echo ""
echo "========================================"
echo " 构建成功！"
echo "========================================"
echo ""
echo " 发布目录: $DIST_DIR"
echo " 目录内容:"
ls -lh "$DIST_DIR" | grep -v "^total" | head -20
echo ""
echo " ── 部署到 OpenEuler ARM ──────────────"
echo " 1. 复制发布目录到目标机器："
echo "    scp -r $DIST_DIR root@<arm-ip>:/opt/cluster-manager"
echo ""
echo " 2. 直接运行："
echo "    ssh root@<arm-ip> '/opt/cluster-manager/start.sh'"
echo ""
echo " 3. 或注册为 systemd 服务（开机自启）："
echo "    scp $DIST_DIR/cluster-manager.service root@<arm-ip>:/etc/systemd/system/"
echo "    ssh root@<arm-ip> 'systemctl daemon-reload && systemctl enable --now cluster-manager'"
echo ""
echo " ── Windows 访问 ──────────────────────"
echo "    浏览器打开 http://<arm-ip>:8000"
echo "    API 文档:  http://<arm-ip>:8000/docs"
echo "========================================"
