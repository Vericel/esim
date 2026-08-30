# esim User Guide

`esim` 是面向 Synopsys VCS 的单用例 EDA 仿真运行器。它从一个 TC 入口和
一个 Rules 入口出发，按 Rules→TC→CLI 合并 YAML，在固定仿真目录中执行
ff→build→run，并保存配置、日志、waiver 和结果快照。本指南面向 Linux/WSL2
上的 TC 作者和仿真使用者。

## 第一章 入门与环境 {#getting-started}

### 了解 esim {#overview}

一次 esim invocation 只运行一个 Effective TC：

```text
TC selector + Rules selector
          │
          ▼
YAML include 与配置合并
          │
          ▼
ff → build → run → 日志判定
          │
          ▼
tc.yaml / rules.yaml / result.yaml / 完整日志
```

首版只实现 VCS adapter，支持 two-step 和 three-step。esim 不是 Makefile
或通用任务编排器：YAML 不提供 suite/regression、任意 cwd、timeout、全局
environment、enabled、prepare、on_failure 或 finalize。

### 安装与环境 {#install}

esim 需要 CPython 3.11+，支持 Linux 和 WSL2。推荐从离线 wheelhouse 安装：

```bash
python3 -m pip install \
  --no-index \
  --find-links ./wheelhouse \
  esim==0.2.0
```

安装后检查：

```bash
esim --help
ff --help
```

运行前设置：

```bash
export DV_HOME=/proj/aaa/dv
export DV_TMP=/proj/aaa/dv_tmp
```

- `$DV_HOME` 是 TC、Rules、环境脚本和 testbench 的项目根。
- `$DV_TMP` 是仿真目录根，运行时产物不会写回源码目录。

### 项目目录 {#project-layout}

推荐组织方式：

```text
$DV_HOME/
├── dtb_common/
│   ├── env/
│   └── rules/
│       ├── default.rules
│       ├── waive.txt
│       └── exclude.txt
└── xxx/yyy/
    ├── env/
    ├── rules/
    │   ├── coverage.rules
    │   ├── waive.txt
    │   └── exclude.txt
    ├── tb/
    │   └── top.f
    └── tests/
        ├── base.tc
        └── func/smoke.tc
```

waiver 文件位于 `rules/`，不是 `tb/`。`dtb_common` 规则始终生效，入口
TC 所属 DTB 的规则在其后补充。

### 快速开始 {#quick-start}

最常用命令：

```bash
# 逻辑 TC，缺省选择 default Rules
esim xxx.yyy:func.smoke

# 选择 coverage Rules，追加 run 参数
esim xxx.yyy:func.smoke -f coverage -r "+ntb_random_seed=17"

# 使用绝对 TC/Rules
esim /proj/aaa/dv/xxx/yyy/tests/func/smoke.tc \
  -f /proj/aaa/dv/dtb_common/rules/coverage.rules
```

默认完整运行会清理这一个目标仿真目录，重新执行 ff、build 和 run。成功后
检查：

```bash
cat "$DV_TMP/xxx.yyy/default/func.smoke/result.yaml"
```

## 第二章 选择器与配置模型 {#selectors-and-configuration}

### Selector 与搜索 {#selectors}

#### TC selector

位置参数接受：

1. `.tc`/`.yaml` 文件的绝对路径；
2. `<dotted-dtb>:<dotted-test>` 逻辑 selector。

`xxx.yyy:func.smoke` 按顺序搜索：

```text
$DV_HOME/xxx/yyy/tests/func/smoke.tc
$DV_HOME/xxx/yyy/tests/func/smoke.yaml
```

绝对 TC 必须位于 `$DV_HOME/<dtb>/tests/` 结构内。显式相对路径非法。

#### Rules selector

`-f/--rules` 接受 Rules 逻辑名或 `.rules`/`.yaml` 绝对路径；缺省等价于
`-f default`。逻辑名按以下顺序搜索：

```text
$DV_HOME/<dtb>/rules/<name>.rules
$DV_HOME/<dtb>/rules/<name>.yaml
$DV_HOME/dtb_common/rules/<name>.rules
$DV_HOME/dtb_common/rules/<name>.yaml
```

