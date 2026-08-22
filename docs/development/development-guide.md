# ff 开发指南

## 环境

开发和 CI 使用 CPython 3.11+；兼容矩阵覆盖 3.11–3.14。Pyright 需要
Node 24，但 Node 不属于 ff 运行时或发布制品。Linux 与 WSL2 均受支持；
在 WSL2 中优先把仓库放在 Linux 文件系统以获得更稳定的权限语义和性能。
`.[dev]` 同时安装精确版本的 `setuptools` 和 `wheel`，因为分发
测试使用 `pip wheel --no-build-isolation` 验证当前开发环境的打包 seam。
这两项仍是开发工具，不进入 esim 的运行依赖或离线 wheelhouse。

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install \
  "git+https://github.com/BottiCelle/onelog.git@d60dc49701944d88c90f3bd7fabf5bbbdb7d6f8c"
.venv/bin/python -m pip install -e ".[dev]"
npm ci
.venv/bin/pre-commit install --hook-type pre-commit --hook-type pre-push
```

固定源码提交的仓库名是 BottiCelle/onelog，Python 发行名是
`onelogg`，Python 导入名仍是 `onelog`。修改 Python 最低版本、运行依赖或固定提交前，必须先取得
用户决定并同步需求、README、用户文档、ADR 和发布文档。

esim 使用 `PyYAML>=6.0,<7` 安全解析 TC/Rules 并生成运行快照；
该 wheel 必须与其他运行依赖一起收入离线 wheelhouse。

## 测试与质量门禁

```bash
# 全量本地门禁，也是 CI quality job 的唯一入口
bash scripts/check.sh

# 一个稳定能力
.venv/bin/python -m pytest tests/test_engine_conditions.py

# 一条精确用例
.venv/bin/python -m pytest \
  tests/test_engine_conditions.py::test_elsif_keeps_first_matching_alternative_branch

# 临时跨能力筛选
.venv/bin/python -m pytest tests/test_engine_*.py -k 'symlink or output_parent'
```

commit hook 自动执行 Ruff format、Ruff check 安全修复和 Pyright；pre-push
hook 执行完整 branch coverage 回归。hook 不能替代交付前显式执行
`scripts/check.sh`。

## 离线 wheelhouse

输出目录必须为空，避免混入旧 wheel：

```bash
FF_PYTHON=.venv/bin/python \
  bash scripts/build-wheelhouse.sh /tmp/esim-wheelhouse
```

命令从固定 onelog commit 构建 `onelogg` wheel，收集 Rich、PyYAML 及传递依赖，构建 esim 0.2.0，
在干净 venv 中使用 `--no-index` 安装并运行 `ff --help` 与
`esim --help`，最后生成
`SHA256SUMS`。开发依赖和 Node 不进入 wheelhouse。

## CI

GitHub Actions 在 pull request、main push 和手工触发时运行常规门禁：

- `python`：CPython 3.11–3.14 测试矩阵；
- `quality`：Node 24、Ruff、Pyright、文档检查和 branch coverage；
- `package`：仅手工触发或发布时构建完整离线 wheelhouse，
  执行干净安装 smoke test 并上传制品。

工作流权限仅为 `contents: read`。仓库建立远端后，由维护者把上述 jobs 配置为
main 分支 required checks。

正式发布前逐项执行[人工发布清单](release-checklist.md)。
