"""
Git 管理器
- 自动初始化仓库（如果不存在）
- git add 指定文件
- 千问生成规范 commit message
- git commit（可选 push）
"""

from pathlib import Path
from openai import OpenAI
import git
from config import QWEN_API_KEY, QWEN_BASE_URL, MODEL_CHAT, GIT_AUTO_PUSH, GIT_BRANCH
from agent.requirement_analyzer import RequirementSpec


class GitManager:
    def __init__(self, repo_dir: Path):
        self._client  = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)
        self._repo_dir = repo_dir
        self._repo     = self._init_repo(repo_dir)

    # ── 公开接口 ──────────────────────────────────────────

    def commit(self, spec: RequirementSpec, project_dir: Path) -> str:
        """
        把 project_dir 下的代码提交到仓库，返回 commit hash 短串。
        """
        # 要提交的文件
        files_to_add = [
            project_dir / "CMakeLists.txt",
            project_dir / "src"   / f"{spec.feature_name}.h",
            project_dir / "src"   / f"{spec.feature_name}.cpp",
            project_dir / "tests" / f"test_{spec.feature_name}.cpp",
        ]

        # git add
        for f in files_to_add:
            if f.exists():
                rel = str(f.relative_to(self._repo_dir))
                self._repo.index.add([rel])

        # 生成 commit message
        commit_msg = self._generate_commit_msg(spec)
        print(f"[GitManager] commit: {commit_msg}")

        # git commit
        self._repo.index.commit(commit_msg)
        short_hash = self._repo.head.commit.hexsha[:7]
        print(f"[GitManager] ✓ 已提交 {short_hash}")

        # push（可选）
        if GIT_AUTO_PUSH:
            self._push()

        return short_hash

    # ── 内部工具 ──────────────────────────────────────────

    def _generate_commit_msg(self, spec: RequirementSpec) -> str:
        """让千问生成符合 Conventional Commits 规范的 message。"""
        prompt = (
            f"为以下C++功能生成一行 git commit message（英文，Conventional Commits格式）：\n"
            f"功能：{spec.description}\n"
            f"接口：{', '.join(spec.public_api)}\n"
            f"只输出 commit message 本身，不要有其他文字。"
        )
        resp = self._client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip().strip('"')

    def _push(self):
        try:
            origin = self._repo.remote("origin")
            origin.push(GIT_BRANCH)
            print(f"[GitManager] ✓ 已 push 到 origin/{GIT_BRANCH}")
        except Exception as e:
            print(f"[GitManager] push 失败（可手动执行 git push）: {e}")

    @staticmethod
    def _init_repo(repo_dir: Path) -> git.Repo:
        repo_dir.mkdir(parents=True, exist_ok=True)
        try:
            repo = git.Repo(str(repo_dir))
        except git.InvalidGitRepositoryError:
            repo = git.Repo.init(str(repo_dir))
            print(f"[GitManager] 已初始化 git 仓库：{repo_dir}")
        return repo