Rules 绝对路径必须位于入口 DTB 或 `dtb_common` 的合法 `rules/` 目录。

### Rules 与 TC schema {#configuration}

`.tc`、`.rules` 和 `.yaml` 都是标准 YAML。文件路径决定角色；源文件不要用
`type` 或 `name` 声明身份。

需要一份复杂、覆盖 two-step TC 全部受支持字段的参考时，查看
[`tests/fixtures/esim-demo-project/dv/xxx/yyy/tests/features/complete.tc`](../../tests/fixtures/esim-demo-project/dv/xxx/yyy/tests/features/complete.tc)。
同目录的 `complete.yaml` 是指向它的兼容符号链接。Rules-only 字段和
three-step-only 字段不属于该 TC。

#### 共享字段

| 字段 | 类型 | 作用 |
|---|---|---|
| `include` | `list[str]` | 按顺序组合其他配置片段 |
| `description` | 非空字符串 | 只采用 CLI 入口文件的值 |
| `tags` | `list[str]` | 按合并顺序追加并稳定去重 |
| `ff` | phase mapping | filelist 展平阶段 |
| `build` | build mapping | two-step 或 three-step build |
| `run` | phase mapping | 仿真运行阶段 |

#### Rules-only 字段

| 字段 | 类型 | 要求 |
|---|---|---|
| `filelist` | path string | 整个有效配置必须恰好声明一次 |
| `simulator` | enum | 首版只接受小写 `vcs` |
| `flow` | enum | 小写 `two-step` 或 `three-step` |

多个 Rules 可以重复声明相同 simulator/flow；冲突值报错。filelist 即使展开
后相同也不能多次声明。Rules 不能声明 `owner`。

#### TC-only 字段

`owner` 是可选的非空单行字符串，只采用入口 TC 的值。TC 不能声明
`filelist`、`simulator` 或 `flow`。

`tags` 建议主要写在 TC；Rules 只标记 `vcs`、`coverage` 等有意义的执行
特征。未知字段会被忽略，终端打印 WARNING，并以来源路径和字段路径记录到
`result.yaml.ignored_fields`；已知字段放错角色或 flow 则直接报错。

### include 与合并 {#include-merge}

include 即使只有一个文件也必须写成列表：

```yaml
include:
  - ../base.tc
  - ./fragments/feature.yaml
```

- TC 和 Rules 可以 include 对方或同类片段。
- include 必须写带 `.tc`、`.rules` 或 `.yaml` 后缀的精确路径。
- 相对路径以声明 include 的 YAML 文件目录为基准。
- 支持 `$NAME`/`${NAME}` 递归展开；缺失、空值和循环引用报错。
- 不支持 shell default、命令替换、反引号、tilde 或 glob。
- include 图按列表顺序深度优先后序合并。
- 活动链重复是循环；菱形重复只合并第一次并记录诊断。

完整优先级从低到高：

```text
较早 Rules includes
→ 较晚 Rules includes
→ 入口 Rules
→ 较早 TC includes
→ 较晚 TC includes
→ 入口 TC
→ CLI 阶段参数
```

phase args 和 before/after 命令列表依次追加并保留重复；tags 追加后稳定去重；
phase 的 `hooks.continue_on_error` 由后层显式值覆盖，缺省为 `false`。

## 第三章 仿真流程 {#simulation-flow}

### two-step 配置 {#two-step}

Rules 示例：

```yaml
description: VCS default build rules
tags: [vcs]

include:
  - ./common.rules

filelist: $DV_HOME/xxx/yyy/tb/top.f
simulator: vcs
flow: two-step

ff:
  args:
    - -d FPGA USE_DDR

build:
  args:
    - -full64 -sverilog -top top_tb
  hooks:
    after:
      - python $DV_HOME/xxx/yyy/tb/check_build.py

run:
  args:
    - +UVM_VERBOSITY=UVM_MEDIUM
```

TC 示例：

