# esim 需求架构

状态：已确认的首版验收基线

最后更新：2026-08-08

## 1. 目标与边界

`esim` 是 EDA 仿真运行器。它从一个 TC 入口和一个 Rules 入口出发，解析 YAML 配置、组合 include，展平 filelist，执行用户 hooks 和仿真器，检查日志并在固定仿真目录中保存可审计产物。

首版只实现 Synopsys VCS adapter，但公共模型要允许以后增加 Cadence Xcelium adapter。Xcelium 的具体命令、日志和 build artifact 不在本版需求中。

`esim` 不把 YAML 当成 Makefile 或通用任务编排语言：

- 配置只表达仿真所需的参数、分阶段 hook 和日志放过规则。
- 不提供用户可配置的 `cwd`、`timeout`、`environment`、`enabled`、`prepare`、`on_failure` 或 `finalize`。
- 不在 YAML 中表达 suite/regression；一次入口解析只产生一个 Effective TC。
- 不自动 hash HDL、header 或 library 内容判断缓存有效性。

## 2. 配置角色

### 2.1 Rules configuration

Rules 是可复用的仿真基线，位于 `$DV_HOME/<dtb>/rules/` 或 `$DV_HOME/dtb_common/rules/` 下，文件后缀为 `.rules` 或 `.yaml`。只有 Rules 可以声明：

- 顶层 `filelist`
- `simulator`
- `flow`

Rules 不允许声明 TC 专属的 `owner`。

### 2.2 TC configuration

TC 表达一个具体测试用例，位于 `$DV_HOME/<dtb>/tests/` 下，文件后缀为 `.tc` 或 `.yaml`。TC 可以使用共享执行字段，并额外支持可选 `owner`，但不允许声明 `filelist`、`simulator` 或 `flow`。

### 2.3 角色与名称来源

- 文件路径是 TC/Rules 角色的唯一权威来源。
- 源 YAML 不使用 `type` 或 `name` 标识身份。
- 内部数据模型应保留从路径派生的 `config_type: ConfigType`，具体 dataclass 结构留待实现设计。
- 生成的 `tc.yaml.name` 取 CLI 入口 TC 文件的 stem；`rules.yaml.name` 取 CLI 入口 Rules 文件的 stem。
- include 文件的文件名不影响生成的 name。

`.tc`、`.rules` 和 `.yaml` 均使用标准 YAML 语法，不引入新的文本语法。
首版使用 `PyYAML>=6.0,<7` 的 `safe_load`/`safe_dump` 实现标准 YAML
解析和生成；不允许任意 Python 对象构造标签。

## 3. CLI 入口与搜索

### 3.1 TC selector

TC 位置参数接受：

1. `.tc`/`.yaml` 文件的绝对路径；
2. `<dotted-dtb>:<dotted-test>` 逻辑 selector。

例如：

```bash
esim xxx.yyy:func.smoke
```

搜索顺序为：

```text
$DV_HOME/xxx/yyy/tests/func/smoke.tc
$DV_HOME/xxx/yyy/tests/func/smoke.yaml
```

绝对 TC 必须符合 `$DV_HOME/<dtb>/tests/<test>.tc|yaml` 结构，否则是输入错误。显式相对路径不受支持。

### 3.2 Rules selector

`-f` 可接受 `.rules`/`.yaml` 文件的绝对路径，或 Rules 逻辑名。`-f` 缺省时等价于 `-f default`。逻辑名 `<name>` 按以下顺序搜索，首个存在且可读的文件获胜：

```text
$DV_HOME/<dtb>/rules/<name>.rules
$DV_HOME/<dtb>/rules/<name>.yaml
$DV_HOME/dtb_common/rules/<name>.rules
$DV_HOME/dtb_common/rules/<name>.yaml
```

显式相对路径不受支持；绝对 Rules 必须位于合法 Rules 目录中。所有候选都不可用时执行前退出 2。

## 4. 源 YAML schema

### 4.1 共享顶层字段

| 字段 | 类型 | 作用 |
|---|---|---|
| `include` | `list[str]` | 按顺序组合其他 TC/Rules 片段 |
| `description` | 非空字符串 | 只采用对应 CLI 入口的说明，允许多行 |
| `tags` | `list[str]` | 分类标签，按合并顺序稳定去重 |
| `ff` | phase mapping | filelist 展平阶段 |
| `build` | phase/build mapping | 根据 flow 表达两步或三步 build |
| `run` | phase mapping | 仿真运行阶段 |

