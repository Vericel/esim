# VCS two-step / three-step flow 与 esim hooks 生命周期

调查日期：2026-07-31  
重点版本：Synopsys VCS W-2024.09-SP1  
资料范围：仅使用本机该版本安装自带的 Synopsys 官方文档

## 结论摘要

1. VCS W-2024.09-SP1 官方所说的 **two-step flow** 是：

   ```text
   vcs 编译（同时构建实例层次并生成 simv）
       ↓
   simv 仿真
   ```

   典型命令：

   ```bash
   vcs -full64 -sverilog -f flat_verilog.f -top tb_top -o simv
   ./simv <run_options>
   ```

   第一个 `vcs` 命令不是 esim 所设想的“纯 analyze”；它把 Verilog/SystemVerilog 的分析、层次构建、代码生成和链接合并为官方称作 `Compilation` 的一步。

2. 官方明确说 two-step **只支持 Verilog HDL 和 SystemVerilog**。mixed-language 没有另一套“mixed-language two-step”定义；VHDL 或 mixed HDL 应采用 **three-step/UUM flow**：

   ```text
   vlogan / vhdlan 分析
       ↓
   vcs elaboration，生成 simv
       ↓
   simv 仿真
   ```

   mixed-language 典型命令：

   ```bash
   vlogan -full64 -sverilog -f flat_verilog.f
   vhdlan -full64 -f flat_vhdl.f
   vcs -full64 work.tb_top -o simv
   ./simv <run_options>
   ```

   多个 analyzer 命令仍属于同一个逻辑 `Analysis` 阶段，所以“three-step”描述的是阶段数，不一定等于 shell 命令数。W-2024.09-SP1 User Guide 的 Basic Usage Model 还明确要求 mixed flow 中先分析 Verilog，再分析 VHDL；VHDL 文件自身按 bottommost entity 到上层的顺序排列。

3. 当前官方 User Guide 把主要流程列为 two-step、three-step 和 partition compile，并没有把 **one-step flow** 列为一个独立正式流程。`vcs ... -R` 会在链接完成后立即运行生成的 executable，因此可被工程上俗称为“单命令编译并运行”：

   ```bash
   vcs -full64 -sverilog -f flat_verilog.f -top tb_top -o simv -R
   ```

   但这只是把 two-step 的 compilation 和 simulation 合并到一次命令调用，不应让 esim 因此删除逻辑上的 `build` 与 `run` 边界。同理，在 three-step 中 `vcs <top> -R` 只是把 elaboration 与 simulation 连续执行；此前的 analysis 仍然存在。

4. 对 esim，建议采用工具无关的主生命周期：

   ```text
   prepare sources（含 ff）
       → resolve build/cache
       → build artifact
       → run
       → check
       → finalize
   ```

   `analyze` 和 `elaborate` 应是 VCS three-step adapter 的 **build 子阶段**；不能作为所有 simulator/flow 都保证存在的公共生命周期边界。two-step 只有一个不可拆开的 `vcs` build 命令，在它中间无法可靠执行 `post_analyze` 或 `pre_elaborate` hook。

5. 推荐的最小用户级 hooks：

   ```yaml
   hooks:
     prepare: []
     pre_build: []
     post_build: []
     pre_run: []
     post_run: []
     pre_check: []
     post_check: []
     on_failure: []
     finalize: []
   ```

   其中 `prepare` 位于 ff 和 cache key 计算之前；`pre_build` 只在 cache miss、即将真正调用编译器时执行；`post_build` 表示“build artifact 已得到结果”，其状态可以是 `success`、`cached` 或 `failed`。这样 cache hit 不需要再增加一个强制的 `cache_hit` hook；hook 可通过上下文中的 `cache_status=hit` 判断。`finalize` 必须恰好执行一次。

## 官方定义与命令映射

### Two-step：Compilation + Simulation

*VCS User Guide*, Version W-2024.09-SP1, “Getting Started → Using the Simulator → Two-step Flow / Basic Usage Model” 明确给出：

