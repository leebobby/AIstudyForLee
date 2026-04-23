"""
代码生成器
- 根据 RequirementSpec 生成 .h / .cpp / CMakeLists.txt
- 使用 qwen-coder-plus（专用代码模型）
"""

import json
from pathlib import Path
from openai import OpenAI
from config import QWEN_API_KEY, QWEN_BASE_URL, MODEL_CODER
from agent.requirement_analyzer import RequirementSpec


_SYSTEM_PROMPT = """\
你是顶级C++工程师，专注于现代C++17/20最佳实践。
根据需求规格生成完整、可编译的C++代码。

输出严格JSON格式：
{
  "header": "完整的.h文件内容（含pragma once、所有include、类定义）",
  "source": "完整的.cpp文件内容（含include自己的.h）",
  "cmake": "完整的CMakeLists.txt内容"
}

代码要求：
- C++17标准
- 头文件有 #pragma once
- 类/函数有完整实现（不留TODO）
- 考虑线程安全（如需求涉及多线程）
- CMakeLists.txt 包含：主库 impl_lib、测试可执行文件 run_tests

只输出JSON，不要有其他文字。\
"""

_CMAKE_TEMPLATE = """\
cmake_minimum_required(VERSION 3.15)
project({name} VERSION 1.0)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 业务实现库（供测试复用）
add_library(impl_lib STATIC src/{name}.cpp)
target_include_directories(impl_lib PUBLIC src)

# 测试可执行文件
add_executable(run_tests tests/test_{name}.cpp)
target_link_libraries(run_tests PRIVATE impl_lib)

enable_testing()
add_test(NAME unit_tests COMMAND run_tests)\
"""


class CodeGenerator:
    def __init__(self):
        self._client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

    def generate(self, spec: RequirementSpec, project_dir: Path) -> dict:
        """
        生成代码文件并写入 project_dir，返回生成的文件路径字典。
        """
        print(f"[Generator] 使用 {MODEL_CODER} 生成代码...")

        raw = self._call_llm(spec)

        # 如果模型没返回 cmake，用模板补充
        if not raw.get("cmake"):
            raw["cmake"] = _CMAKE_TEMPLATE.format(name=spec.feature_name)

        # 写入文件
        src_dir   = project_dir / "src"
        tests_dir = project_dir / "tests"
        src_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        header_path = src_dir   / f"{spec.feature_name}.h"
        source_path = src_dir   / f"{spec.feature_name}.cpp"
        cmake_path  = project_dir / "CMakeLists.txt"

        header_path.write_text(raw["header"], encoding="utf-8")
        source_path.write_text(raw["source"], encoding="utf-8")
        cmake_path .write_text(raw["cmake"],  encoding="utf-8")

        print(f"[Generator] ✓ {header_path.name} ({_line_count(raw['header'])} 行)")
        print(f"[Generator] ✓ {source_path.name} ({_line_count(raw['source'])} 行)")
        print(f"[Generator] ✓ CMakeLists.txt")

        return {
            "header": header_path,
            "source": source_path,
            "cmake":  cmake_path,
        }

    def fix_code(self, spec: RequirementSpec, project_dir: Path,
                 error_msg: str) -> None:
        """编译失败时，读取现有代码 + 错误信息，让千问修复后覆盖写回。"""
        print(f"[Generator] 分析编译错误，尝试修复...")

        header_path = project_dir / "src" / f"{spec.feature_name}.h"
        source_path = project_dir / "src" / f"{spec.feature_name}.cpp"

        current_header = header_path.read_text(encoding="utf-8")
        current_source = source_path.read_text(encoding="utf-8")

        fix_prompt = f"""以下C++代码出现编译错误，请修复。

=== {spec.feature_name}.h ===
{current_header}

=== {spec.feature_name}.cpp ===
{current_source}

=== 编译错误 ===
{error_msg}

输出修复后的完整JSON：{{"header": "...", "source": "..."}}
只输出JSON。"""

        resp = self._client.chat.completions.create(
            model=MODEL_CODER,
            messages=[
                {"role": "system", "content": "你是C++专家，修复编译错误并输出JSON。"},
                {"role": "user",   "content": fix_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        fixed = json.loads(resp.choices[0].message.content)
        header_path.write_text(fixed["header"], encoding="utf-8")
        source_path.write_text(fixed["source"], encoding="utf-8")
        print(f"[Generator] ✓ 代码已修复")

    def _call_llm(self, spec: RequirementSpec) -> dict:
        prompt = f"""需求规格：
功能名称: {spec.feature_name}
功能描述: {spec.description}
公开接口: {json.dumps(spec.public_api, ensure_ascii=False)}
边界情况: {json.dumps(spec.edge_cases,  ensure_ascii=False)}"""

        resp = self._client.chat.completions.create(
            model=MODEL_CODER,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(resp.choices[0].message.content)


def _line_count(text: str) -> int:
    return len(text.splitlines())
