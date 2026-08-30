# ff 开发指南

## 环境

开发和 CI 使用 CPython 3.11+；兼容矩阵覆盖 3.11–3.14。Pyright 需要
Node 24，但 Node 不属于 ff 运行时或发布制品。Linux 与 WSL2 均受支持；
在 WSL2 中优先把仓库放在 Linux 文件系统以获得更稳定的权限语义和性能。
`.[dev]` 同时安装精确版本的 `setuptools` 和 `wheel`，因为分发
测试通过 `tools/packaging/build-wheel.sh` 使用 `pip wheel --no-build-isolation`
验证当前开发环境的打包 seam。
这两项仍是开发工具，不进入 esim 的运行依赖或离线 wheelhouse。
`markdown-it-py` 和 `Pygments` 也是固定版本开发依赖，只用于从 User Guide
Markdown 内容源生成带构建期语法高亮的 standalone HTML，不进入运行依赖或
wheelhouse。

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install \
  "git+https://github.com/BottiCelle/onelog.git@d60dc49701944d88c90f3bd7fabf5bbbdb7d6f8c"
.venv/bin/python -m pip install -e ".[dev]"
npm --prefix tools/typecheck ci
.venv/bin/pre-commit install --hook-type pre-commit
```

固定源码提交的仓库名是 BottiCelle/onelog，Python 发行名是
`onelogg`，Python 导入名仍是 `onelog`。修改 Python 最低版本、运行依赖或固定提交前，必须先取得
用户决定并同步需求、README、用户文档、ADR 和发布文档。

esim 使用 `PyYAML>=6.0,<7` 安全解析 TC/Rules 并生成运行快照；
该 wheel 必须与其他运行依赖一起收入离线 wheelhouse。

## 测试与质量门禁

```bash
# 创建 release tag 前的全量本地门禁
bash tools/quality/check.sh

# 更新或检查 ff/esim 双格式 User Guide
.venv/bin/python tools/docs/generate_user_guides.py
.venv/bin/python tools/docs/generate_user_guides.py --check

# 一个稳定能力
.venv/bin/python -m pytest tests/test_engine_conditions.py

# 一条精确用例
.venv/bin/python -m pytest \
  tests/test_engine_conditions.py::test_elsif_keeps_first_matching_alternative_branch

# 临时跨能力筛选
.venv/bin/python -m pytest tests/test_engine_*.py -k 'symlink or output_parent'

# 本地 feature 开发的快速语法/格式检查（可换成本次修改的具体文件）
.venv/bin/ruff format --check src tests scripts
.venv/bin/ruff check src tests scripts
```

feature 开发期间只执行新增/受影响测试和 Ruff，不要在每次本地交付时运行
全量回归。commit hook 自动执行 Ruff format 和 Ruff check 安全修复；
本地 pre-push 不执行 coverage。创建 release tag 前必须通过 `tools/quality/check.sh`
执行 Pyright、文档检查、完整 branch coverage 回归和 `pip check`。
PR CI 使用同一入口作为远程合入门槛。
该门禁同时要求两份生成 HTML 与 Markdown 内容源完全同步。

### User Guide 章节规范

User Guide Markdown 必须使用固定层级，不能把所有主题平铺为同级标题：

```markdown
# <tool> User Guide

## 第一章 入门 {#getting-started}

### 快速开始 {#quick-start}

#### 可选的节内小节
```

- H2 是章，单份指南至少包含两章。
- 每个 H2 章至少包含一个 H3 节；H3 会进入两级章节导航。
- H4 只用于节内局部结构，不进入主导航。
- 章和节均使用显式稳定 ID；调整章节归属时保留既有节 ID。

生成器会拒绝少于两章或存在空章的平铺文档，因此该规范由
`tools/quality/check.sh` 和 CI 强制执行，而不只依赖人工审阅。

## 离线 wheelhouse

只构建本项目 wheel 时使用隔离入口；脚本将打包所需源码复制到临时目录，
因此不会在项目 checkout 中创建或刷新 `build/`、`src/esim.egg-info/`：

```bash
FF_PYTHON=.venv/bin/python \
  bash tools/packaging/build-wheel.sh /tmp/esim-wheel
```

输出目录必须为空，避免混入旧 wheel：

```bash
FF_PYTHON=.venv/bin/python \
  bash tools/packaging/build-wheelhouse.sh /tmp/esim-wheelhouse
```

命令从固定 onelog commit 构建 `onelogg` wheel，收集 Rich、PyYAML 及传递依赖，构建 esim 0.2.0，
在干净 venv 中使用 `--no-index` 安装并运行 `ff --help` 与
`esim --help`，最后生成
`SHA256SUMS`。开发依赖和 Node 不进入 wheelhouse。
wheelhouse 脚本复用上述隔离入口；GitHub Actions 的 Python 测试矩阵和
package job 因此验证同一条本地 wheel 构建路径。

## CI

GitHub Actions 在 pull request、main push 和手工触发时运行常规门禁：

- `python`：CPython 3.11–3.14 测试矩阵；
- `quality`：Node 24、Ruff、Pyright、文档检查和 branch coverage；
- `package`：仅手工触发或发布时构建完整离线 wheelhouse，
  执行干净安装 smoke test 并上传制品。

工作流权限仅为 `contents: read`。仓库建立远端后，由维护者把上述 jobs 配置为
main 分支 required checks。

正式发布前逐项执行[人工发布清单](release-checklist.md)。
