# Filelist Flattening

该上下文定义 Verilog/SystemVerilog 仿真工程中 filelist 预处理的统一语言。

## Language

**ff**:
读取一个顶层 filelist，根据预定义宏和嵌套引用生成一个语义等价的扁平 filelist 的预处理工具。范围仅包含 Verilog/SystemVerilog filelist，不包含 mixed-language 或 logical library 建模。
_Avoid_: Source Manifest Resolver, mixed-language resolver

**Top-level filelist**:
每次 `ff` 调用的唯一入口 filelist，其中可以继续引用子 filelist。其内容中的相对路径默认以该顶层 filelist 所在目录为基准。
_Avoid_: Root manifest, source manifest

**Flat filelist**:
`ff` 的权威输出：嵌套引用和条件内容已处理，且所有路径均为已通过存在性与类型校验的规范化绝对路径，可作为后续 Verilog/SystemVerilog 编译输入的 filelist。
_Avoid_: Source manifest, intermediate manifest

**Working-directory filelist reference (`-f`)**:
相对路径以 `ff` 启动时工作目录为基准的子 filelist 引用。
_Avoid_: Parent-relative include

**Filelist-relative reference (`-F`)**:
相对路径以当前 filelist 所在目录为基准的子 filelist 引用。
_Avoid_: Working-directory include

**Source chain**:
从顶层 filelist 到当前内容的完整嵌套引用路径，包含每层 filelist、行号和原始引用。所有解析错误均使用它定位内容的引入来源。
_Avoid_: Stack trace

**Symlink target annotation**:
flat filelist 中紧邻 symlink 路径条目的 `ff` 生成注释，记录该逻辑绝对路径跟随 symlink 后的物理路径。仿真器仍使用注释后保留 symlink 的逻辑路径。
_Avoid_: Original path, source expression

**Predefined macro**:
由 `ff` 调用者提供的无值 Verilog 标识符。它用于判定 filelist 条件分支，并在 flat filelist 开头生成为同名 `+define+` HDL 编译宏；可以来自直接命令行调用，也可以由 esim 从 Effective TC 的 `ff.args` 解析后传入。
_Avoid_: Macro substitution

**Global compile option groups**:
flat filelist 的稳定输出分组，依次为调用者预定义宏生成的 `+define+`、有效输入 filelist 原有的 `+define+`、规范化后的 `+incdir+` 和其余有效内容。每组内部保留展开后的原顺序和重复项。
_Avoid_: Global source order

