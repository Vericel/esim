# onelogg PyPI 分发迁移设计

## 背景

`BottiCelle/onelog` 已发布 PyPI 分发 `onelogg` 0.1.1，Python 导入名仍为
`onelog`。当前 esim 0.2.0 声明不存在于 PyPI 的
`botticelle-onelog>=0.1,<0.2`，并在开发、CI 和离线 wheelhouse 构建时从固定
Git commit 预先安装该分发。这使普通索引安装无法独立解析运行时依赖，也让
发布流程继续依赖旧的临时分发身份。

## 决策

- esim 的运行时依赖改为 `onelogg>=0.1.1,<0.2`。
- Python public API 保持 `from onelog import get_logger`；不修改源码导入名、
  类型 stub 或日志行为。
- 开发环境、CI 和离线 wheelhouse 使用精确版本 `onelogg==0.1.1`，从 PyPI
  正式发布物安装或收集，不再从 Git commit 构建运行时依赖。
- wheelhouse 继续包含 esim、onelogg、Rich 及其传递依赖，并继续执行
  `--no-index` 干净安装、`pip check`、`ff --help` 和 SHA-256 清单验证。
- 当前权威文档统一使用“分发名 `onelogg`、导入名 `onelog`”；已经完成的历史
  设计和实施计划保留当时事实，不做追溯性改写。
- 新增 ADR 取代 ADR-0003 和 ADR-0004 中关于 `botticelle-onelog` 分发身份及
  固定 Git commit 来源的部分，保留其日志所有权、Python 版本和离线发行决策。
- 文档提示 `onelog`、`botticelle-onelog` 与 `onelogg` 是不同的 Python 分发，
  但可能写入同一个 `onelog` 导入包；迁移环境不得同时保留这些分发。

## Public seam 与验收行为

本次 TDD 唯一 public seam 是 Python 分发及安装 seam：构建 esim wheel 后读取
其标准 `METADATA`，并通过正式 wheelhouse 入口在干净环境安装。

可观察验收行为如下：

1. esim wheel 声明 `Requires-Dist: onelogg<0.2,>=0.1.1`，且不包含 vendored
   `onelog`。
2. CI 能仅依靠 PyPI 的 `onelogg==0.1.1` 建立开发环境，不需要 onelog Git
   checkout 或固定 commit。
3. wheelhouse 包含 `onelogg` 0.1.1 wheel，并能在无索引安装中解析 esim、通过
   `pip check` 并运行 `ff --help`。
4. `src/ff/cli.py` 继续通过 `onelog` 导入 `get_logger`，现有 CLI 日志回归保持
   不变。

## 兼容性与发布影响

`onelogg` 0.1.1 保持现有 `onelog` API，因此不改变 ff CLI 或引擎行为。分发名
变化会使包管理器把新旧依赖视为不同项目；已有开发环境应卸载
`botticelle-onelog`（以及无关的 `onelog` 分发）后重建，避免同名导入文件由多个
分发共同拥有。esim 版本暂保持 0.2.0，因为当前仓库仍在准备该版本；若 0.2.0
已对外发布，则应另行决定补丁版本，而不是覆盖既有发布物。
