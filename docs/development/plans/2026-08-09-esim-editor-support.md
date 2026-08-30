# esim 编辑器语法高亮实施计划

## 目标

让 VS Code 和 Vim/gVim 将 `*.tc` 与 `*.rules` 识别为标准 YAML，同时提供可随 esim 源码 release 分享的安装文件和说明。

## 范围

- 在本仓库中提供 VS Code workspace 文件关联，开箱即用。
- 提供可复制到用户配置的 VS Code 设置片段。
- 提供遵循 Vim package 目录结构的 `ftdetect` 脚本，同时支持 Vim 与 gVim。
- 编写安装、卸载和验证说明，并从项目入口文档链接。

## 非目标

- 不为 esim 定制一套偏离 YAML 的语法。
- 不发布 VS Code Marketplace 扩展或 Vim 插件仓库。
- 不添加 YAML schema 校验或自动补全。

## 实施阶段

1. 确认 VS Code/Vim 的最小关联方式与现有 release 边界。
2. 新增仓库级 VS Code 关联和可分享的 `tools/editors/` 文件。
3. 更新项目入口与 release 检查说明。
4. 验证 JSON/Vim 脚本、文档链接、diff 和工作区边界。

## 验证

- 解析所有新增 JSON 文件。
- 用 Vim 的 ex mode 打开 `.tc`/`.rules` 样例并断言 `filetype=yaml`（环境有 Vim 时）。
- 运行项目文档链接检查。
- 运行 `git diff --check` 并检查 `git status --short`。