```yaml
description: Basic smoke testcase
owner: dv-team
tags: [smoke, func]

include:
  - ../base.tc

build:
  args:
    - +define+SMOKE_TEST

run:
  args:
    - +UVM_TESTNAME=smoke_test +ntb_random_seed=1
```

two-step 只允许直接的 `build.args` 和 build hooks；出现
`build.analyze`/`build.elaborate`，即使是空映射也报错。

### three-step 配置 {#three-step}

```yaml
filelist: $DV_HOME/xxx/yyy/tb/top.f
simulator: vcs
flow: three-step

build:
  hooks:
    before:
      - echo build-ready
  analyze:
    args:
      - -full64 -sverilog
  elaborate:
    args:
      - -full64 top_tb

run:
  args:
    - +UVM_TESTNAME=smoke_test
```

three-step 不允许直接 `build.args`。执行顺序固定为：

```text
build.before
→ analyze.before → analyze → analyze log check → analyze.after
→ elaborate.before → elaborate → elaborate log check → elaborate.after
→ build.after
```

任一用户 hook、主命令或日志检查失败都会截断其后用户节点；esim 自身的
cleanup 仍会保存结果和释放资源。

### CLI 阶段参数与 args {#arguments}

| flow | `-b` | `-e` | `-r` |
|---|---|---|---|
| `two-step` | `build.args` | 非法 | `run.args` |
| `three-step` | `build.analyze.args` | `build.elaborate.args` | `run.args` |

每个选项可重复，每次接收一个 POSIX argv fragment：

```bash
esim xxx.yyy:func.smoke \
  -b "-full64 -debug_access+all" \
  -r "+ntb_random_seed=7 +UVM_VERBOSITY=UVM_HIGH"
```

- args 必须是字符串列表；每个字符串可以包含多个参数。
- fragments 合并后使用 POSIX `shlex` 分词并直接构造 argv，不经过 shell。
- `&&`、`;`、`|` 在 args 中只是普通 token。
- token 支持 `$NAME`/`${NAME}` 递归展开；引号只分组，不抑制展开。
- args 中 `$$` 产生一个字面量 `$`。
- 非字符串、不配对 quoting、shell default、命令替换、tilde 和 glob 非法。
- `ff.args` 首版只开放 `-d/--define`；ff 输入、输出、日志和 debug 由 esim
  管理，不能在 YAML 中覆盖。

### Phase hooks {#hooks}

ff、two-step build、three-step 外层 build、analyze、elaborate 和 run 均可配置：

```yaml
run:
  hooks:
    before:
      - source $DV_HOME/xxx/yyy/env/setup.sh && echo ready
      - csh -f -c 'source setup.csh; ./prepare.csh'
    after:
      - python post_process.py --mode check
    continue_on_error: false
```

- `hooks` 是可选 mapping，空 mapping 合法。
- `before`/`after` 必须是字符串列表，不能使用标量简写。
- 每条 command 必须是非空单行字符串。
- 每条 command 在仿真目录中由独立的
  `/bin/bash -o pipefail -c <command>` 执行。
- 同一 hook 的 commands 不共享 `cd`、export 或 shell function。
- 需要 csh/zsh 时在 command 中显式调用，或执行带 shebang 的脚本。
- phase 级 `continue_on_error: true` 同时作用于 before/after，只会继续当前列表的剩余命令；hook 最终仍失败，
  不进入后续节点。Command failure 不能被 waiver 放过。
- 合并后没有 command 的 hook 不执行，也不产生空日志。

## 第四章 Workspace、缓存与 VCS {#workspace-cache-vcs}

### 仿真目录与锁 {#simulation-directory}

目标目录固定为：

```text
$DV_TMP/<dotted-dtb-key>/<rules-file-stem>/<dotted-test-key>/
```

例如：

```text
$DV_TMP/xxx.yyy/default/func.smoke/
```

所有命令都以该目录为工作目录。YAML 不能覆盖 cwd；args/commands 中的相对
路径自然相对此目录解释。

esim 在清理、缓存读取或写入之前获取目标目录的非等待式内核锁。锁冲突时
立即退出 2；锁文件存在本身不代表锁仍有效。主运行和 `esim check` 使用同一
把锁。

