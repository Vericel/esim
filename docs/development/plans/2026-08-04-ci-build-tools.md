# CI build tools implementation plan

## 目标

修复 GitHub Actions 中 CPython 3.12–3.14 的分发测试，使所有受支持
Python 版本都具备测试直接调用的 PEP 517 构建工具。

## 根因

Python 3.12 起 `venv` 不再默认提供 `setuptools`。`test_distribution.py`
显式使用 `pip wheel --no-build-isolation`，因此测试环境本身必须安装
`setuptools` 和 `wheel`。当前 `.[dev]` 没有声明这两项直接开发依赖。

## 实施

1. 在 `.[dev]` 中以精确版本声明 `setuptools` 和 `wheel`。
2. 在开发指南和验证文档中说明分发测试的构建工具前提。
3. 在干净 CPython 3.11–3.14 环境中验证分发测试，再运行完整
   `scripts/check.sh`。
4. 提交并推送 `main`，跟踪 GitHub Actions 直至完成。

## 边界

- 不改变 Python 最低版本或运行依赖。
- 不将开发构建工具收入发布 wheelhouse。
- 不修改 `ff` 公开行为。