```text
Compilation: vcs [compile_options] Verilog_files
Simulation:  simv [run_options]
```

同一章节说明：

- two-step 只支持 Verilog HDL 与 SystemVerilog；
- compilation 阶段构建 instance hierarchy 并生成 `simv`；
- simulation 阶段执行 `simv`。

因此 esim 的映射应是：

| VCS two-step | 外部命令 | esim 逻辑阶段 |
|---|---|---|
| Compilation | `vcs ... <sources>` | `build`；内部同时涵盖 analyze + elaborate/link |
| Simulation | `simv <run_options>` | `run` |

不能把 two-step 的第一个 `vcs` 命令只映射为 `analyze`，再期待独立的 `elaborate` 命令。官方对该步的定义已经包含层次构建和 `simv` 生成。

### Three-step：Analysis + Elaboration + Simulation

*VCS User Guide*, “VCS Flow → Three-step Flow” 和 “Getting Started → Using the Simulator → Three-step Flow” 给出的基本模型是：

```text
Analysis:
    vlogan [vlogan_options] file1.v file2.v
    vhdlan [vhdlan_options] file3.vhd file4.vhd

Elaboration:
    vcs [elaboration_options] design_unit

Simulation:
    simv [run_options]
```

SystemVerilog 的官方示例为：

```bash
vlogan -sverilog <vlogan_options> file1.sv file2.sv file3.v
```

analysis 生成并保存 elaboration 所需的 intermediate files；elaboration 使用这些文件构建 instance hierarchy、生成并链接 `simv`；最后执行 `simv`。

esim 的直接映射为：

| VCS three-step | 外部命令 | esim 逻辑阶段 |
|---|---|---|
| Analysis | 一个或多个 `vlogan` / `vhdlan` | `build.analyze` |
| Elaboration | `vcs ... design_unit` | `build.elaborate` |
| Simulation | `simv ...` | `run` |

这里的 `build.analyze` 可以包含多个有顺序约束的 command action。例如 mixed-language 是先 `vlogan`、后 `vhdlan`，但两者合起来仍是一个 Analysis 阶段。

### Verilog/SystemVerilog 与 mixed-language 的选择

| 设计类型 | two-step | three-step |
|---|---:|---:|
| Verilog | 官方支持 | 官方支持 |
| SystemVerilog | 官方支持 | 官方支持，使用 `vlogan -sverilog` |
| VHDL | 不支持 | 官方支持，使用 `vhdlan` |
| Verilog/SystemVerilog + VHDL | 不支持 | 官方支持，使用 `vlogan`/`vhdlan` 后再 `vcs` elaboration |

Application Note *VCS Two-Step Flow or Three-Step Flow*, Version W-2024.09-SP1, Chapter 1 “Introduction” 和 “Deciding on Two-Step Flow or Three-Step Flow” 还指出：

- two-step 面向 Verilog/SystemVerilog，只有一条 compilation command 和一条 simulation command；
- three-step 可用于 MX designs、pure Verilog 或 pure VHDL；
- three-step/UUM 通过 design/work logical library 保存 analysis 中间结果，并支持多 logical libraries。

所以若有人把：

```bash
vlogan ...
vhdlan ...
vcs ... -R
```

口头称作“mixed-language two-step”，那只是按进程调用把最后两阶段合并计数，不是 W-2024.09-SP1 官方的 two-step flow。对 schema、缓存键和 hooks 应继续按 three-step 的逻辑阶段处理。

## ff/filelist 应放在哪一步

### 原则

`ff` 是 esim 的 source preparation，不是 VCS 的 analysis。它必须发生在 **第一个消费 HDL source list 的 VCS 命令之前**，并且发生在 build cache key 最终计算之前：

```text
prepare hook
  → ff 展平并生成规范化 source manifest
  → 对 manifest、源文件、选项、工具版本等计算 cache key
  → cache lookup
  → 必要时调用 VCS build
```

这样由 `prepare` hook 生成或修改的 filelist/source 能进入缓存指纹；如果把 ff 放在 cache lookup 之后，会出现输入已经变化却误命中旧缓存的问题。

