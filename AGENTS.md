# AGENTS.md

本文件是本仓库唯一的代理开发规范，适用于仓库中的所有文件。直接用户指令优先；本文件与权威项目文档发生冲突时，停止修改并向用户说明冲突，不得自行猜测。

## 开始工作前

1. 阅读本文件和根目录 `CONTEXT.md`。
2. 根据任务阅读 `docs/requirements/` 下对应的需求、相关 ADR、设计和实施计划。
3. 运行 `git status --short`，识别并保护用户已有的修改和未跟踪文件。
4. 明确任务范围、可观察行为、验证方式以及需要同步更新的文档。

## 权威来源与优先级

- `CONTEXT.md`：领域术语和统一语言。代码、测试和文档使用其中的术语，避免自创新同义词。
- `docs/requirements/ff.md`：`ff` 可观察行为的权威契约。
- `docs/requirements/esim.md`：`esim` TC/Rules、执行流程和运行产物的权威契约。
- `docs/development/adr/`：跨功能、长期有效的架构决策。重要架构变化新增 ADR，不静默改写已接受决策的历史。
- `docs/development/designs/`：单项功能经用户确认的设计，不得擅自扩大需求。
- `docs/development/plans/`：正式、可审阅、纳入版本控制的实施计划。
- `tests/`：行为契约的可执行证据。测试中的偶然行为不能覆盖已确认需求。
- `README.md`：项目入口、安装说明和最小示例。
- `docs/user/ff-user-guide.html`：完整用户使用文档。
- `docs/development/verification.md`：项目级验证方法和结果。
- `docs/development/development-guide.md`：开发环境、质量门禁和 CI 使用说明。
- `docs/development/release-checklist.md`：人工发布与离线制品检查清单。
- `CHANGELOG.md`：遵循 SemVer 的用户可见变更记录。
- `docs/development/research/`：调研证据，不自动成为需求或架构决策。

实现、测试和文档不一致时，先确认需求；不得通过只修改其中一层来掩盖冲突。任何可观察行为变更必须在同一逻辑变更中同步更新需求、测试、实现和受影响的用户文档。

## 工作流与计划文件

- 非简单行为变更先形成设计，写入 `docs/development/designs/YYYY-MM-DD-<slug>-design.md`，经用户确认后再实施。
- 需要正式实施计划时，写入 `docs/development/plans/YYYY-MM-DD-<slug>.md`。
- 预计包含 3 个以上阶段或 5 次以上工具操作时，使用 `$planning-with-files`。其运行时文件只能放在 `.planning/YYYY-MM-DD-<slug>/`，不得放入 `docs/` 或仓库根目录。
- 同一任务的正式计划与运行时目录使用相同日期和 slug；路径已存在时添加 `-02`、`-03` 等后缀，禁止覆盖。
- 运行时 `task_plan.md` 必须引用对应的正式计划。`.planning/` 始终保持 Git 忽略状态。
- 并行任务各用独立运行时目录，并通过该技能的 `PLAN_ID` 固定当前会话；并行会话不得争用 `.planning/.active_plan`。
- 纯文档、小型机械修改和不改变行为的配置修改不强制创建设计或实施计划，但仍须验证内容、路径和链接。

## TDD 与测试规范

新增功能、缺陷修复以及任何可观察行为变化都必须调用并遵循 `$tdd`：

1. 开始写测试前，明确并与用户确认本次测试的 public seam，例如 CLI、公开引擎 API 或文件输出。
2. 按纵向切片执行：写一个失败测试，运行并确认因预期原因失败，只写使其通过的最小实现，再进入下一条测试。
3. 测试通过公开接口验证行为，名称应像行为规格；不要测试私有方法或内部调用次数。
4. 期望值来自需求、已验证示例或独立字面值，不得用与实现相同的算法重新计算期望值。
5. 只在外部 API、文件系统、时间、随机性等系统边界使用 mock；不 mock 自有模块或内部协作者。
6. 不先批量写完所有测试再批量实现，不添加尚无失败测试驱动的推测性代码。

### 测试目录与命名

测试统一放在 `tests/`，按 public seam 和可观察能力组织，不机械镜像 `src/` 的内部模块结构：

```text
tests/
├── conftest.py                  # 跨多个测试文件共享的 pytest fixture；需要时创建
├── fixtures/                    # 纳入版本控制的静态输入和期望输出；需要时创建
│   └── <scenario>/
├── support/                     # 跨文件共享的测试构建器或辅助代码；需要时创建
├── test_cli_output.py           # CLI 输出与宏透传
├── test_cli_logging.py          # CLI 日志与调试输出
├── test_cli_errors.py           # CLI 参数、受控错误和内部错误
├── test_engine_inputs.py        # 顶层输入、源码解析和可读性
├── test_engine_conditions.py    # 条件指令和预定义宏
├── test_engine_filelists.py     # 嵌套 filelist、递归和 source chain
├── test_engine_comments.py      # 行注释和块注释
├── test_engine_environment.py   # 环境变量展开
├── test_engine_options.py       # 仿真器选项、define 和 incdir
├── test_engine_output.py        # 输出发布、编码和 symlink
├── test_engine_path_validation.py # 路径语法约束
└── test_distribution.py         # 打包、安装和入口点 seam
```