**Conditional directive**:
filelist 中由 `` `ifdef``, `` `ifndef``, `` `elsif``, `` `else`` 和 `` `endif`` 构成的条件结构。`ff` 根据预定义宏保留选中分支，但不执行宏文本替换；未选中分支只参与条件结构校验，其他内容不解析。
_Avoid_: Macro substitution

**Environment path reference**:
filelist 路径中以 `$NAME` 或 `${NAME}` 引用运行 `ff` 时的进程环境变量。引用会递归展开，直到不再包含环境变量，并在 flat filelist 中转换为绝对路径；任一引用不存在、值为空或形成循环时，展平失败。
_Avoid_: Shell expression

**Environment expansion chain**:
从 path entry 直接引用的环境变量到递归引用的各层变量所构成的链路。环境变量错误同时展示它与 source chain。
_Avoid_: Shell expansion

**Pass-through option**:
`ff` 不拥有其语义的仿真器 filelist 选项。`ff` 不因为无法识别该选项而拒绝它，而是将其原样保留在 flat filelist 中。
_Avoid_: Invalid option, ff option

**Path entry**:
`ff` 拥有其路径语义的 filelist 内容，包括普通非选项源码 token、`-f`/`-F`、`-v`/`-y` 和 `+incdir+`。普通源码 token 不通过文件扩展名判定。
_Avoid_: Known extension

**Include directory entry**:
flat filelist 中只包含一个规范化绝对目录的 `+incdir+` logical entry。输入行中以 `+` 连写的多个 include 目录按原始顺序拆成多个该条目。
_Avoid_: Combined include path

**Logical entry**:
filelist 中占据一行的一个完整内容单元，可以是源码路径、带参数的选项、条件指令、注释或空行。`ff` 不支持一行包含多个独立的逻辑条目。
_Avoid_: Arbitrary token stream

**Rules configuration**:
位于 Rules 搜索目录下、并由 esim 按 CLI 指定的名称解析的可复用仿真基线，可以使用顶层 `description` 和 `tags`，且只有它可以提供 top-level filelist、`simulator` 和 `flow`。源 YAML 不提供有效 `name`；生成的 `rules.yaml` 从入口 Rules 文件名 stem 派生 name。所有参与 Effective TC 的 Rules 声明必须最终得到 simulator/flow：同一字段可在多处重复相同值，但不同值冲突并列出来源；不提供隐式默认值。枚举严格区分大小写并使用规范小写，首版为 `simulator: vcs` 与 `flow: two-step|three-step`，未来再增加 `xcelium`。Top-level filelist 仍使用独立的恰好一次声明规则。
_Avoid_: TC configuration

**Execution configuration**:
Rules configuration 与 TC configuration 共享的仿真执行配置部分，包括 source preparation、build、run 及 hooks 等能力。Top-level filelist 不属于该共享部分，只能由 Rules configuration 提供。
_Avoid_: TC inheritance, Rules metadata

**TC configuration**:
由 esim 从 Rules 搜索目录之外的路径读取的具体测试用例描述，使用顶层 `description`、`tags` 和可选的 TC 专属 `owner`，在 Rules configuration 提供的仿真基线上增加用例专属扩展。源 YAML 不提供 `name`；生成的 `tc.yaml` 从入口 TC 文件名 stem 派生 name。TC configuration 不能提供 top-level filelist、`simulator` 或 `flow`，`ff` 也不读取或解释它。
_Avoid_: Rules configuration, ff configuration

**Configuration tags**:
TC/Rules 的可选 `list[str]` 分类字段；缺失或空列表合法，每项必须是非空字符串且区分大小写。按完整 Rules→TC 合并顺序追加，并以首次出现位置稳定去重。User Guide 建议 tags 主要写在 TC，Rules 只标记确有意义的执行特征。
_Avoid_: Scalar tag, case-normalized label

**Entry description**:
TC/Rules 入口可选的非空字符串说明，允许 YAML 多行文本，只取对应 CLI 入口文件的值；include 中的 description 不继承。空字符串或纯空白是已知字段值错误。
_Avoid_: Inherited description

**TC owner**:
入口 TC 可选的非空单行字符串，只取入口值并写入 Effective TC；include 中 owner 不继承，入口缺失时生成快照不输出。Rules 中 owner 是已知字段角色错误。
_Avoid_: Rules owner, inherited owner

**Configuration include**:
一个配置文件通过 `list[str]` 形式的精确路径序列引入任意其他配置片段作为合并基底，不限制 TC/Rules 文件边界，最终仍只产生一个配置结果；即使只有一个 include 也必须写单项列表，标量简写非法。路径先按 ff 同款规则递归展开 `$NAME`/`${NAME}`，再以声明该 include 的 YAML 文件目录为相对基准；缺失/空值/循环引用是执行前输入错误。生成的 rules/tc 快照删除 include 字段，独立来源链只记录规范化绝对路径。它不表示多个可独立运行的测试用例集合。
_Avoid_: Test list, suite, regression expansion

**Configuration path field**:
TC/Rules schema 中的 `include` 与 Rules-only `filelist`。两者支持 ff 同款受控 `$NAME`/`${NAME}` 递归展开，拒绝 shell default、命令替换、反引号和 tilde；相对 filelist 以实际声明该字段的 Rules 文件目录为基准。路径规范化时消除 dot-segments/重复分隔符但保留 symlink 逻辑路径，并在执行前验证 top-level filelist 为可读普通文件。生成快照中的 schema-owned 路径和独立 include 来源链均使用规范化绝对路径；args 与 hook commands 是不透明用户文本，不做路径识别或改写，其中相对路径在执行时以 Simulation directory 为基准。受控路径展开不适用于 description/tags/owner 等普通文本；hook commands 由 Bash 展开，phase args 使用独立 argv token 规则。
_Avoid_: Arbitrary YAML expansion, shell path expression

**Configuration fragment**:
通过 Configuration include 参与组合的部分配置，允许被任一类型入口复用。任何不属于当前 schema 预定义字段的键（包括旧的 `type`/`name`）都被忽略且不参与合并，并应通过诊断留痕；最终配置角色由路径决定，生成快照的 name 仅由对应 CLI 入口文件名派生。已知字段位于非法角色或 flow（例如 TC `filelist`、two-step `build.analyze`）仍是错误，不按 unknown field 忽略。User Guide 必须提示该兼容策略。
_Avoid_: Base TC, base Rules

**Resolved Rules configuration**:
将 CLI 选定的 Rules 入口及其 Configuration include 图按优先级合并后得到的完整仿真基线。较早 include 的优先级较低，入口 Rules 自身的优先级最高，整个图必须恰好声明一个 top-level filelist。
_Avoid_: Default rules, flattened rules

**Effective TC configuration**:
真正驱动一次 esim 执行的完整测试配置，依次由 Resolved Rules configuration、TC include 图、入口 TC 和 CLI 阶段参数合并而成。它必须包含且只包含一个由 Rules 层引入的 top-level filelist。
_Avoid_: Total TC, raw TC

**Run configuration snapshots**:
esim 在第一个用户 phase hook 执行前写入本次仿真目录的必备 `rules.yaml` 和 `tc.yaml`。前者序列化 Resolved Rules configuration 并以入口 Rules 文件名 stem 写入派生 `name`，后者序列化包含 CLI 最终参数的 Effective TC configuration 并以入口 TC 文件名 stem 写入派生 `name`；源 YAML/include 中的 name 被忽略。生成 `rules.yaml.source` 记录入口 Rules 和实际 merge_order，生成 `tc.yaml.source` 记录入口 TC/Rules 以及完整实际 merge_order；列表按首次出现去重且全部是规范化绝对路径。`source` 是输出专用字段，源配置出现时按 unknown field 忽略并诊断。两份快照不随执行结果或 Log recheck 改写，用于审计与复现。实际 ff/build/run 始终消费生成快照时的同一份已解析内存模型，不重新读取快照驱动执行。
_Avoid_: Source configuration, runtime reparse

**Simulation directory**:
一次 esim invocation 的产物与命令执行位置。逻辑入口 `esim xxx.yyy:func.smoke` 配合 Rules `default` 时固定为 `$DV_TMP/xxx.yyy/default/func.smoke/`，一般形状是 `$DV_TMP/<dtb-key>/<rules-key>/<test-key>/`；点号形式原样保留。绝对 TC 必须位于 `$DV_HOME/<dtb>/tests/<test>.tc|yaml`，从相对路径把目录分隔转换为点号得到 dtb/test key；不符合该结构是输入错误。rules key 始终取解析后入口 Rules 文件名去掉 `.rules`/`.yaml` 的 stem，因此逻辑与绝对 selector 得到相同目录。默认新 invocation 丢弃该精确目录的旧仿真产物并重新创建干净目录；CLI `-k/--keep` 保留 simulator adapter 定义的工具缓存和 build artifacts（VCS 至少包括 `simv` 及关联目录），但仍完整执行 ff/build/run，并重写本次快照、总 waiver、Result snapshot 和全部受管日志。首版不计算 cache fingerprint 或自动跳过阶段，旧日志不得进入新结果。`tc.yaml`、`rules.yaml`、`result.yaml`、总 waiver、阶段日志和 EDA 产物均位于其中，YAML 不提供 `cwd` 字段。
_Avoid_: Configurable cwd, source directory

**Simulation directory lock**:
esim 在完成 CLI 解析和最小 selector 解析、得到 Simulation directory 后立即获取的非等待式独占内核文件锁，早于目录清理、缓存读取或任何写操作；主运行与 Log recheck 使用同一把锁。锁文件位于目标目录外并可记录 host/PID/命令，但文件存在不代表锁仍生效。锁描述符禁止传给子进程，因此 esim 正常退出、异常、崩溃或被 `SIGKILL` 时均由内核释放，不依赖删除锁文件。
_Avoid_: Lockfile-exists protocol, inherited lock descriptor

**Stage action**:
CLI `-a build` 或 `-a run` 请求使用既有 Simulation directory 的上游阶段缓存，只执行指定阶段动作。Stage action 隐含 `--keep`，要求目标目录已存在且绝不执行默认清理；同时显式提供 `-k` 合法但冗余。esim 仍重新解析当前 TC/Rules：`-a build` 要求 ff/filelist 上游配置字段与缓存一致且已有 flat filelist 可读，允许 build 及 run/metadata 变化并重做 build；`-a run` 要求 ff/filelist/build 上游配置字段一致且 simulator build artifact 有效，允许 run/metadata 变化并复用 build artifact。上游不兼容时执行前退出 2；检查通过后才以当前 Effective TC 更新快照、waiver 和 Result snapshot。esim 不扫描或 hash HDL、header、`-y` library 内容；选择 Stage action 即由用户声明未执行上游的源码依赖没有变化。Stage action 只接受目标阶段参数：two-step build 为 `-b`，three-step build 为 `-b/-e`，run 为 `-r`；其他 phase 参数是 CLI 用法错误。
_Avoid_: Full invocation, automatic cache hit

**Simulator-managed artifact**:
由 simulator adapter 强制确定路径、供 keep/Stage action/Log recheck 稳定定位的 build artifact 和日志。VCS 首版的 build artifact 固定为 Simulation directory 下的 `simv`（含关联目录），仿真主日志固定为 `simv.log`；adapter 自动加入对应 `-o`/`-l` 等参数。用户 phase/CLI args 若提供会改写这些路径的保留选项，执行前报冲突错误；未来 Cadence adapter 定义自己的等价产物与日志。
_Avoid_: User-selected output, inferred artifact

**VCS command construction**:
two-step build 为 `vcs -f <abs-flat> <merged-build-argv> -o <abs-simv> -l <abs-vcs.log>`；three-step analyze 为 `vlogan -f <abs-flat> <merged-analyze-argv> -l <abs-vlogan.log>`，elaborate 为 `vcs <merged-elaborate-argv> -o <abs-simv> -l <abs-vcs.log>`；run 为 `<abs-simv> <merged-run-argv> -l <abs-simv.log>`。Flat filelist 在前、Rules→TC→CLI 用户 args 居中、adapter 保留参数最后；用户 `-f/-o/-l` 冲突执行前报错，所有受管路径用绝对形式。
_Avoid_: Last-option-wins conflict, relative managed path

**esim flat filelist artifact**:
esim 在进程内调用共享 flattening engine，由 Rules-only top-level filelist 和合并后的 ff.args 生成的固定 `<simulation-directory>/flattened.f`，配套日志为 `ff.log`。输入、`-o/--output`、`-l/--log` 路径由 esim 管理，用户 ff.args 冲突时执行前退出 2。完整运行（含 `--keep`）重建它；`-a build` 要求并复用已有可读 artifact，`-a run` 不消费它但仍校验上游配置。
_Avoid_: User-named flat filelist, ff subprocess output

**ff argument**:
首版 `ff.args` 中唯一开放的 engine-owned 参数是可重复的 `-d/--define`，每次可带一个或多个宏；fragment 拆分后由 adapter 转成 ff 的结构化 macro 集合，按 ff 契约校验、区分大小写并去重。input/output/log/debug 由 esim 管理，未知或保留参数是 argv 输入错误而不是可忽略 YAML field；未来 engine 新增处理能力时再扩展 adapter。
_Avoid_: predefined_macros field, arbitrary ff CLI option

**Phase log**:
Simulation directory 中由实际执行节点覆盖生成的完整日志。VCS 工具日志固定为 `ff.log`、two-step build/three-step elaborate 的 `vcs.log`、three-step analyze 的 `vlogan.log` 和 run 的 `simv.log`；phase hook 日志为 `pre_<phase>.log`/`post_<phase>.log`，three-step build 外层也使用 `pre_build.log`/`post_build.log`。同一 hook 的 commands 汇入同一日志；未配置或未执行的 hook 不生成空日志，Result snapshot 记录本次实际日志，Stage action 只覆盖目标阶段相关日志。
_Avoid_: Appended invocation log, inferred executed phase

**Result snapshot**:
本次仿真目录中的 `result.yaml`，保存 action、阶段日志路径、命令退出码、Log findings、waiver 命中、ignored_fields 和当前 `PASS`/`FAIL`/`NOT_RUN` 等动态结果。每个未知字段还立即向终端打印 WARNING，并在 ignored_fields 中按“绝对来源文件 + 字段路径”去重记录，不保存字段值。完整运行或 run action 成功可得 PASS，任一实际执行节点失败为 FAIL；build action 成功只表示 build 请求完成，run 为 not_run 且顶层为 NOT_RUN，CLI 仍返回 0。`-a build` 不删除既有仿真主日志，后续 Log recheck 可按用户明确请求重新判断该日志。Result snapshot 与不可变的 `tc.yaml` 输入快照分离，并可由 Log recheck 原子更新当前判断；不保存 initial/recheck 历史。
_Avoid_: Run configuration, Effective TC

**Log recheck**:
通过 `esim check <absolute-sim-dir>` 执行；仿真目录参数必须是绝对路径。它不重新执行 ff、用户 hooks、编译器或仿真器，而是读取 `tc.yaml`/`result.yaml`，重新合并当前 waiver rules，并由 simulator adapter 定位仿真主日志（VCS 为 `simv.log`）。主日志存在时只对它执行专用 checker、通用 `fail`/`error` 扫描及 waiver 过滤，再更新当前 PASS/FAIL；主日志不存在时只给出 warning、保持当前 result 状态并返回 0，不把 build/hook 日志替代成仿真结论。已记录的 run Command failure 仍不能由文本 waiver 放过。`-a build` 后保留的旧主日志也可由用户显式 check。
_Avoid_: Rerun, resume simulation

**Log recheck exit code**:
`esim check` 以 `0` 表示命令正常完成且未判定出 FAIL，可能是主日志通过，也可能是主日志缺失并只产生 warning、Result snapshot 仍为 NOT_RUN；`1` 表示已记录 run Command failure 或主日志存在未放过 finding，`2` 表示 CLI 用法、运行目录、快照或 waiver 等输入错误，`3` 表示 esim 内部错误。调用方需要区分 PASS/NOT_RUN 时读取 `result.yaml`。
_Avoid_: Simulator exit code

**esim exit code**:
主仿真命令以 `0` 表示最终 PASS，`1` 表示已进入执行流程后的 hook/ff/tool Command failure 或未放过 finding，`2` 表示执行前可发现的 CLI、TC/Rules/include/filelist 声明、路径或 waiver 配置输入错误，`3` 表示 esim 内部错误。
_Avoid_: Tool exit code, Log recheck exit code

**TC selector**:
esim CLI 中定位入口 TC 的参数，可以是指向 `.tc` 或 `.yaml` 的绝对路径，也可以是将 DTB、test group 和 TC 名组合成的紧凑逻辑表达式，如 `xxx.yyy:func.smoke`。显式相对路径非法，两种后缀的文件内容都是标准 YAML。
_Avoid_: Test name, TC ID

**Rules selector**:
esim CLI `-f` 中定位入口 Rules 的参数，可以是指向 `.rules` 或 `.yaml` 的绝对路径，也可以是按 DTB-local 再 `dtb_common`、每个目录 `.rules` 再 `.yaml` 顺序搜索的逻辑名。缺省 `-f` 等价于逻辑名 `default`，显式相对路径非法，两种后缀的文件内容都是标准 YAML。
_Avoid_: Filelist option, Rules ID

**Log finding**:
某个 hook、ff 或 simulator 阶段的独立日志中，被该阶段检查器按行识别为潜在失败的内容。未被 waiver rule 放过的 finding 会使阶段失败；它与命令退出码表示的 Command failure 是两条独立判定通道。
_Avoid_: Raw error substring, process failure

**Hook log checker**:
对用户 phase hook 的完整日志逐行做大小写不敏感的 `fail` 或 `error` 子串扫描；子串位于单词内部（如 `failover`）也产生候选 Log finding。检查器故意不猜测 `0 errors` 等成功语义，项目通过统一 waiver rules 明确决定哪些文本可放过。
_Avoid_: Word-boundary matcher, tool-specific checker

**Tool log checker**:
由 simulator adapter 提供的工具专用日志识别器，并与大小写不敏感的 `fail`/`error` 通用子串扫描取并集。同一日志行命中多个检测规则时只产生一个 Log finding，但保留全部命中原因；ff 还优先使用展平引擎的结构化结果。VCS 与未来 Xcelium 使用各自 checker。
_Avoid_: Hook-only checker, simulator-neutral parser

**Built-in waiver rules**:
esim 内部为确定且普遍安全的 Log finding 放过条件预留的独立规则层。首版规则集为空，不预置任何具体模式；以后新增内置规则必须通过该扩展点进入统一 waiver 流程，并以 `// source: esim built-in` 作为第一来源块写入仿真目录的总 waiver 文件。空内置层不输出空来源块；最终来源顺序固定为 built-in、dtb_common、入口 DTB，禁止存在只在代码中隐式生效而未进入总文件的规则。
_Avoid_: Hard-coded suppression, implicit success heuristic

