# esim complete demo project

这是一个同时供自动测试和人工 VCS/Verdi smoke 使用的完整 DV 工程。它不再是
单一最小 testcase：yyy 展示 YAML/two-step 的复杂配置组合，zzz 展示
`.tc/.rules`/three-step 的完整 phase 生命周期，common Rules 展示 selector fallback。

逐项需求映射见 [FEATURES.md](FEATURES.md)。测试应先复制整个 fixture，再在副本上
执行，避免修改版本控制内的输入。

ff 逐项映射另见 [FF_FEATURES.md](FF_FEATURES.md)。

## 初始化

从仓库根目录执行：

```bash
export DV_HOME="$PWD/tests/fixtures/esim-demo-project/dv"
export DV_TMP=/tmp/esim-demo-runs
source "$DV_HOME/xxx/yyy/env/feature_setup.sh"
```

`feature_setup.sh` 同时展示配置路径和 phase args 的递归环境展开。普通 smoke 不依赖
这些附加变量；yyy complete/full 和 portable Rules 需要它们。

## ff 完整特性入口

`full.f` 是供 ff engine、CLI 和 esim/VCS 共用的正向综合 filelist。它包含
条件分支、两种嵌套基准、递归环境、注释、重复、define/incdir 分组、
`-v/-y`、透传选项和 symlink annotation。

```bash
mkdir -p /tmp/ff-demo-full
ff "$DV_HOME/xxx/yyy/tb/full.f" \
  -o /tmp/ff-demo-full/flattened.f \
  -d COMPLETE_YYY COMPLETE_LEFT \
  -d COMPLETE_RIGHT COMPLETE_LEAF \
  --debug -l /tmp/ff-demo-full/ff.log
```

相对 `-f` 必须从指定 launch directory 运行：

```bash
cd "$DV_HOME/xxx/yyy/tb/ff_cases/working-directory/launch"
ff ../top.f -o /tmp/ff-demo-working-directory.f
```

零源码也是合法结果：

```bash
mkdir -p /tmp/ff-demo-empty
cd /tmp/ff-demo-empty
ff "$DV_HOME/xxx/yyy/tb/ff_cases/empty.f"
```

环境循环场景展示三层 source chain 和退出码 1：

```bash
export FF_DEMO_CYCLE_A='$FF_DEMO_CYCLE_B'
export FF_DEMO_CYCLE_B='${FF_DEMO_CYCLE_A}'
ff "$DV_HOME/xxx/yyy/tb/ff_cases/environment-cycle/top.f"
```

### 输出安全与编码配方

这些能力会改变权限、symlink 或故意触发失败，因此只在 `/tmp` 副本中
执行：

```bash
ff_demo_tmp=$(mktemp -d /tmp/ff-demo-safety-XXXXXX)
cp "$DV_HOME/xxx/yyy/tb/ff_cases/empty.f" "$ff_demo_tmp/input.f"

# 既有普通输出保留 rw 位并清除 executable 位。
printf 'old\n' >"$ff_demo_tmp/output.f"
chmod 0754 "$ff_demo_tmp/output.f"
ff "$ff_demo_tmp/input.f" -o "$ff_demo_tmp/output.f"
stat -c '%a %n' "$ff_demo_tmp/output.f"

# 输出 symlink 节点被替换，target 内容不变。
printf 'target\n' >"$ff_demo_tmp/target.f"
ln -s "$ff_demo_tmp/target.f" "$ff_demo_tmp/link.f"
ff "$ff_demo_tmp/input.f" -o "$ff_demo_tmp/link.f"

# BOM + CRLF 输入固定输出为无 BOM UTF-8 + LF。
printf '\357\273\277// encoded\r\n' >"$ff_demo_tmp/crlf.f"
ff "$ff_demo_tmp/crlf.f" -o "$ff_demo_tmp/utf8-lf.f"
```

输入/输出/日志真实文件同一性、父目录权限、损坏 symlink、非 UTF-8、
glob/shell/Windows 路径和非法条件指令由 public-seam tests 在 `tmp_path` 副本上
构造；详细定位见 `FF_FEATURES.md`。

## 三组可运行入口

基础 smoke 保留最短路径：

```bash
esim xxx.yyy:func.smoke
esim xxx.zzz:func.smoke
```