`tags` 缺失或为 `[]` 合法；每项必须是非空字符串，区分大小写，不做 trim 或规范化。User Guide 应建议 tags 主要写在 TC；Rules 仅用于 `vcs`、`coverage` 等确有意义的执行特征。

`description` 可选，但显式值不得为空或纯空白。Resolved Rules 只采用入口 Rules description，Effective TC 只采用入口 TC description；include 中的值不继承。

### 4.2 Rules-only 字段

| 字段 | 类型 | 要求 |
|---|---|---|
| `filelist` | path string | 所有参与配置中必须恰好声明一次 |
| `simulator` | enum | 首版只接受小写 `vcs` |
| `flow` | enum | 只接受小写 `two-step`/`three-step` |

`filelist` 只能出现在 Rules 文件中。所有参与 Effective TC 的 Rules 文件总计必须恰好声明一个 filelist：零个或多个都报错，即使多处展开后是同一路径也不例外。错误应列出所有声明来源和 include chain。

`simulator` 和 `flow` 也只能出现在 Rules。多个 Rules 可重复声明相同值；不同值冲突时报出全部来源。任一字段最终缺失也是错误，不提供隐式默认值。

### 4.3 TC-only 字段

`owner` 是可选的非空单行字符串。只采用入口 TC 的 owner，include 中的 owner 不继承；入口未声明时生成的 `tc.yaml` 不输出 owner。Rules 出现 owner 是已知字段角色错误。

### 4.4 两步流 Rules 示例

```yaml
description: VCS default build rules
tags:
  - vcs

include:
  - ./common.rules

filelist: $DV_HOME/xxx/yyy/tb/top.f
simulator: vcs
flow: two-step

ff:
  args:
    - -d FPGA USE_DDR
  hooks:
    before:
      commands:
        - source $DV_HOME/xxx/yyy/tb/setup.sh && echo ff-ready

build:
  args:
    - -full64 -sverilog
  hooks:
    after:
      commands:
        - python $DV_HOME/xxx/yyy/tb/check_build.py

run:
  args:
    - +UVM_VERBOSITY=UVM_MEDIUM
```

### 4.5 TC 示例

```yaml
description: Basic smoke testcase
owner: dv-team
tags:
  - smoke
  - func

include:
  - ../base.tc

build:
  args:
    - +define+SMOKE_TEST

run:
  args:
    - +UVM_TESTNAME=smoke_test +ntb_random_seed=1
  hooks:
    before:
      commands:
        - python $DV_HOME/xxx/yyy/tests/scripts/create_input.py --case smoke
        - csh -f -c 'source $DV_HOME/xxx/yyy/tb/env.csh; ./prepare.csh'
      continue_on_error: false
```

`schema_version`、`kind`、`type`、`name`、`metadata` 均不是首版源 schema 字段。

## 5. include 与路径

### 5.1 include 形式

- `include` 始终是 `list[str]`；单个文件也必须写成单项列表。
- TC 和 Rules 可以自由 include 对方或同类文件。
- 文档应建议 TC 不要再 include CLI 已选中的项目默认 Rules，但 schema 不禁止这种组合。
- 每个 include 项是带 `.tc`/`.rules`/`.yaml` 后缀的精确路径，不应用 CLI selector 搜索或自动补后缀。
- include 内的相对路径以声明它的 YAML 文件目录为基准；绝对路径直接使用。

### 5.2 受控环境变量展开

`include` 和 `filelist` 使用与 `ff` 相同的受控语义：

- 支持 `$NAME` 和 `${NAME}`，并递归展开变量值。
- 变量缺失、空值或循环引用是输入错误。
- 不支持 shell default、命令替换、反引号、tilde 或 glob。
- 规范化后消除 dot-segments 和重复分隔符，并保留 symlink 逻辑路径。
- filelist 在执行前必须是可读普通文件。

生成快照中的 schema-owned path 都写为规范化绝对路径。`description`、`tags`、`owner` 不展开环境变量；phase args 和 hook commands 各自按第 8 节的边界处理。

### 5.3 图遍历

- 每个入口的 include 图按列表从左到右深度优先后序遍历：先处理 include，再处理当前文件。
- 活动递归链中再次遇到同一配置是循环，必须报出完整 cycle chain。
- 菱形依赖等非循环重复在全局只合并第一次，之后跳过并记录诊断。
- 配置身份使用规范化绝对路径。

## 6. 合并规则

### 6.1 全局顺序