### 完整运行、keep 与 Stage action {#cache-actions}

#### 默认与 keep

- 默认完整运行只删除精确目标仿真目录，然后重建。
- `-k/--keep` 保留 simulator cache/build artifacts，但仍完整执行
  ff→build→run，并重写快照、waiver 和本次日志。
- keep 不表示自动 cache hit；首版不计算 HDL fingerprint，也不跳过阶段。

#### build action

```bash
esim xxx.yyy:func.smoke -a build -b "-debug_access+all"
```

- 隐含 `--keep`，复用兼容且可读的 `flattened.f`，只重做 build。
- two-step 只允许 `-b`；three-step 允许 `-b/-e`；`-r` 非法。
- build 成功后 status 为 `NOT_RUN`，CLI 返回 0，并保留既有主仿真日志。

#### run action

```bash
esim xxx.yyy:func.smoke -a run -r "+ntb_random_seed=18"
```

- 要求 ff/filelist/build 上游配置兼容且 simulator build artifact 有效。
- 只允许 `-r`，只执行 run，并得到 PASS 或 FAIL。

Stage action 会重新解析当前 TC/Rules，并在兼容性校验成功后更新快照。esim
不 hash HDL、header 或 `-y` library；选择 action 即表示用户确认未执行的
上游源码依赖没有变化。

### VCS 命令与受管产物 {#vcs}

two-step：

```text
vcs -f <absolute-flattened.f> <merged-build-argv> \
    -o <absolute-simv> -l <absolute-vcs.log>

<absolute-simv> <merged-run-argv> -l <absolute-simv.log>
```

three-step：

```text
vlogan -f <absolute-flattened.f> <merged-analyze-argv> \
       -l <absolute-vlogan.log>

vcs <merged-elaborate-argv> -o <absolute-simv> \
    -l <absolute-vcs.log>

<absolute-simv> <merged-run-argv> -l <absolute-simv.log>
```

esim 在进程内调用共享 ff engine，固定生成 `flattened.f` 和 `ff.log`。VCS
build artifact 固定为 `simv` 及其关联目录。用户 args 中出现会覆盖受管输入、
输出或日志的 `-f/-o/-l` 时执行前退出 2。

## 第五章 日志、结果与排错 {#logs-results-troubleshooting}

### 日志、finding 与 waiver {#logging-waivers}

| 节点 | 日志 |
|---|---|
| ff | `ff.log` |
| three-step analyze | `vlogan.log` |
| two-step build / three-step elaborate | `vcs.log` |
| run | `simv.log` |
| hook before / after | `pre_<phase>.log` / `post_<phase>.log` |

同一 hook 的 commands 依次写入同一日志。受管日志每次覆盖、不追加；没有
执行的 hook 不生成空日志。

日志 checker 逐行、不区分大小写搜索 `fail`/`error` 子串，包括单词内部；
工具日志还叠加 VCS/ff 专用规则。同一行命中多条规则只产生一个 finding，但
保留全部原因。任一未放过 finding 使节点失败。进程非零退出是独立的
Command failure，不能被文本 waiver 放过。

waiver 来源依次为：

1. esim built-in（首版为空）；
2. `$DV_HOME/dtb_common/rules/`；
3. 入口 TC 所属 `$DV_HOME/<dtb>/rules/`。

每行一条规则：

- 空行、`#` 和 `//` 整行注释忽略；不支持行尾注释。
- `waive.txt` 使用区分大小写的 shell glob，对整行匹配。
- `exclude.txt` 使用区分大小写的 regex search，可显式写 `(?i)`。
- 所有 glob/regex 在执行命令前统一严格校验，并一次报告全部非法模式。
- include 文件所在 DTB 不增加 waiver 来源。

仿真目录中总是生成本次实际使用的 `waive.txt` 和 `exclude.txt`。非空来源块
带 `// source: <absolute-path>`，保留来源顺序、规则顺序和重复项。

### 快照与结果 {#snapshots}