**Command failure**:
hook command、ff、编译器、仿真器或其他受 esim 管理的进程以非零状态退出。Command failure 始终使阶段失败，不能由基于日志文本的 waiver rule 放过。
_Avoid_: Log finding, waived exit code

**Hook command continuation**:
phase `hooks` 节点的 `continue_on_error` 同时控制该 phase 的 before/after 命令列表：某条 command 非零退出后是否继续当前列表的剩余 commands。它不放过 Command failure，不把 hook 改判为成功，也不允许进入后续 hook、工具或阶段。该字段只接受 YAML 规范小写布尔量 `true`/`false`；字符串、数字和 `yes`/`no` 均非法。合并时后层显式值覆盖前层，缺失则继承，最终缺省为 `false`。
_Avoid_: Ignore failure, continue simulation

**Hook command execution**:
`hooks` 是可选映射，空映射合法；`before` 和 `after` 是可选字符串列表，即使只有一条也不允许标量简写。缺失或空列表都不增加命令，且空列表不清除前层命令。每个列表项必须是非空单行 shell 字符串，含 CR/LF 或仅空白的项是已知字段值错误。每个 command 由独立的 `/bin/bash -o pipefail -c` 进程执行；同一 hook 的 commands 不共享 `cd`、export 或 shell function，但 stdout/stderr 依次汇入同一 hook 日志。合并后没有 command 的 before/after 从生成快照中省略，不执行也不生成日志；仅声明 `continue_on_error` 的片段可为后续合并进来的 before/after 命令提供配置。esim 不读取用户 `$SHELL`，也不提供 YAML `shell` 字段；需要 csh/zsh 时由 command 显式调用解释器，或直接执行带 shebang 的脚本。
_Avoid_: Shared shell session, login shell, implicit user shell

