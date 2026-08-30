# Changelog

本项目遵循 Semantic Versioning。所有面向用户的重要变化记录在此文件。

## Unreleased

### Changed

- 日志运行依赖迁移到带 PEP 561 内联类型的
  `onelogg>=0.1.2,<0.2`，删除重复的本地 `onelog` stub。
- 简化 esim TC/Rules phase hooks：`before`/`after` 直接使用命令列表，
  `continue_on_error` 上移到 hooks 层并同时作用于两个列表。
- 将 demo 中覆盖 two-step TC 全部受支持字段的参考实体统一为
  `complete.tc`，并保留 `complete.yaml` 相对符号链接。

### Added

- 新增 `esim` CLI，支持 TC/Rules YAML 组合、VCS two-step/three-step、
  hooks、统一日志判定、waiver 合并、stage action 和独立 `check`。
- 新增 `PyYAML>=6.0,<7` 运行依赖，仅使用 safe load/dump 解析配置。
- 新增 VS Code 与 Vim/gVim 编辑器支持，将 `*.tc` 和 `*.rules`
  按标准 YAML 语法高亮。
- ff 与 esim User Guide 现在同时提供 Markdown 和可离线打开的 HTML，
  HTML 从唯一 Markdown 内容源确定性生成，并提供 YAML/Bash 语法高亮、
  代码语言标签、篇章结构和响应式两级章节导航。

## 0.2.0 - 2026-08-03

### Changed

- 最低运行版本提升为 CPython 3.11，正式支持 Linux 和 WSL2。
- 项目和 Python 分发名统一为 `esim`，独立 `ff` 命令保持可用。
- onelog 运行依赖使用 `BottiCelle/onelog` 声明的发行名
  `botticelle-onelog>=0.1,<0.2`。

### Added

- GitHub Actions、Dependabot 和统一的本地质量门禁。
- 完整离线 wheelhouse 构建、校验和与干净环境 smoke test。
- Ruff、Pyright、pre-commit 和 90% branch coverage 门禁。
- 按 public seam 与稳定能力拆分的可选择回归测试。
- Markdown/HTML 本地链接和 fragment 检查命令。