第一个用户 hook 之前生成：

- `rules.yaml`：Resolved Rules；
- `tc.yaml`：包含 CLI 最终参数的 Effective TC。

两者删除 include，只保存合并后的已知有效字段和规范化绝对路径，并分别用
`source` 记录入口和实际 merge order。`rules.yaml.name`、`tc.yaml.name` 来自
CLI 入口文件 stem，不读取源 YAML 的 name。

`result.yaml` 是可原子更新的动态结果，至少记录：

- `status`: `PASS`、`FAIL` 或 `NOT_RUN`；
- 本次 action；
- 实际阶段/hook、命令退出码和日志；
- findings、waiver 命中和 `ignored_fields`。

主要可审计产物：

```text
rules.yaml  tc.yaml  result.yaml
waive.txt  exclude.txt
flattened.f  ff.log  vcs.log  vlogan.log  simv.log
pre_<phase>.log  post_<phase>.log
```

### 独立日志重检 {#recheck}

更新 waiver 后可以只重判既有仿真主日志：

```bash
esim check /proj/aaa/dv_tmp/xxx.yyy/default/func.smoke
```

`check` 获取同一把锁，重新读取快照、合并 waiver，并且只重检 adapter 指定
的主日志；VCS 为 `simv.log`。它不执行 ff、hook、compiler、elaborator 或
simulator。

已记录的 run 非零退出仍导致 FAIL。主日志缺失时只打印 warning、保持当前
result 状态并返回 0；不会拿 build/hook 日志代替仿真结论。

### 错误与退出码 {#errors}

#### 主命令

| 退出码 | 含义 |
|---|---|
| `0` | 完整运行 PASS，或 build action 成功 |
| `1` | 执行后的 Command failure 或未放过 finding |
| `2` | CLI、selector、YAML、schema、路径、waiver、缓存或锁等输入错误 |
| `3` | esim 内部程序错误 |

#### `esim check`

| 退出码 | 含义 |
|---|---|
| `0` | 未判定为 FAIL；可能 PASS，也可能主日志缺失且状态保持 |
| `1` | 未放过 finding，或已有 run 非零退出 |
| `2` | 仿真目录、快照、waiver 或 CLI 输入错误 |
| `3` | esim 内部程序错误 |

调用方要区分 PASS 与 NOT_RUN 时必须读取 `result.yaml`，不能只看退出码 0。

执行前错误优先检查：

1. TC/Rules selector 是否为逻辑名或合法绝对路径；
2. YAML 顶层及结构字段类型是否正确；
3. 已知字段是否放在正确角色和 flow；
4. include/filelist 环境变量、后缀和可读性；
5. filelist 是否恰好声明一次，simulator/flow 是否存在且一致；
6. args quoting 和 adapter 保留参数；
7. waiver glob/regex；
8. Stage action 所需缓存和上游兼容性。

## 第六章 参考 {#reference-chapter}

### 配置速查 {#reference}

| 任务 | 命令或位置 |
|---|---|
| 默认运行 | `esim xxx.yyy:func.smoke` |
| 选择 Rules | `-f coverage` |
| two-step build 参数 | `-b FRAGMENT` |
| three-step analyze/elaborate 参数 | `-b FRAGMENT -e FRAGMENT` |
| run 参数 | `-r FRAGMENT` |
| 保留 cache 的完整运行 | `-k` |
| 只做 build/run | `-a build` / `-a run` |
| 只重检主日志 | `esim check <absolute-sim-dir>` |
| TC | `$DV_HOME/<dtb>/tests/**/*.tc|yaml` |
| Rules | `$DV_HOME/<dtb>/rules/*.rules|yaml` 或 `dtb_common/rules/` |
| waiver | 两层 `rules/waive.txt`、`exclude.txt` |
| 运行目录 | `$DV_TMP/<dtb-key>/<rules-key>/<test-key>/` |

filelist 规则见 [ff User Guide](ff-user-guide.md)。`.tc`/`.rules` 的 VS Code 和
Vim/gVim 文件关联见 [编辑器支持](../../editors/README.md)。
