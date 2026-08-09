# esim User Guide

`esim` 是面向 VCS 的单用例仿真运行器。它按 Rules→TC→CLI 的顺序
合并 YAML，执行 ff→build→run，然后用统一规则检查每个实际执行节点的日志。

## 环境与目录

```bash
export DV_HOME=/proj/aaa/dv
export DV_TMP=/proj/aaa/dv_tmp
```

项目可按下列结构组织：

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
    └── tests/func/smoke.tc
```

waiver 文件位于 `rules/`，不是 `tb/`。common 规则始终生效，
入口 TC 所属 DTB 的规则作为补充。

## 运行命令

```bash
# 逻辑 selector，缺省 -f default
esim xxx.yyy:func.smoke

# 选择 coverage Rules，追加仿真参数
esim xxx.yyy:func.smoke -f coverage -r "+ntb_random_seed=17"

# TC 和 Rules 也可显式传入绝对路径
esim /proj/aaa/dv/xxx/yyy/tests/func/smoke.tc \
  -f /proj/aaa/dv/dtb_common/rules/coverage.rules
```

TC 逻辑 selector 是 `<dotted-dtb>:<dotted-test>`。Rules 逻辑名依次搜索
入口 DTB 和 `dtb_common` 的 `.rules`/`.yaml`。显式路径必须是绝对路径。

CLI 参数：

- `-f/--rules NAME|ABS_PATH`：Rules，缺省为 `default`。
- `-b FRAGMENT`：two-step build 或 three-step analyze 参数。
- `-e FRAGMENT`：three-step elaborate 参数。
- `-r FRAGMENT`：run 参数。
- `-k/--keep`：保留原有 simulator cache，但仍完整执行。
- `-a build|run`：只执行指定动作并复用上游缓存。

`-b/-e/-r` 可重复出现，每次接收一个 POSIX argv fragment。例如：

```bash
esim xxx.yyy:func.smoke -b "-full64 -debug_access+all" -r "+SEED=7"
```

## Rules 与 TC

Rules 声明全局仿真基线，只有 Rules 可声明且最终必须恰好有一个
`filelist`：

```yaml
include:
  - ./vcs_base.rules

filelist: $DV_HOME/xxx/yyy/tb/top.f
simulator: vcs
flow: two-step

ff:
  args:
    - -d ESIM_DEMO

build:
  args:
    - -full64 -sverilog -top top_tb

run:
  args:
    - +UVM_VERBOSITY=UVM_LOW
```

TC 表达具体用例，不声明 `filelist`/`simulator`/`flow`：

```yaml
description: Minimal smoke testcase
owner: verification-team
tags: [smoke, func]

include:
  - ../base.tc

run:
  args:
    - +UVM_TESTNAME=smoke_test
  hooks:
    before:
      commands:
        - source $DV_HOME/xxx/yyy/env/setup.sh && echo ready
        - csh -f -c 'source setup.csh; ./prepare.csh'
      continue_on_error: false
```

`tags` 通常写在 TC；Rules 中只建议放 `vcs`/`coverage` 等执行特征。
TC 可以自由 include TC 或 Rules，但不建议再 include CLI 已选择的
`default.rules`。不属于 schema 的字段会被忽略，终端打印 WARNING，并记入
`result.yaml.ignored_fields`。

three-step 的 build 形状为：

```yaml
flow: three-step
build:
  analyze:
    args: [-full64 -sverilog]
  elaborate:
    args: [-full64 top_tb]
```

hooks 可放在 `ff`、`build`、`run` 中，three-step 还可放在
`build.analyze`/`build.elaborate` 中。每条 command 原样交给独立的
`/bin/bash -o pipefail -c`；需要 csh/zsh 时在 command 里显式调用。

## 缓存动作与重检

```bash
# 复用 flattened.f，只重做 build
esim xxx.yyy:func.smoke -a build -b "-debug_access+all"

# 复用 simulator build artifact，只重做 run
esim xxx.yyy:func.smoke -a run -r "+ntb_random_seed=18"

# 更新 waiver 后只重判既有 simv.log
esim check /proj/aaa/dv_tmp/xxx.yyy/default/func.smoke
```

`-a build` 要求现有 `flattened.f` 与 ff/filelist 配置兼容；
`-a run` 还要求 build 配置未变且 `simv` 可执行。esim 不 hash HDL
内容，选择 stage action 即表示用户确认上游源码未变。

## 日志、waiver 与结果

日志检查不区分大小写搜索 `fail`/`error` 子串，包括 `failover`
等单词内命中。`waive.txt` 每行是区分大小写的 glob，`exclude.txt`
每行是区分大小写的 regex search；空行、`#` 和 `//` 整行注释会忽略。

仿真目录中的主要可审计产物是：

```text
rules.yaml  tc.yaml  result.yaml
waive.txt  exclude.txt
flattened.f  ff.log  vcs.log  simv.log
pre_<phase>.log  post_<phase>.log
```

退出码：成功或成功的 build action 为 0；执行/日志失败为 1；
受控输入错误为 2；esim 内部错误为 3。