### Two-step

two-step 中源文件由 `vcs` compilation 消费，因此：

```bash
ff original.f > flat_verilog.f
vcs -full64 -sverilog -f flat_verilog.f ... -o simv
```

W-2024.09-SP1 User Guide 的 compilation 语法是 `vcs [compile options] Verilog_files`，并说明 `-file <filename>` 可包含 files 和 compile-time options。该版本 Command Reference 同时定义了常用的 `-f <filename>` filelist 方式；esim adapter 可选择与 ff 输出格式相匹配的 `-f` 或 `-file`，但它们都属于 compilation 输入。

### Three-step

three-step 中 HDL source list 由 analyzer 消费，而不是 elaboration 消费：

```bash
ff verilog.f > flat_verilog.f
vlogan -full64 -sverilog -f flat_verilog.f

ff vhdl.f > flat_vhdl.f
vhdlan -full64 -f flat_vhdl.f

vcs -full64 <elaboration_options> work.tb_top -o simv
```

User Guide 对 `vlogan -f` 和 `vhdlan -f` 都定义为包含 source files 的文件；对 elaboration 的 `vcs -file` 则定义为包含 **elaboration options**。因此不要把 HDL source filelist 延迟到 elaboration 的 `vcs` 命令。

对于 mixed-language，单一“纯文本 flat.f”通常不足以无歧义地同时喂给 `vlogan` 和 `vhdlan`。更稳妥的 ff 输出是一个规范化 manifest，至少保留：

- language/analyzer；
- logical library / `-work`；
- 稳定的文件顺序；
- include path、define 和 library option 的适用范围；
- 原 filelist 到最终源文件的来源链。

VCS adapter 再从 manifest 生成 `flat_verilog.f`、`flat_vhdl.f` 等 analyzer-specific 输入。不要只按扩展名粗暴分组后丢失 library 和顺序语义。

## 推荐的 esim 生命周期

### 公共阶段与 VCS adapter 子阶段

```text
invocation
  ├─ prepare sources
  │    └─ ff / manifest / input fingerprint
  ├─ resolve build
  │    ├─ cache hit  ───────────────────┐
  │    └─ cache miss → build            │
  │                    ├─ VCS two-step: vcs compilation
  │                    └─ VCS three-step:
  │                         ├─ analyze: vlogan/vhdlan
  │                         └─ elaborate: vcs
  ├─ build artifact ready ◀─────────────┘
  ├─ run: simv
  ├─ check
  └─ finalize
```

公共 hooks 应围绕稳定的 `build/run/check` 生命周期，而不是围绕某个工具恰好暴露的命令。adapter 内部仍应记录 `analyze_started`、`analyze_failed`、`elaborate_started` 等结构化事件，供日志、诊断和将来的高级扩展使用；当前不必全部开放为 YAML hooks。

### 最小 hooks 及精确定义

| Hook | 何时执行 | cache hit | 失败时 |
|---|---|---:|---|
| `prepare` | build 输入解析前；可生成 filelist/source | 执行，因为其输出参与 cache key | 失败则停止 build，转 `on_failure`、`finalize` |
| `pre_build` | cache miss 后、真正启动 tool build 前 | 不执行 | 失败则不启动编译器 |
| `post_build` | logical build 得到结果后 | 执行，`status=cached` | 也执行，`status=failed`，用于收集 build 日志 |
| `pre_run` | 已验证 `simv` artifact，启动前 | 与 cache 无关 | 失败则不启动 `simv` |
| `post_run` | `simv` 已启动并结束后 | 与 cache 无关 | 即使 exit nonzero/timeout 也执行，携带 outcome |
| `pre_check` | check 被计划且所需产物存在时 | 与 cache 无关 | 失败则 check 失败 |
| `post_check` | check 尝试结束后 | 与 cache 无关 | 执行并携带 check outcome |
| `on_failure` | 整个 invocation 的 primary failure 确定后 | 可执行 | 最多一次；自身失败不得递归触发 |
| `finalize` | invocation 退出前 | 执行 | 始终恰好一次，保留 primary failure |

