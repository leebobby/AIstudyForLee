import os
from pathlib import Path

# ── 千问 API ────────────────────────────────────────────
QWEN_API_KEY  = os.getenv("QWEN_API_KEY", "your-api-key-here")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 普通对话用 qwen-max，代码生成用 qwen-coder-plus
MODEL_CHAT  = "qwen-max"
MODEL_CODER = "qwen-coder-plus"

# ── 工作目录 ─────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
WORKSPACE_DIR = BASE_DIR / "workspace"   # 生成的 C++ 项目放这里

# ── Git 设置 ─────────────────────────────────────────────
GIT_AUTO_PUSH   = False          # True = 自动 push；False = 只 commit
GIT_REMOTE_NAME = "origin"
GIT_BRANCH      = "main"

# ── Agent 行为 ───────────────────────────────────────────
MAX_FIX_RETRIES       = 3        # 编译/测试失败最多重试几次
CLARIFY_THRESHOLD     = 0.6      # 置信度低于此值时向用户提问
CMAKE_BUILD_TYPE      = "Release"
