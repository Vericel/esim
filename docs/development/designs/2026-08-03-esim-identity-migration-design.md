# esim 项目身份与 onelog 分发名迁移设计

## 目标

将仓库的产品和 Python 分发身份统一为 `esim`，同时保留
`ff` 作为可独立执行的 filelist 预处理命令。日志依赖只使用
`BottiCelle/onelog` 当前声明的 `botticelle-onelog` 分发名，并从可控文本、
制品和 Git 记录中清除旧个人分发名。

## 命名边界

- 产品、仓库和 Python 分发名：`esim`。
- 完整仿真入口：`esim`；其产品行为必须由单独需求和设计驱动，
  本次身份迁移不伪造空实现。
- filelist 预处理组件、Python 导入包和独立命令：`ff`。
- 日志源码仓库：`BottiCelle/onelog`；Python 分发名：`botticelle-onelog`；
  Python 导入名：`onelog`。

## 分发与离线安装

`pyproject.toml` 的分发名改为 `esim`，当前 wheel 继续安装独立
`ff` console entry point。未有完整仿真契约之前，不发布名不副实的
`esim` console entry point。

wheelhouse 保留为离线发布制品，不作为每个 PR 的默认必跑门禁。
它由 GitHub Actions 手工触发或正式发布触发；普通 PR/main CI 构建
单个 wheel 并做联网安装验证。全员可用由管理员安装到统一版本目录并
通过 PATH 或 Environment Modules 发布，不由 wheelhouse 自动完成。

## 依赖迁移

`BottiCelle/onelog` 当前 `main` 已声明 `botticelle-onelog` 0.1.0。esim 改为从
该已核对提交构建，wheel metadata 依赖范围改为
`botticelle-onelog>=0.1,<0.2`。依赖改名同步更新包元数据、测试、README、
需求、用户手册、ADR、发布清单和 wheelhouse 构建脚本。

## 历史清理

对本仓库所有本地分支和 tag 重写包含旧分发名的文件快照与提交元数据。
重写前创建仓库外的本地 mirror 备份，验证后再删除可达 refs 中的旧对象。

onelog 远程历史也包含旧名称。对其 `main` 和 `v0.1.0` 重写将改变
公开 commit/tag ID，使旧 clone 分叉；因此只在用户对“远程 force-push”
给出明确批准后执行。本地改写、验证和备份可先行完成。

## TDD 与验证 seam

- 分发 seam：构建 wheel，检查 `Name: esim`、`Requires-Dist: botticelle-onelog`
  和 `ff` console entry point。
- CLI seam：从干净环境安装 wheel 后运行 `ff --help`。
- 离线 seam：手工/发布流程构建 wheelhouse，使用 `--no-index` 安装
  `esim`，再执行 `ff --help` 和 `pip check`。
- 污染检查：对工作树、所有 refs 可达对象、wheel 元数据和压缩制品
  执行大小写不敏感搜索。
