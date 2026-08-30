# esim 首版特性矩阵

本矩阵记录 esim 首版的公开能力边界。正常能力由 fixture
文件和可执行命令展示；会使工程非法或故意失败的能力由 pytest 在 `tmp_path`
副本中构造，不污染可直接运行的 demo。

| 需求能力 | demo / 命令证据 | 自动验证证据 |
|---|---|---|
| Rules/TC 角色及 `.yaml` | `xxx/yyy/rules/full.yaml`、`tests/func/smoke.yaml` | 配置编译回归 |
| 复杂 two-step TC 全字段参考 | `tests/features/complete.tc`（`complete.yaml` 链接） | `test_complete_tc_demo_composes_every_configuration_layer` |
| `.rules/.tc` 传统后缀 | `xxx/zzz/rules/full.rules`、`tests/features/complete.tc` | `test_complete_three_step_demo_runs_every_nested_hook_and_cli_argument` |
| 逻辑与绝对 TC/Rules selector | README“Selector”命令 | `test_absolute_tc_and_rules_derive_the_same_simulation_identity` |
| 缺省 DTB-local Rules | 两个 DTB 的 `default.*` | `test_logical_tc_uses_default_rules_and_derives_simulation_identity` |
| DTB-local → common Rules fallback | `dtb_common/rules/portable.yaml`、`-f portable` | `test_logical_rules_fall_back_to_a_runnable_common_configuration` |
| 相对/绝对/环境 include | yyy `full.yaml` 与 `tests/fragments/` | complete-yaml 配置测试 |
| 跨角色 include 与菱形去重 | 两个 Rules 分支共同 include `tests/fragments/shared.yaml` | complete-yaml 的 merge order 字面值 |
| 递归环境展开 | `feature_setup.sh` 中相互引用的变量 | complete-yaml 配置与 workspace 测试 |
| description/owner 入口专属 | complete 入口与 fragment 中不同的值 | complete-yaml 配置测试 |
| tags 追加及稳定去重 | `duplicate` tag 分布在多个 fragment | complete-yaml 配置测试 |
| unknown field 忽略与诊断 | `unsupported-fields.yaml` Rules/TC 中的 `metadata`、`ff.timeout`、`run.enabled` | dedicated unsupported-fields workspace 的 warnings/result |
| args 合并、shlex quoting、递归展开、`$$` | yyy extended TC 和 CLI `-b/-r` | complete-yaml 配置测试 |
| ff `-d/--define` 与条件 filelist | `tb/full.f`、`COMPLETE_YYY` | complete-yaml flattened.f 断言 |
| two-step | yyy default/full Rules | complete-yaml workspace 测试 |
| three-step | zzz default/full Rules | complete-three-step 应用测试 |
| ff/build/run before/after | yyy full Rules/TC | complete-yaml workspace logs |
| build/analyze/elaborate 嵌套 hooks | zzz full-base Rules | complete-three-step node order |
| hook 独立 Bash 与日志聚合 | base/smoke/complete hooks | `test_run_hooks_use_independent_bash_commands_and_aggregate_logs` |
| phase 级 `continue_on_error` 合并与失败截断 | yyy full-left/complete 配置 | 配置继承测试与 execution failure 测试 |
| VCS 受管命令/路径 | two-step/three-step adapter | `test_esim_vcs_adapter.py` |
| 默认 clean | README full run；complete workspace 预置 stale 文件 | complete-yaml workspace 测试 |
| `--keep` 完整重跑 | README 操作命令 | WorkspaceMode 及完整运行回归 |
| Simulation directory lock | 同一目录主运行/check 共锁 | `test_lock_conflict_is_non_waiting_and_happens_before_clean` |
| `-a build` / `-a run` | README Stage action 命令 | `test_build_then_run_actions_reuse_only_their_required_upstream_cache` |
| 上游 cache 兼容性 | README 注意事项 | application cache rejection tests |
| glob/regex、common/local waiver | 四层 `waive.txt`/`exclude.txt` | `test_esim_log_policy.py` 与真实 VCS smoke |
| finding 与 Command failure 独立 | README“失败与重检”说明 | execution failure tests |
| rules/tc/result snapshots | complete workspace 运行目录 | complete-yaml workspace 测试 |
| flat filelist、phase logs、simv | complete workspace 运行目录 | complete-yaml/three-step 应用测试 |
| `esim check` Log recheck | README check 命令 | `test_esim_application_check.py` |
| 主命令/check 退出码 | README 退出码表 | CLI 与 application tests |

明确不在首版范围：Xcelium、suite/regression、YAML `timeout/environment/cwd/enabled`
执行语义、自动 cache fingerprint 和内置 waiver。专用 unsupported-fields fixtures
中的同名 unknown fields 只用于展示“忽略并审计”，不表示支持这些未来能力。

ff 的完整 filelist/CLI/engine 能力映射见 [FF_FEATURES.md](FF_FEATURES.md)。