从低优先级到高优先级的完整顺序是：

```text
较早 Rules includes
→ 较晚 Rules includes
→ CLI 入口 Rules
→ 较早 TC includes
→ 较晚 TC includes
→ CLI 入口 TC
→ CLI 阶段参数
```

Resolved Rules 由 Rules 入口图生成。Effective TC 由 Resolved Rules、TC 入口图和 CLI 参数生成。

### 6.2 字段合并

- 所有 phase `args` 列表按全局顺序追加，保留顺序和重复项。
- 同名 hook 的 `commands` 以相同方式追加，不对 after 做反向执行。
- `tags` 追加后稳定去重，保留每个值的首次出现位置。Rules tags 进入 Effective TC。
- hook `continue_on_error` 由后层显式值覆盖前层，缺失时继承，合并后仍缺失则为 `false`。
- `description`、`owner` 使用入口专属规则，不参与 include 继承。
- `filelist` 采用恰好一次声明，不覆盖也不追加。
- `simulator`/`flow` 采用一致性合并，相同值可重复，冲突值报错。

esim 不尝试解析或消解用户仿真器选项间的冲突，只拦截与 adapter 管理的 input/output/log 参数冲突的保留选项。

## 7. Schema 验证与未知字段

- YAML 顶层和所有结构节点必须符合已知字段的类型要求。
- 已知字段出现在错误角色或 flow 中必须报错，例如 TC `filelist`、Rules `owner`、two-step `build.analyze`。
- 不属于首版 schema 的字段一律忽略，包括源 YAML 中的 `type`、`name`、`source`、`timeout`、`environment`、`cwd` 和 `enabled`。
- 每个忽略字段立即在终端打印 WARNING，并以“源文件绝对路径 + 字段路径”稳定去重后写入 `result.yaml.ignored_fields`。
- 忽略记录不保存原始值，未知字段不参与合并，也不进入生成快照。

所有可在命令执行前发现的 selector、YAML、include、schema、filelist、waiver 和保留参数错误都必须在第一个用户 hook 之前失败。

## 8. Phase、args 与 hooks

### 8.1 公共生命周期

公共执行阶段固定为：

```text
ff → build → run
```

two-step 的 build 是一次不可拆分的 VCS 调用；three-step 的 build 内部才分为 analyze 和 elaborate。

two-step 只允许：

```yaml
build:
  args: []
  hooks: {}
```

three-step 只允许：

```yaml
build:
  hooks: {}
  analyze:
    args: []
    hooks: {}
  elaborate:
    args: []
    hooks: {}
```

two-step 出现 `build.analyze`/`build.elaborate`，或 three-step 出现直接 `build.args`，即使值是空映射/空列表也是执行前错误。

CLI 阶段参数映射：

| flow | `-b` | `-e` | `-r` |
|---|---|---|---|
| `two-step` | `build.args` | 非法 | `run.args` |
| `three-step` | `build.analyze.args` | `build.elaborate.args` | `run.args` |

### 8.2 args

- phase `args` 是字符串列表。
- 每个字符串是一个可包含多个参数的 POSIX 命令行片段，例如 `-d FPGA USE_DDR`。
- esim 先合并 fragments，再用 POSIX `shlex` 分词，最后构造 argv；它不通过 shell 执行。
- `&&`、`;`、`|` 在 args 中只是普通 argv token，没有 shell 连接语义。
- 非字符串项或不配对 quoting 是输入错误。
- 分词后的 token 支持 `$NAME`/`${NAME}` 递归环境展开，引号只用于分组，不抑制展开。
- args 中 `$$` 表示字面量 `$`，例如 `$$unit` 最终为 `$unit`。
- 不支持 shell default、命令替换、tilde 或 glob。

`ff.args` 首版只接受可重复的 `-d`/`--define`，每次可带一个或多个宏。esim 将它转成共享 ff engine 的结构化宏集合，并沿用 ff 的校验、去重和排序规则。ff input、output、log、debug 或其他未开放参数是冲突/未支持错误。

### 8.3 hooks

`ff`、two-step `build`、three-step 外层 `build`、`analyze`、`elaborate` 和 `run` 都可以内嵌：

```yaml
hooks:
  before:
    commands:
      - echo ready && ./prepare.sh
    continue_on_error: false
  after:
    commands:
      - python post_process.py --mode check
```

规则如下：