推荐向每个 hook 提供结构化上下文或等价环境变量：

```text
mode            = test | build | run | check
phase           = prepare | build | run | check | finalize
status          = success | failed | cached | skipped
cache_status    = hit | miss | disabled | not_applicable
build_source    = fresh | cache | explicit_artifact
failed_phase    = prepare | build.analyze | build.elaborate | run | check | hook | none
artifact_dir
run_dir
log_path
exit_code
timed_out
```

`post_*` 的统一语义应是“该 logical phase 尝试/解析结束”，而不是“只有成功才执行”。这样失败日志收集不依赖另设大量 `build_failed`、`run_failed`、`check_failed` hooks；`on_failure` 用于一次性的失败响应，`finalize` 用于无条件收尾。

### Cache hit

cache hit 时推荐顺序：

```text
prepare
  → ff / fingerprint
  → cache lookup(hit)
  → restore and validate artifact
  → post_build(status=cached, cache_status=hit)
  → 后续 run/check（若本次 mode 包含）
  → finalize
```

明确不执行：

- `pre_build`；
- VCS compilation；
- VCS analysis/elaboration 子阶段。

`post_build` 在这里不是“编译器跑完”，而是“logical build 已解析为可用 artifact”。如果未来确有只在命中缓存时执行动作的需求，可以增加 hook 条件：

```yaml
post_build:
  - when: cache_status == "hit"
    command: [...]
```

不必先增加独立的 `cache_hit` 生命周期节点。

缓存 restore/validation 失败不应冒充普通 cache miss 静默重编译，除非策略明确允许。至少要记录 `cache_restore_failed`；严格模式进入 `on_failure`，修复模式可标记损坏条目后转为 cache miss。

### 阶段失败

默认采用 fail-fast：

- `prepare`/ff 失败：不查 cache、不 build、不 run、不 check；
- analysis 失败：不 elaboration、不 run；
- elaboration 失败：不 run；
- run 启动失败：不 check；
- run 已启动但 exit nonzero/timeout：执行 `post_run`；若日志/结果产物可用，可按策略继续 check 以补充诊断，但不能覆盖原始 run failure；
- check 失败：测试失败；
- 任一 primary failure 后执行一次 `on_failure`，最后执行 `finalize`。

失败优先级应保留最早的 primary failure。`on_failure` 或 `finalize` 自身再失败时追加 secondary diagnostics，不覆盖例如 `build.analyze` 的根因；若此前没有失败，`finalize` 失败可以使 invocation 失败。

### 仅 build

```text
prepare
  → ff/cache
  → [pre_build → tool build] 或 cache hit
  → post_build
  → finalize
```

不执行 `pre_run/post_run/pre_check/post_check`。`post_build` 完成只表示 artifact 可用或 build 失败，不应暗含测试通过。

### 仅 run

真正的 run-only 应要求显式或可确定的已有 artifact，并且不静默触发编译：

```text
resolve/validate existing artifact
  → pre_run
  → simv
  → post_run
  → pre_check/check/post_check（若 run 命令定义包含检查）
  → finalize
```

它不执行 `prepare`、ff、`pre_build`、`post_build`。artifact 缺失或不兼容属于 artifact resolution failure，进入 `on_failure` 和 `finalize`。如果产品希望“run，必要时自动 build”，应将其命名或文档化为 test/auto-build mode，而不是 run-only。

### Check 与 finalize

`check` 是 esim 对仿真产物的判定阶段，不是 VCS simulation 本身。它可能检查：

- simulator exit status；
- UVM summary、fatal/error pattern；
- expected/forbidden log pattern；
- 结果文件、coverage 或 scoreboard 输出。

当 `simv` 已经启动并产生可检查产物时，即使 exit nonzero，也可运行 check 以补充分类信息；但 check success 不得把 timeout、signal、license/launch failure 等 infrastructure/run failure 改写成 pass。若 `simv` 根本未启动或必需产物不存在，则将 check 标记为 skipped，并保留 skip reason。

