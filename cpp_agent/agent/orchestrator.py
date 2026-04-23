"""
主流程编排器 (Orchestrator)
把 5 个模块串起来，含重试逻辑和状态打印。
"""

import time
from dataclasses import dataclass
from pathlib import Path
from config import WORKSPACE_DIR, MAX_FIX_RETRIES
from agent.requirement_analyzer import RequirementAnalyzer
from agent.code_generator       import CodeGenerator
from agent.build_system         import BuildSystem
from agent.test_runner          import TestRunner
from agent.git_manager          import GitManager


@dataclass
class AgentResult:
    success:     bool
    commit_hash: str  = ""
    project_dir: Path = None
    elapsed_sec: float = 0.0
    message:     str  = ""


class Orchestrator:
    def __init__(self):
        self._analyzer  = RequirementAnalyzer()
        self._generator = CodeGenerator()
        self._builder   = BuildSystem()
        self._tester    = TestRunner()
        self._git       = GitManager(WORKSPACE_DIR)

    def run(self, requirement: str) -> AgentResult:
        t0 = time.time()

        # ── Step 1: 需求理解 ───────────────────────────────
        _section("需求理解")
        spec = self._analyzer.analyze(requirement)
        print(f"[Analyzer] ✓ 功能: {spec.feature_name}")
        print(f"[Analyzer] ✓ 描述: {spec.description}")
        print(f"[Analyzer] ✓ 接口: {len(spec.public_api)} 个")

        # 为这个功能创建独立工作目录
        project_dir = WORKSPACE_DIR / spec.feature_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # ── Step 2: 生成代码 ───────────────────────────────
        _section("代码生成")
        self._generator.generate(spec, project_dir)

        # ── Step 3: 编译（含重试）─────────────────────────
        _section("编译构建")
        for attempt in range(1, MAX_FIX_RETRIES + 1):
            build_result = self._builder.configure_and_build(project_dir)
            if build_result:
                break
            if attempt == MAX_FIX_RETRIES:
                return AgentResult(
                    success=False,
                    message=f"编译失败（已重试 {MAX_FIX_RETRIES} 次），需要人工介入。\n{build_result.error}",
                    elapsed_sec=time.time() - t0,
                )
            print(f"[Builder] ✗ 第 {attempt} 次编译失败，千问修复中...")
            self._generator.fix_code(spec, project_dir, build_result.error)

        # ── Step 4: 生成并运行测试（含重试）───────────────
        _section("测试")
        self._tester.generate_tests(spec, project_dir)

        for attempt in range(1, MAX_FIX_RETRIES + 1):
            # 每次测试前重新编译（包含测试文件）
            rebuild = self._builder.build_tests(project_dir)
            if not rebuild:
                print(f"[TestRunner] 测试文件编译失败，修复中...")
                self._generator.fix_code(spec, project_dir, rebuild.error)
                continue

            test_result = self._tester.run(project_dir)
            if test_result.success:
                break
            if attempt == MAX_FIX_RETRIES:
                return AgentResult(
                    success=False,
                    message=f"测试未通过（已重试 {MAX_FIX_RETRIES} 次），需要人工介入。\n{test_result.output}",
                    elapsed_sec=time.time() - t0,
                )
            print(f"[TestRunner] ✗ 第 {attempt} 次测试失败，千问修复中...")
            self._tester.fix_source(spec, project_dir, test_result.output)

        # ── Step 5: 上库 ───────────────────────────────────
        _section("提交上库")
        commit_hash = self._git.commit(spec, project_dir)

        elapsed = time.time() - t0
        return AgentResult(
            success=True,
            commit_hash=commit_hash,
            project_dir=project_dir,
            elapsed_sec=elapsed,
            message=(
                f"✅ 任务完成！\n"
                f"   Commit   : {commit_hash}\n"
                f"   项目目录 : {project_dir}\n"
                f"   文件     : src/{spec.feature_name}.h  src/{spec.feature_name}.cpp\n"
                f"   测试     : tests/test_{spec.feature_name}.cpp\n"
                f"   耗时     : {elapsed:.1f}s"
            ),
        )


def _section(name: str):
    print(f"\n{'─'*40}")
    print(f"  {name}")
    print(f"{'─'*40}")
