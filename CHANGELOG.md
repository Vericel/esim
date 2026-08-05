# Changelog

本项目遵循 Semantic Versioning。所有面向用户的重要变化记录在此文件。

## Unreleased

## 0.2.0 - 2026-08-03

### Changed

- 最低运行版本提升为 CPython 3.11，正式支持 Linux 和 WSL2。
- 项目和 Python 分发名统一为 `esim`，独立 `ff` 命令保持可用。
- onelog 运行依赖使用正式 PyPI 分发 `onelogg>=0.1.1,<0.2`，Python 导入名
  保持 `onelog`；CI 和离线 wheelhouse 固定收集 onelogg 0.1.1。

### Added

- GitHub Actions、Dependabot 和统一的本地质量门禁。
- 完整离线 wheelhouse 构建、校验和与干净环境 smoke test。
- Ruff、Pyright、pre-commit 和 90% branch coverage 门禁。
- 按 public seam 与稳定能力拆分的可选择回归测试。
- Markdown/HTML 本地链接和 fragment 检查命令。