- `hooks`、`before`、`after` 是可选 mapping，空 mapping 合法。
- `commands` 必须是 `list[str]`，标量简写非法。
- `commands` 缺失或为 `[]` 都不增加命令，也不清除前层命令。
- 每条 command 必须是非空单行字符串；包含 CR/LF 或仅空白的值非法。
- `continue_on_error` 只接受规范小写 YAML 布尔量 `true`/`false`；字符串、数字、`yes/no` 均非法。
- 只声明 `continue_on_error` 的片段可以为其他层合并进来的 commands 提供配置。
- 最终没有 command 的 hook 从生成快照省略，不执行也不生成日志。

每条 command 均以仿真目录为工作目录，由独立的以下进程执行：

```text
/bin/bash -o pipefail -c <command>
```

同一 hook 的 commands 不共享 `cd`、`export` 或 shell function。需要 csh/zsh 时，用户应在 command 中显式调用，或执行带 shebang 的脚本。hook command 保持原文并由 Bash 完成变量和 shell 语法解析，不使用 args 的 `$$` 规则。

`continue_on_error: true` 只在某条 command 非零退出后继续当前 hook 的剩余 commands。该 hook 最终仍失败，不进入后续 hook、工具或阶段。Command failure 不能被 waiver 放过。

### 8.4 three-step 执行顺序

```text
build.before
→ analyze.before
→ analyze
→ analyze log check
→ analyze.after
→ elaborate.before
→ elaborate
→ elaborate log check
→ elaborate.after
→ build.after
```

任一 before、主命令、日志检查或 after 失败都截断之后的全部用户节点。内部 esim cleanup 仍必须关闭日志、写入结果并释放资源；它不是用户 hook。

## 9. ff 与 VCS adapter

### 9.1 filelist 展平

esim 必须在进程内调用与 `ff` CLI 共享的 flattening engine，不启动 `ff` 子进程。固定产物为：

```text
<sim-dir>/flattened.f
<sim-dir>/ff.log
```

完整运行和 `--keep` 完整运行都重建 `flattened.f`。`-a build` 复用已有且可读的 `flattened.f`；`-a run` 不消费它，但仍做上游配置一致性校验。

VCS 本身可以通过 filelist 中的 `-f`/`-F` 继续引用子 filelist；esim 仍在调用 VCS 前用 ff 递归展平，以统一条件、路径、校验和可审计输出。

### 9.2 VCS 两步流

```text
vcs -f <absolute-flattened.f> <merged-build-argv> \
    -o <absolute-simv> -l <absolute-vcs.log>

<absolute-simv> <merged-run-argv> -l <absolute-simv.log>
```

### 9.3 VCS 三步流

```text
vlogan -f <absolute-flattened.f> <merged-analyze-argv> \
       -l <absolute-vlogan.log>

vcs <merged-elaborate-argv> -o <absolute-simv> \
    -l <absolute-vcs.log>

<absolute-simv> <merged-run-argv> -l <absolute-simv.log>
```

命令构造顺序固定为 adapter 工具/必要输入、Rules→TC→CLI 合并 argv、adapter-managed output/log。所有受管路径为绝对路径。用户 phase/CLI args 中出现会冲突的 `-f`、`-o`、`-l` 时执行前退出 2。

VCS build artifact 固定为 `<sim-dir>/simv` 及 VCS 产生的关联目录/增量编译数据。将来的 simulator adapter 必须声明自己的等价 artifact、主日志和保留参数。

## 10. Simulation directory、清理和锁

### 10.1 目录映射

目标目录固定为：

```text
$DV_TMP/<dotted-dtb-key>/<rules-file-stem>/<dotted-test-key>/
```

例如 `esim xxx.yyy:func.smoke` 使用 Rules `default.rules` 时：

```text
$DV_TMP/xxx.yyy/default/func.smoke/
```

逻辑和绝对 TC selector 必须得到同一目录 key。所有命令以该目录为工作目录；YAML 不允许覆盖 cwd。args/commands 中的相对路径不被 esim 识别或改写，执行时自然以该目录为基准。

### 10.2 默认运行与 keep

- 默认完整运行在获取锁后删除精确目标仿真目录，重建干净目录。
- `-k/--keep` 保留 simulator cache 和 build artifacts，但仍完整执行 ff/build/run。
- keep 运行仍重写本次 `tc.yaml`、`rules.yaml`、`result.yaml`、总 waiver 和全部实际执行节点的受管日志。
- 首版不计算 cache fingerprint，也不因 `--keep` 自动跳过阶段。

### 10.3 互斥锁