`finalize` 的职责是无条件收尾，例如：

- 刷新/关闭报告；
- 归档已存在的日志；
- 写最终状态 manifest；
- 释放锁或临时资源。

它不是另一次结果检查，也不应依赖 build/run/check 成功。只要 invocation 已进入生命周期，`finalize` 就必须恰好执行一次，包括 cache hit、build-only、run-only、timeout、hook failure 和用户中断。

## 为什么不建议把 hooks 放进 analyze

若 schema 写成：

```yaml
analyze:
  args: [...]
  hooks:
    before: [...]
    after: [...]
```

会在 VCS two-step 下产生无法兑现的语义：唯一的 `vcs` compilation 命令内部已经同时完成分析、层次构建和链接，esim 没有进程边界可插入 `after analyze`。mixed-language three-step 的 Analysis 又可能包含多个 `vlogan`/`vhdlan` action，“after analyze”究竟是每条 analyzer 命令后还是整个 Analysis 后也会歧义。

因此应保持：

```text
top-level hooks     = esim lifecycle orchestration
analyze/elaborate   = tool adapter 的 build 子阶段及参数
```

将来若确有高级需求，可另加明确的 adapter-scoped hooks，例如 `vcs.after_vlogan_command`，但不应把它们伪装成所有 flow 都具备的通用阶段。

## 官方资料

以下均为本机 VCS W-2024.09-SP1 安装自带的 Synopsys 第一方资料。

### VCS User Guide

- 文档：*VCS® User Guide*
- 版本：W-2024.09-SP1，December 2024
- PDF：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/pdf/vcs_user_guide.pdf`
- 重点章节与 HTML：
  - Getting Started → Using the Simulator → Two-step Flow / Three-step Flow / Basic Usage Model  
    `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_user_guide/getting_started/using_simulator.html`
  - VCS Flow → Two-step Flow  
    `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_user_guide/vcs_flow/two_step_flow.html`
  - VCS Flow → Compilation  
    `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_user_guide/vcs_flow/compilation.html`
  - VCS Flow → Three-step Flow → Analysis / Elaboration / Simulation  
    `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_user_guide/vcs_flow/three_step_flow.html`

其中 `using_simulator.html` 的 Basic Usage Model 是本文命令序列的最直接出处；`three_step_flow.html` 还明确记载 `vlogan -f`、`vhdlan -f` 的 source-list 语义和 elaboration 的 `vcs -file` option-list 语义。

### VCS Two-Step Flow or Three-Step Flow Application Note

- 文档：*VCS Two-Step Flow or Three-Step Flow Application Note*
- 版本：W-2024.09-SP1，December 2024
- 章节：Chapter 1, “Introduction”; “Deciding on Two-Step Flow or Three-Step Flow”
- PDF：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/pdf/Using_Two-Step_Flow_or_Three-Step_Flow.pdf`
- HTML：
  - `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_recommended_topics/using_two_or_three_step_flow/introduction.html`
  - `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_recommended_topics/using_two_or_three_step_flow/deciding_on_two-step_flow_or_three-step_flow.html`

该 Application Note 是“two-step 仅面向 Verilog/SystemVerilog；three-step/UUM 面向 mixed-language/VHDL，也可用于 pure Verilog”结论的直接出处。

### VCS Command Reference Guide

- 文档：*VCS Command Reference Guide*
- 版本：W-2024.09-SP1
- 章节：Compilation/Elaboration Options 中的 `-f`、`-F`、`-file`、`-R`
- PDF：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/pdf/vcs_cmd_ref.pdf`
- HTML：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_cmd_ref/compiler_options/compilation_elaboration_options_compiler.html`

User Guide 的 Compilation 和 Three-step Flow 章节也分别说明 `-R` 会在 VCS 链接 executable 后立即运行它，因此本文只把“one-step”作为单命令调用方式，而不把它声明为 W-2024.09-SP1 的第三种官方主要 flow。
