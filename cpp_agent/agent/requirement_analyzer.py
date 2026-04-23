"""
需求理解器
- 把模糊的自然语言需求解析成结构化 Spec
- 置信度不足时向用户提一个澄清问题
"""

import json
from dataclasses import dataclass, field
from typing import List
from openai import OpenAI
from config import QWEN_API_KEY, QWEN_BASE_URL, MODEL_CHAT, CLARIFY_THRESHOLD


@dataclass
class RequirementSpec:
    feature_name: str          # 英文下划线命名，用于文件名
    description:  str          # 一句话功能描述
    public_api:   List[str]    # 对外接口列表，如 ["push(T val)", "pop()->T"]
    edge_cases:   List[str]    # 需要处理的边界/异常情况
    confidence:   float = 1.0  # 0~1，模型对需求理解的置信度


_SYSTEM_PROMPT = """\
你是一名资深C++需求分析师。
用户给你一段需求描述（可能很模糊），你需要：
1. 理解用户真正想要的功能
2. 输出结构化分析结果（JSON格式）

输出字段说明：
- feature_name : 英文蛇形命名，用于文件名，如 thread_safe_queue
- description  : 一句话说清这个类/函数的功能
- public_api   : 对外接口列表，每条格式 "返回类型 方法名(参数)"，如 "void push(int val)"
- edge_cases   : 需要测试的边界/异常场景列表（至少3条）
- confidence   : 你对需求理解的置信度，0.0~1.0
- clarify_question : 若 confidence < 0.7，填写你需要向用户提问的一个最关键问题；否则填 null

只输出 JSON，不要有其他文字。\
"""


class RequirementAnalyzer:
    def __init__(self):
        self._client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

    def analyze(self, raw_requirement: str) -> RequirementSpec:
        """
        主入口：解析需求，必要时向用户提问，返回 RequirementSpec。
        """
        while True:
            spec_dict = self._call_llm(raw_requirement)
            confidence = spec_dict.get("confidence", 1.0)
            clarify_q  = spec_dict.get("clarify_question")

            if confidence < CLARIFY_THRESHOLD and clarify_q:
                print(f"\n[Analyzer] 需求有些模糊，请回答一个问题：")
                print(f"           {clarify_q}")
                answer = input("你的回答 > ").strip()
                raw_requirement = f"{raw_requirement}\n补充说明：{answer}"
            else:
                break

        return RequirementSpec(
            feature_name = spec_dict["feature_name"],
            description  = spec_dict["description"],
            public_api   = spec_dict.get("public_api", []),
            edge_cases   = spec_dict.get("edge_cases", []),
            confidence   = confidence,
        )

    def _call_llm(self, requirement: str) -> dict:
        resp = self._client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[
                {"role": "system",  "content": _SYSTEM_PROMPT},
                {"role": "user",    "content": requirement},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(resp.choices[0].message.content)