- 测试文件使用 `test_<public-seam>.py`；单个 seam 过大且确有导航困难时，按稳定能力拆为 `test_<public-seam>_<capability>.py`，不为追求目录对称而拆分。
- 测试函数使用 `test_<observable_behavior>`，名称描述调用者可观察到的行为，不描述内部实现步骤。
- 只被一个测试文件使用的 fixture 和 helper 留在该文件；跨多个文件共享的 fixture 放入 `tests/conftest.py`，共享 helper 放入 `tests/support/`。
- 静态 filelist、源码样例和期望输出放入 `tests/fixtures/<scenario>/`；场景目录使用小写 kebab-case，并让输入与期望文件名表达各自角色。
- 测试运行时产生的文件使用 pytest 的 `tmp_path`，不得写入 `tests/fixtures/`、仓库根目录或源码目录。
- 当前不建立 `unit/`、`integration/` 等分层目录，也不添加对应 marker；只有出现明确的运行成本、外部环境或选择性执行需求时，先取得用户确认再引入。
- 新增 public seam 时增加对应测试文件，并同步更新 `docs/development/verification.md`；不要顺带重排与当前任务无关的既有测试。
- `conftest.py`、`fixtures/` 和 `support/` 均按需创建，不保留空目录或占位文件。

纯文档、注释、格式调整和不改变行为的配置修改豁免 TDD 红绿循环。

## 代码与依赖

- 生产代码必须兼容 CPython 3.11，不使用更高版本才提供的语法或标准库 API。
- 开发依赖使用 `.[dev]` extra 中的精确版本；Pyright 1.1.411 使用 Node 24 和 `tools/typecheck/package-lock.json`，Node、Pyright 与其他质量工具不得进入运行依赖或发布 wheelhouse。
- CLI 层只负责参数解析、调用应用逻辑和呈现结果；核心业务规则放入可独立理解和测试的模块。
- 优先使用小而清晰的接口；不做与当前需求无关的重构，不提前实现未来功能。
- 代码标识符和测试函数名使用英文；CLI 参数、输出和错误信息保持现有英文风格，除非需求明确要求本地化。
- 与用户沟通以及编写需求、设计、计划、ADR 和开发说明时默认使用中文。
- 不手工编辑 `build/`、`dist/`、`*.egg-info/`、缓存、虚拟环境等生成物。

任何 Python 语言版本或最低支持版本的调整，以及运行时依赖的新增、删除或升级，都必须先向用户说明动机、替代方案、兼容性和部署影响，由用户决定。得到批准后，必须同步更新 `pyproject.toml`、`README.md`、用户文档、需求文档和相关 ADR，并执行完整验证。

## 验证与完成标准

- TDD 循环中先运行最小相关测试。本地新增或修改 feature 时，声称完成前只要求运行本次新增的测试、受影响的现有测试，以及对本次修改 Python 文件的 Ruff format/check；不默认运行全量 pytest、Pyright 或完整质量门禁。
- 稳定的部分回归按能力文件运行，例如 `.venv/bin/python -m pytest tests/test_engine_conditions.py`；单条用例使用完整 node ID；跨能力临时筛选可使用 `-k`，但不得把 `-k` 表达式当成持久测试分类。
- 完整质量门禁统一运行 `bash tools/quality/check.sh`；该入口依次执行 Ruff、Pyright、文档链接检查、90% branch coverage 全量回归和 `pip check`。本地只在创建 release tag 前或用户明确要求时执行；PR CI 继续调用同一入口作为远端合入门槛。
- 离线发布验证使用空输出目录运行 `FF_PYTHON=.venv/bin/python bash tools/packaging/build-wheelhouse.sh <OUTPUT>`；该命令必须完成固定 onelog commit、全部运行依赖、无网络安装 smoke test 和 SHA-256 清单。
- 修改 CLI、输出格式或错误信息时，同时覆盖 CLI seam 和引擎 API seam 的相关测试。
- 文档或路径变化后，搜索仓库内引用并确认没有失效链接或旧路径。
- 完成前检查 `git diff --check` 和 `git status --short`，确认没有覆盖或混入用户的其他改动。
- 没有实际运行验证时不得声称“完成”或“通过”。环境阻止验证时，明确报告命令、阻碍和未验证范围。
- pre-commit hook 只执行快速 Ruff 格式化与 lint 修复；本地不设置 coverage pre-push hook。hook 不替代 feature 开发期间对受影响测试的显式验证，创建 release tag 前必须显式执行 `bash tools/quality/check.sh`。

## Git 规范

- 提交标题遵循英文 Conventional Commits：`<type>: <imperative summary>`。
- 主要类型为 `feat`、`fix`、`test`、`docs`、`refactor`、`chore`。
- 一个提交只包含一个逻辑变更；实现与对应测试放在同一提交中。
- 小型、明确且工作区干净的改动可在当前分支完成。较大功能或工作区已有未提交修改时，优先使用独立 worktree 和 `<type>/<kebab-case-description>` 分支。
- 不得覆盖、回滚、删除或顺带提交用户已有改动。
- 只有用户明确要求时，代理才能提交、推送、变基、合并、改写历史或创建 PR。禁止自行执行破坏性 Git 操作。

## 安全与交付

- 不读取、提交或在输出中泄露密钥、许可证内容及本地环境配置。
- 不扩大任务范围，不修改无关文件；发现阻塞或规范冲突时提供证据并请求用户决定。
- 最终交付说明必须列出主要改动、实际运行的验证及结果、仍存在的风险或未验证项；不要宣称未执行的操作。