完整配置覆盖复杂 include、merge、args、unknown fields 和全部 phase hooks：

```bash
esim xxx.yyy:features.complete -f full \
  -b "-debug_access+all" -r "+CLI=1"

esim xxx.zzz:features.complete -f full \
  -b "-kdb" -e "-debug_access+all" -r "+CLI=1"
```

只存在于 `dtb_common/rules` 的 Rules 会在 DTB-local 搜索失败后命中：

```bash
esim xxx.yyy:func.smoke -f portable
```

## Selector

逻辑 selector 和绝对 selector 映射到相同的 Simulation identity：

```bash
esim xxx.yyy:features.complete -f full

esim "$DV_HOME/xxx/yyy/tests/features/complete.yaml" \
  -f "$DV_HOME/xxx/yyy/rules/full.yaml"
```

搜索后缀顺序是 TC `.tc → .yaml`、Rules `.rules → .yaml`；yyy 和 zzz 分别让
两种后缀真实成为入口。

## 完整运行、keep 与 Stage action

默认完整运行先清理精确 Simulation directory，再执行 ff/build/run：

```bash
esim xxx.yyy:features.complete -f full
```

`--keep` 保留 simulator cache/build artifacts，但仍完整重做 ff/build/run 并覆盖本次
受管快照与日志：

```bash
esim xxx.yyy:features.complete -f full --keep
```

在已经完成一次 full run 后，可以只重做目标阶段：

```bash
esim xxx.yyy:features.complete -f full \
  -a build -b "-debug_access+all"

esim xxx.yyy:features.complete -f full \
  -a run -r "+ntb_random_seed=99"
```

Stage action 会重新解析当前配置并校验上游快照；它不 hash HDL 内容，选择 action
表示调用者确认未执行阶段的源码依赖没有变化。build 成功得到 `NOT_RUN`，run 才得到
`PASS/FAIL`。

## 日志、waiver 与 Log recheck

top_tb 会输出一条 common glob waiver 和一条 DTB-local regex waiver；Y-2026.03
编译日志噪声由 common regex 精确放过。原始日志不会被删除或改写。

```bash
esim check "$DV_TMP/xxx.yyy/full/features.complete"
```

`check` 只读取快照、重新合并当前 waiver 并重判 `simv.log`，不会再次执行 ff、hook、
VCS 或 simv。Command failure 不能被 waiver 放过。锁冲突、非法 include/YAML/regex、
角色/flow 错位和 cache 不兼容等失败场景由测试在 fixture 副本中构造。

## 运行产物

以 yyy complete/full 为例：

```text
$DV_TMP/xxx.yyy/full/features.complete/
├── flattened.f
├── rules.yaml
├── tc.yaml
├── result.yaml
├── waive.txt
├── exclude.txt
├── ff.log
├── pre_ff.log / post_ff.log
├── pre_build.log / post_build.log
├── vcs.log
├── pre_run.log / post_run.log
├── simv
├── simv.daidir/
└── simv.log
```

zzz three-step 额外产生 `vlogan.log`、`pre_analyze.log`、`post_analyze.log`、
`pre_elaborate.log` 和 `post_elaborate.log`。

## 真实 Y-2026.03 VCS/Verdi

完整 zzz 命令中的 `-kdb/-debug_access+all` 会生成 Verdi 可读取的设计数据库：

```bash
esim xxx.zzz:features.complete -f full \
  -b "-kdb" -e "-kdb -debug_access+all"
```

随后用团队批准的 Verdi Y-2026.03 启动器打开
`$DV_TMP/xxx.zzz/full/features.complete/simv.daidir`。demo 默认验证 KDB；没有主动
生成 FSDB，波形 dump 不是 esim 配置能力。

## 退出码

| 命令 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `esim ...` | PASS 或 build action 成功 | 执行失败/finding | 输入、配置、cache、锁错误 | 内部错误 |
| `esim check ...` | 未判定 FAIL | 主日志/既有 run failure | 输入或快照错误 | 内部错误 |

CI 在外部 VCS 进程边界使用 `ScriptedProcessRunner`，因此不要求 EDA license；最终
人工验收另外使用真实 Y-2026.03 VCS/Verdi。