esim 在 CLI 和最小 selector 解析得到目标仿真目录后，必须在任何清理、缓存读取或写入前立即获取非等待式独占内核文件锁。

- 锁文件位于目标目录之外，例如同级 `.func.smoke.esim.lock`。
- 锁文件可记录 host/PID/命令，但文件存在不表示锁有效。
- 锁 FD 必须 close-on-exec，不传给 hook 或 EDA 子进程。
- 进程正常退出、异常或 `SIGKILL` 都由内核释放锁，不依赖删除锁文件。
- 锁已被占用时不等待，退出 2。
- 主运行与 `esim check` 使用同一把锁。

## 11. Stage action

`-a build` 和 `-a run` 使用已有仿真目录的上游缓存，只执行指定动作。

共通规则：

- Stage action 隐含 `--keep`；显式同时传 `-k` 合法但冗余。
- 目标仿真目录必须已存在，且 Stage action 绝不做默认清理。
- esim 重新解析当前 TC/Rules，不冻结或盲信旧快照。
- 兼容性校验通过后才用当前 Effective TC 更新快照、waiver 和 result。
- esim 不 hash HDL/header/`-y` library 内容；用户选择 action 就表示自行确认未执行上游的源码依赖未变。

`-a build`：

- 要求 ff/filelist 上游配置与缓存一致，且 `flattened.f` 存在并可读。
- 允许 build、run 和描述性字段变化，重做 build 但不重做 ff/run。
- two-step 只允许 CLI `-b`；three-step 允许 `-b`/`-e`；`-r` 非法。
- build 成功后 result status 为 `NOT_RUN`，CLI 返回 0。
- 保留已有仿真主日志，例如 VCS `simv.log`。

`-a run`：

- 要求 ff/filelist/build 上游配置与缓存一致，且 simulator build artifact 有效。
- 允许 run 和描述性字段变化，只执行 run。
- CLI 只允许 `-r`，`-b`/`-e` 非法。
- 根据本次 run 的退出码和日志得到 `PASS` 或 `FAIL`。

上游不兼容、所需缓存文件缺失或目标阶段 CLI 参数错位时，执行前退出 2。

## 12. 日志、finding 与 waiver

### 12.1 日志命名和写入

| 节点 | 日志 |
|---|---|
| ff | `ff.log` |
| three-step analyze | `vlogan.log` |
| two-step build / three-step elaborate | `vcs.log` |
| run | `simv.log` |
| hook before | `pre_<phase>.log` |
| hook after | `post_<phase>.log` |

three-step 外层 build hook 使用 `pre_build.log`/`post_build.log`。同一 hook 的全部 commands 将 stdout/stderr 按执行顺序完整汇入同一日志。执行节点每次覆盖它的受管日志，不追加；未配置/未执行的 hook 不产生空日志。Result 只记录本次实际执行的日志。

### 12.2 finding 识别

- hook checker 逐行、大小写不敏感地搜索 `fail` 或 `error` 子串，包括 `failover` 等单词内部匹配。
- tool checker 取 simulator/tool 专用规则与同一通用子串扫描的并集。
- 同一日志行命中多条 checker 规则时产生一个 finding，但保留所有命中原因。
- ff 优先使用共享 engine 的结构化结果，同时保留日志检查。
- 任意未放过 finding 使当前节点失败。原始完整日志始终保留，过滤不删除或修改日志。
- 进程非零退出是独立的 Command failure，无论日志文本如何都失败，且不能被 waiver 放过。

### 12.3 waiver 来源

按以下顺序合并：

1. esim built-in rules；首版为空；
2. `$DV_HOME/dtb_common/rules/waive.txt` 和 `exclude.txt`；
3. CLI 入口 TC 所属 `$DV_HOME/<dtb>/rules/` 下的同名文件。

common 规则始终生效，入口 DTB 规则是补充。include 文件所在 DTB 不增加 waiver 来源。所有源文件可选：缺失、空文件或只有注释均表示无规则；存在但不可读是执行前错误。

每行一条规则：

- 去除行首尾空白。
- 忽略空行以及首个非空白内容为 `#` 或 `//` 的整行注释。
- 不支持行尾注释或跨行模式。
- `waive.txt` 是区分大小写的 shell-style glob，对 finding 整行匹配。
- `exclude.txt` 是区分大小写的正则表达式，对 finding 单行做 search；规则可显式使用 `(?i)` 等 flag。
- 任一 glob 或 regex 命中即放过该 finding。