**esim cleanup**:
esim 自身不可由 TC/Rules 配置的可靠收尾路径，用于关闭日志、保存运行状态和释放 esim 管理的资源。它独立于用户 hooks，并在用户 hook 或主命令失败时仍执行；用户的阶段 `hooks.after` 只属于成功工作流，不承担 finally 语义。
_Avoid_: User after hook, configurable failure hook

**Phase hook**:
嵌入 `ff`、`build`、three-step 的 `analyze`/`elaborate` 或 `run` 具体阶段的用户 `hooks.before`/`hooks.after`。esim YAML 不提供顶层 `prepare`、`on_failure` 或 `finalize` hook；阶段前置工作归入对应 phase before，正常后处理归入对应 phase after。
_Avoid_: Global hook, cleanup hook

**Build flow shape**:
`two-step` 只允许 `build.args` 和 build 级 hooks，任何 `build.analyze`/`build.elaborate` 字段（包括空映射）都是执行前 schema 错误；`three-step` 只允许 `build.analyze`/`build.elaborate` 及相应 hooks，任何直接 `build.args`（包括空列表）同样非法。esim 不忽略或猜测错位参数。
_Avoid_: Phase coercion, implicit argument remapping

**Phase configuration**:
首版 `ff`、`build`、three-step `analyze`/`elaborate` 和 `run` 节点只支持 `args` 与 `hooks`（其中 flow 决定 build 的合法形状）。`timeout`、`environment`、`cwd`、`enabled` 等字段待出现明确需求后再加入；当前 schema 不认识的 phase 字段统一忽略并诊断，而不是失败。
_Avoid_: Future placeholder field, permissive phase mapping

