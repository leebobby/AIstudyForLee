"""
测试生成 + 运行器
- 让千问生成覆盖正常/边界/异常的测试文件
- 编译并运行，解析测试结果
- 失败时让千问分析原因并修复业务代码
"""

import json
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
from openai import OpenAI
from config import QWEN_API_KEY, QWEN_BASE_URL, MODEL_CODER, CMAKE_BUILD_TYPE
from agent.requirement_analyzer import RequirementSpec


@dataclass
class TestResult:
    success:    bool
    total:      int  = 0
    passed:     int  = 0
    failed:     int  = 0
    output:     str  = ""
    fail_names: List[str] = field(default_factory=list)


_SYSTEM_PROMPT = """\
你是C++测试专家。
根据提供的需求和代码，生成完整的测试文件（不依赖第三方框架，仅用标准C++）。

测试文件规则：
1. #include 对应的头文件（路径：../src/{feature_name}.h）
2. 每个测试是一个独立的 void test_xxx() 函数
3. 用 assert() 验证结果；失败时 assert 会 abort
4. 在 test 函数内捕获异常并 re-throw
5. main() 依次调用所有测试，全部通过打印 "ALL_TESTS_PASSED"，返回 0
6. 任一测试失败打印 "TEST_FAILED: <测试名>" 并返回 1
7. 覆盖：正常功能、边界值（空/满/极值）、并发（如有需要）

只输出纯C++代码，不要有markdown代码块标记。\
"""


class TestRunner:
    def __init__(self):
        self._client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

    # ── 公开接口 ──────────────────────────────────────────

    def generate_tests(self, spec: RequirementSpec, project_dir: Path) -> Path:
        """生成测试文件，写入 tests/ 目录，返回文件路径。"""
        print(f"[TestRunner] 千问生成测试用例...")

        header_code = (project_dir / "src" / f"{spec.feature_name}.h").read_text(encoding="utf-8")
        source_code = (project_dir / "src" / f"{spec.feature_name}.cpp").read_text(encoding="utf-8")

        prompt = f"""需求规格：
功能名称: {spec.feature_name}
功能描述: {spec.description}
公开接口: {json.dumps(spec.public_api, ensure_ascii=False)}
边界情况: {json.dumps(spec.edge_cases,  ensure_ascii=False)}

=== 头文件 {spec.feature_name}.h ===
{header_code}

=== 实现文件 {spec.feature_name}.cpp ===
{source_code}

请生成完整测试文件 test_{spec.feature_name}.cpp。"""

        resp = self._client.chat.completions.create(
            model=MODEL_CODER,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT.replace("{feature_name}", spec.feature_name)},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
        )
        test_code = _strip_code_fences(resp.choices[0].message.content)

        test_path = project_dir / "tests" / f"test_{spec.feature_name}.cpp"
        test_path.parent.mkdir(exist_ok=True)
        test_path.write_text(test_code, encoding="utf-8")
        print(f"[TestRunner] ✓ 测试文件已生成（{len(test_code.splitlines())} 行）")
        return test_path

    def run(self, project_dir: Path) -> TestResult:
        """编译 run_tests 并执行，解析结果。"""
        build_dir = project_dir / "build"

        # 先重新编译（确保测试文件也被编译进去）
        build_result = self._build(project_dir, build_dir)
        if not build_result["success"]:
            return TestResult(
                success=False, output=build_result["error"],
                fail_names=["[编译失败]"]
            )

        # 运行测试可执行文件
        exe = self._find_exe(build_dir)
        if exe is None:
            return TestResult(success=False, output="找不到测试可执行文件 run_tests")

        try:
            result = subprocess.run(
                [str(exe)], capture_output=True, text=True,
                timeout=30, encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return TestResult(success=False, output="测试超时（>30s）")

        output = result.stdout + result.stderr
        return self._parse_result(output, result.returncode)

    def fix_source(self, spec: RequirementSpec, project_dir: Path,
                   test_output: str) -> None:
        """测试失败时，让千问修复业务代码（不修改测试）。"""
        print(f"[TestRunner] 分析测试失败，修复业务代码...")

        header_path = project_dir / "src" / f"{spec.feature_name}.h"
        source_path = project_dir / "src" / f"{spec.feature_name}.cpp"
        test_path   = project_dir / "tests" / f"test_{spec.feature_name}.cpp"

        prompt = f"""以下C++代码未能通过测试，请修复业务代码（不要修改测试文件）。

=== 头文件 ===
{header_path.read_text(encoding='utf-8')}

=== 实现文件 ===
{source_path.read_text(encoding='utf-8')}

=== 测试文件（只读，不要修改）===
{test_path.read_text(encoding='utf-8')}

=== 测试失败输出 ===
{test_output}

输出修复后的JSON：{{"header": "完整头文件内容", "source": "完整实现文件内容"}}
只输出JSON。"""

        resp = self._client.chat.completions.create(
            model=MODEL_CODER,
            messages=[
                {"role": "system", "content": "你是C++专家，修复业务逻辑使测试通过，输出JSON。"},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        fixed = json.loads(resp.choices[0].message.content)
        header_path.write_text(fixed["header"], encoding="utf-8")
        source_path.write_text(fixed["source"], encoding="utf-8")
        print(f"[TestRunner] ✓ 业务代码已修复")

    # ── 内部工具 ──────────────────────────────────────────

    def _build(self, project_dir: Path, build_dir: Path) -> dict:
        result = subprocess.run(
            ["cmake", "--build", str(build_dir),
             "--config", CMAKE_BUILD_TYPE, "--parallel"],
            cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace",
        )
        return {
            "success": result.returncode == 0,
            "error":   result.stdout + result.stderr,
        }

    @staticmethod
    def _find_exe(build_dir: Path):
        for name in ["run_tests", "run_tests.exe",
                     f"Release/run_tests.exe", f"Debug/run_tests.exe"]:
            p = build_dir / name
            if p.exists():
                return p
        return None

    @staticmethod
    def _parse_result(output: str, returncode: int) -> TestResult:
        passed     = len(re.findall(r"✓|PASSED|passed|OK", output))
        fail_names = re.findall(r"TEST_FAILED:\s*(\S+)", output)
        failed     = len(fail_names)
        total      = passed + failed if (passed + failed) > 0 else (0 if returncode != 0 else 1)

        success = returncode == 0 and "ALL_TESTS_PASSED" in output

        if success:
            print(f"[TestRunner] ✓ 全部 {total} 个测试通过")
        else:
            print(f"[TestRunner] ✗ {failed} 个测试失败")
            for name in fail_names:
                print(f"[TestRunner]   - {name}")

        return TestResult(
            success=success, total=total,
            passed=passed, failed=failed,
            output=output, fail_names=fail_names,
        )


def _strip_code_fences(text: str) -> str:
    """移除 ```cpp ... ``` 包裹"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end -= 1
        return "\n".join(lines[start:end])
    return text
