# 严格工程质量体系实施计划

## 目标

在 `chore/engineering-quality-gates` 分支把已批准设计落地为可重复的本地、CI 和离线发布门禁。

## 全局约束

- 不改变 ff CLI 或公开引擎行为。
- 行为新增只发生在 distribution seam 与 `scripts/check_docs.py` 命令 seam，严格使用红—绿 TDD。
- 测试拆分与 Ruff 格式化属于行为不变重构；每批后运行相关测试并最终全量回归。
- Node 和开发依赖不得进入 `[project.dependencies]` 或 wheelhouse。
- 每项运行时、文档和发布声明同步更新全部权威文档。

## 阶段

### 1. Python 3.11 与 0.2.0 分发契约

1. 在 `tests/test_distribution.py` 增加 wheel metadata 失败测试：版本必须为 0.2.0，`Requires-Python` 必须为 `>=3.11`，onelog 范围保持兼容 0.1。
2. 运行单测确认因旧 metadata 失败。
3. 最小修改 `pyproject.toml` 使其通过。
4. 更新 README、需求、用户手册、验证矩阵与新增 ADR；ADR 只取代旧决策的 Python 版本部分，保留 packaged onelog 架构。

### 2. 测试能力拆分

1. 保存 `pytest --collect-only -q` 基线。
2. 按设计中的 8 个 engine 文件和 3 个 CLI 文件移动原测试函数，保留名字、参数和断言。
3. 删除空的旧测试文件，修复仓库内所有 node ID 和测试路径引用。
4. 比较收集数量并运行能力文件和完整回归。

### 3. Ruff、Pyright、覆盖率和 pre-commit

1. 在 `pyproject.toml` 添加固定 dev extra、Ruff 和 coverage 配置。
2. 添加私有 `package.json`、锁文件和 Pyright 配置；添加最小 `typings/onelog.pyi`。
3. 添加 pre-commit：commit 自动 Ruff format/check fix 与 Pyright，pre-push 完整覆盖率测试。
4. 对 `src/`、`tests/` 和 `scripts/` 执行一次格式化，逐项修复 lint/type 诊断，不改变行为。

### 4. 文档检查命令

1. 每个周期只增加一个 `tests/test_docs_check.py` 行为测试并确认失败。
2. 依次实现有效链接、缺失文件、fragment、HTML href/src、外部 URL 忽略和稳定诊断。
3. 添加 `scripts/check.sh` 汇总离线质量门禁。
4. 运行覆盖率；只为真实可观察分支补测试，不用无理由 pragma 游戏覆盖率。

### 5. CI、wheelhouse 与发布治理

1. 添加 GitHub Actions 三类 jobs 与 3.11–3.14 矩阵；只授予 contents: read。
2. 添加 `scripts/build-wheelhouse.sh`，从固定 onelog commit 构建完整 wheelhouse，在干净 venv 中离线安装 ff 0.2.0 并运行 `ff --help`。
3. 添加每周 pip/npm/github-actions Dependabot，只提 PR、不自动合并。
4. 添加 CHANGELOG、开发指南和人工发布清单，更新 AGENTS 的准确命令与版本门禁。

### 6. 验收

运行 Ruff format check、Ruff lint、Pyright、文档检查、90% branch coverage、`pip check`、Python 3.11 本地全量测试、wheelhouse 离线安装和 `git diff --check`。审查变更只覆盖本计划；保留 GitHub required checks 作为远端建立后的人工配置项。