**Argument fragment**:
phase `args` 列表中的一个字符串，可在一项中使用 POSIX shell quoting/escaping 写一个或多个参数（例如 `-d FPGA USE_DDR`）。esim 按全局配置合并顺序保留 fragments，再用 POSIX `shlex` 依次拆成最终 argv，然后对每个 token 按 ff 相同规则递归展开 `$NAME`/`${NAME}`；引号只分组，不抑制展开。phase args 专用的 `$$` 在环境展开期间受保护并最终变为一个字面量 `$`，例如 `$$unit → $unit`；该规则不作用于 hook shell commands。缺失/空值/循环是执行前输入错误，不支持 shell default、命令替换、tilde 或 glob。args 不通过 shell 执行，`&&`、`;`、`|` 等没有命令连接含义。非字符串项或非法 quoting 是执行前 schema/input 错误。
_Avoid_: Shell command, one-token argument

**Three-step build order**:
build 是 analyze/elaborate 的逻辑外层，顺序固定为 `build.before → analyze.before → analyze → analyze log check → analyze.after → elaborate.before → elaborate → elaborate log check → elaborate.after → build.after`。任一用户 hook、主命令或日志检查失败都会截断其后全部用户节点，包括尚未执行的 after；esim cleanup 仍独立执行。
_Avoid_: Reverse after order, user finally chain

