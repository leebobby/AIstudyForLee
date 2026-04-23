"""
编译构建系统
- 自动检测 CMake 和编译器
- cmake 配置 + 编译
- 返回成功/失败 + 错误信息
"""

import subprocess
import shutil
from pathlib import Path
from config import CMAKE_BUILD_TYPE


class BuildResult:
    def __init__(self, success: bool, output: str = "", error: str = ""):
        self.success = success
        self.output  = output
        self.error   = error

    def __bool__(self):
        return self.success


class BuildSystem:
    def __init__(self):
        self._cmake = self._find_cmake()

    # ── 公开接口 ──────────────────────────────────────────

    def configure_and_build(self, project_dir: Path) -> BuildResult:
        """cmake 配置 + 编译，返回 BuildResult。"""
        build_dir = project_dir / "build"
        build_dir.mkdir(exist_ok=True)

        print(f"[Builder] cmake 配置中...")
        cfg = self._run(
            [self._cmake, "-S", str(project_dir),
             "-B", str(build_dir),
             f"-DCMAKE_BUILD_TYPE={CMAKE_BUILD_TYPE}"],
            project_dir,
        )
        if not cfg.success:
            return cfg

        print(f"[Builder] cmake 编译中...")
        build = self._run(
            [self._cmake, "--build", str(build_dir),
             "--config", CMAKE_BUILD_TYPE,
             "--parallel"],
            project_dir,
        )
        if build.success:
            print(f"[Builder] ✓ 编译成功")
        return build

    def build_tests(self, project_dir: Path) -> BuildResult:
        """单独重新编译（用于修复代码后重编）。"""
        build_dir = project_dir / "build"
        return self._run(
            [self._cmake, "--build", str(build_dir),
             "--config", CMAKE_BUILD_TYPE,
             "--parallel"],
            project_dir,
        )

    # ── 内部工具 ──────────────────────────────────────────

    def _run(self, cmd: list, cwd: Path) -> BuildResult:
        try:
            result = subprocess.run(
                cmd, cwd=str(cwd),
                capture_output=True, text=True,
                timeout=120, encoding="utf-8", errors="replace",
            )
            combined = result.stdout + result.stderr
            if result.returncode == 0:
                return BuildResult(True, combined)
            else:
                return BuildResult(False, result.stdout, result.stderr)
        except FileNotFoundError as e:
            return BuildResult(False, "", str(e))
        except subprocess.TimeoutExpired:
            return BuildResult(False, "", "编译超时（>120s）")

    @staticmethod
    def _find_cmake() -> str:
        cmake = shutil.which("cmake")
        if cmake:
            return cmake
        # Windows 常见安装路径
        fallbacks = [
            r"C:\Program Files\CMake\bin\cmake.exe",
            r"C:\Program Files (x86)\CMake\bin\cmake.exe",
        ]
        for path in fallbacks:
            if Path(path).exists():
                return path
        raise EnvironmentError(
            "未找到 cmake，请安装：winget install cmake\n"
            "安装后重启终端再运行。"
        )
