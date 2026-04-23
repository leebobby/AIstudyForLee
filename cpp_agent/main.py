"""
C++ 自主开发 Agent — 启动入口

用法：
  python main.py                         # 交互模式，手动输入需求
  python main.py "实现一个LRU缓存"         # 直接传入需求
"""

import sys
from agent.orchestrator import Orchestrator


BANNER = """
╔══════════════════════════════════════════════════════╗
║           C++ 自主开发 Agent                          ║
║   大脑: 通义千问  |  构建: CMake  |  上库: Git         ║
╚══════════════════════════════════════════════════════╝

功能：你给需求（哪怕很模糊），Agent 自动完成：
  理解需求 → 生成C++代码 → 编译 → 自测试 → 上库

输入 quit 退出。
"""


def main():
    print(BANNER)

    agent = Orchestrator()

    # 支持命令行直接传参
    if len(sys.argv) > 1:
        requirements = [" ".join(sys.argv[1:])]
    else:
        requirements = None

    while True:
        if requirements:
            req = requirements.pop(0)
            print(f"需求：{req}")
        else:
            req = input("\n请输入需求 > ").strip()
            if not req or req.lower() in ("quit", "exit", "q"):
                print("再见！")
                break

        result = agent.run(req)
        print(f"\n{'═'*54}")
        print(result.message)
        print(f"{'═'*54}\n")

        if requirements is not None and not requirements:
            break


if __name__ == "__main__":
    main()