**Waiver rule**:
用户在 `$DV_HOME/dtb_common/rules/` 和入口 TC 所属 DTB 的 `rules/` 下通过 `waive.txt`、`exclude.txt` 逐行提供 Log finding 放过条件；common 规则始终有效，入口 DTB 规则在其上补充，被 include 的配置不引入其所在 DTB 的 waiver。esim 将两层规则分别合并为仿真目录中的总 `waive.txt` 和总 `exclude.txt`，作为本次运行实际使用的可审计过滤条件：common 有效规则在前、入口 DTB 有效规则在后，保留各自顺序及重复项，去除原空行和注释，并以 `// source: <absolute-path>` 标记每个来源块；即使没有规则也生成两个总文件。这两份总文件统一过滤本次 invocation 的所有 phase hook 和工具日志，诊断保留 finding 所属阶段、日志以及命中的规则来源。`waive.txt` 使用 shell 风格 glob 对候选行做整行匹配，`exclude.txt` 使用正则表达式对候选行做单行 search；任意规则匹配即放过该 finding。两类规则默认区分大小写，regex 可用显式 flag（如 `(?i)`）改变语义。源文件解析时去除行首尾空白，忽略空行及首个非空白内容为 `#` 或 `//` 的整行注释，不支持行尾注释。各源文件均可选：缺失、为空或只有注释都表示该来源没有对应规则；文件存在但不可读则是运行前配置错误。所有有效规则在运行命令前统一严格校验，非法模式必须报告绝对路径、行号、原始规则及原因。规则不做跨行匹配，只影响判定，不删除、修改或隐藏原始日志。
_Avoid_: Log deletion, error suppression