所有模式必须在任何命令执行前一次性校验。非法模式不得忽略，并应一次报告所有错误的绝对文件、行号、原始规则和原因。

### 12.4 总 waiver 文件

esim 每次在仿真目录生成实际使用的 `waive.txt` 和 `exclude.txt`，即使没有任何规则也生成空文件。

- 来源顺序固定为 built-in→common→entry DTB。
- 保留每个来源内规则顺序和重复项，省略原空行和注释。
- 每个非空来源块前写 `// source: <absolute-path>`。
- 未来的 built-in rule 也必须以 `// source: esim built-in` 块写入总文件，不允许只在代码内隐式生效。
- 首版不预置 `*UVM_ERROR : 0*` 或其他具体 built-in waiver。

## 13. 运行快照与结果

### 13.1 rules.yaml 和 tc.yaml

esim 必须在第一个用户 hook 之前写入：

- `<sim-dir>/rules.yaml`：Resolved Rules；
- `<sim-dir>/tc.yaml`：包含 CLI 最终参数的 Effective TC。

两份文件是不受运行结果影响的配置快照。执行器消费与生成快照同一份已解析内存模型，不重新解析快照驱动执行。

生成快照：

- 删除 `include`；
- 只保留合并后的已知有效字段；
- 把 filelist 及来源路径写成规范化绝对路径；
- 省略最终没有 command 的 hooks；
- 源 YAML 的 `source` 按未知字段忽略。

`rules.yaml.source` 包含：

- `entry`：入口 Rules 绝对路径；
- `merge_order`：Rules 图实际参与合并的绝对路径。

`tc.yaml.source` 包含：

- `entry_tc`：入口 TC 绝对路径；
- `entry_rules`：入口 Rules 绝对路径；
- `merge_order`：完整 Rules→TC 实际合并顺序。

source 列表按第一次出现稳定去重。

### 13.2 result.yaml

`result.yaml` 是可更新的动态结果，至少记录：

- `status`: `PASS`/`FAIL`/`NOT_RUN`；
- 本次 action；
- 实际执行的 phase/hook、退出码和日志；
- findings 及对应 waiver 命中；
- `ignored_fields`。

result 只保存当前有效判断，不保存 initial/recheck 历史。更新必须原子替换；重检可替换状态、findings 和 waiver 命中，但保留已记录日志路径与原始进程退出码。

## 14. 独立日志重检

```bash
esim check <absolute-sim-dir>
```

`check` 必须：

1. 获取该仿真目录的同一把锁；
2. 读取 `tc.yaml`/`result.yaml` 定位当前 waiver 来源和 simulator adapter；
3. 重新生成总 `waive.txt`/`exclude.txt`；
4. 不执行 ff、hook、compiler、elaborator 或 simulator；
5. 只重检 adapter 指定的仿真主日志，VCS 为 `simv.log`；
6. 用当前 checker 和 waiver 原子更新 result。

主日志存在时，按 tool-specific + generic checker + waiver 重判 PASS/FAIL。已记录的 run 非零退出仍导致 FAIL，不能放过。主日志缺失时只打印 warning，保持 result 当前状态并返回 0；不检查 build/hook 日志来代替仿真结论。

`-a build` 刻意保留的旧主日志也可由用户显式调用 `check` 重判。

## 15. 退出码

### 15.1 esim 主命令

```text
0  完整运行 PASS，或请求的 build action 成功
1  进入执行后的 hook/ff/tool Command failure 或未放过 finding
2  CLI、selector、YAML、include、schema、路径、waiver、缓存校验或锁冲突等受控输入错误
3  esim 内部程序错误
```

### 15.2 esim check

```text
0  未判定为 FAIL；可能是 PASS，也可能是主日志缺失且状态保持
1  主日志存在未放过 finding，或已记录 run 非零退出
2  CLI、仿真目录、快照或 waiver 等受控输入错误
3  esim 内部程序错误
```

调用方需要区分 `PASS` 与 `NOT_RUN` 时必须读取 `result.yaml`，不能只依赖退出码 0。

## 16. 待后续设计

以下内容不得在首版中凭实现假设补齐：

- Python dataclass/模块 API 的具体结构与可见性。
- Xcelium 流程、命令、日志和 cache artifact。
- suite/regression 中的多 TC 调度。
- `timeout`、`environment`、`cwd`、`enabled` 等未来 phase 能力。
- 自动缓存 fingerprint 和源码内容变化检测。
- 预置 built-in waiver 的具体规则。
