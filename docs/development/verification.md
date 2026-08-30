# ff 需求验证矩阵

以 `docs/requirements/ff.md` 为权威契约，验收面只使用公开 Python 引擎和
真实 `ff` CLI，文件系统用 pytest `tmp_path`，不 mock 自有解析模块。

## esim 实施中验证

esim 以 Configuration、Application、CLI 和 Simulation directory 文件为
public seams，仅在外部进程边界使用 scripted runner。当前已实现的可执行证据：

| esim 需求类别 | 公开验证证据 |
|---|---|
| 逻辑 TC、缺省 Rules 搜索和 Simulation identity | `test_logical_tc_uses_default_rules_and_derives_simulation_identity` |
| 绝对 TC/Rules 与逻辑入口一致的目录映射 | `test_absolute_tc_and_rules_derive_the_same_simulation_identity` |
| 相对 TC 路径和 selector 搜索失败诊断 | `test_relative_tc_path_is_rejected_as_an_input_error`、`test_missing_logical_tc_reports_the_searched_candidates` |
| VCS two-step/three-step 命令、受管 artifact/log 和保留选项 | `test_two_step_plan_uses_managed_inputs_outputs_and_logs`、`test_three_step_plan_splits_analyze_and_elaborate_commands`、`test_plan_rejects_user_option_that_overrides_a_managed_path` |
| waiver 来源合并、总文件、finding、Y-2026 许可证回退码和非法 glob/regex 聚合诊断 | `test_waivers_merge_common_then_entry_rules_and_render_source_blocks`、`test_log_evaluation_finds_substrings_inside_words_and_applies_both_waivers`、`test_demo_waives_known_y2026_license_fallback_codes`、`test_all_invalid_regex_waivers_are_reported_before_execution`、`test_invalid_glob_and_regex_waivers_are_reported_together` |
| 进程完整日志与非零状态 | `test_subprocess_runner_combines_complete_output_and_returns_nonzero_status` |
| clean workspace 精确范围、非等待锁、快照缓存及原子发布 | `test_clean_workspace_discards_only_the_exact_simulation_directory`、`test_lock_conflict_is_non_waiting_and_happens_before_clean`、`test_workspace_publishes_input_snapshots_and_total_waivers`、`test_workspace_atomically_replaces_the_current_result`、`test_cached_workspace_loads_the_three_required_snapshots` |
| two-step ff/build/run、artifact 校验和 PASS/FAIL/NOT_RUN | `test_full_two_step_execution_runs_ff_build_and_run_to_pass`、`test_successful_build_without_required_artifact_does_not_run`、`test_build_action_reuses_flat_filelist_and_preserves_existing_run_log`、`test_run_action_rejects_invalid_vcs_build_artifact_before_execution` |
| hook Bash 边界、聚合日志、`continue_on_error` 和失败截断 | `test_run_hooks_use_independent_bash_commands_and_aggregate_logs`、`test_hook_continue_on_error_finishes_only_the_current_hook_then_stops` |
| tool/ff Command failure 与 Log finding 独立记录 | `test_nonzero_tool_exit_still_records_log_findings_and_stops`、`test_flatten_failure_still_records_ff_log_findings_and_stops` |
| three-step 外层 build 与 analyze/elaborate/run hook 顺序 | `test_three_step_execution_preserves_nested_build_hook_order` |
| Rules/TC include 合并、args/环境展开、hook 继承、顶层/结构/标量节点类型、filelist source chain 和快照 | `test_compile_expands_rules_and_tc_include_graphs_in_global_order`、`test_phase_args_split_before_recursive_environment_expansion_and_dollar_escape`、`test_hook_continue_on_error_is_inherited_until_explicitly_overridden`、`test_compile_rejects_explicit_null_structural_mapping`、`test_compile_rejects_tc_without_a_top_level_mapping`、`test_compile_rejects_explicit_null_string_field`、`test_duplicate_filelists_report_every_source_and_include_chain`、`test_compile_renders_resolved_rules_and_effective_tc_snapshots` |
| logical selector 路径边界 | `test_logical_tc_rejects_non_dotted_path_segments_before_search`、`test_logical_rules_name_rejects_path_syntax` |
| Application 端到端、stage cache 兼容性与产物预检 | `test_application_runs_full_two_step_flow_and_publishes_auditable_result`、`test_run_action_rejects_changed_build_configuration_before_commands`、`test_stage_action_rejects_missing_required_cache_before_publishing_inputs`、`test_build_then_run_actions_reuse_only_their_required_upstream_cache` |
| 独立 check 重建 waiver、重判主日志、保留 Command failure 和缺日志 warning | `test_check_rebuilds_waivers_and_preserves_recorded_run_command_failure`、`test_check_warns_and_preserves_status_when_the_primary_log_is_missing` |
| 真实 esim CLI 组合根、VCS 进程边界和退出码 | `test_real_cli_runs_the_demo_through_the_vcs_process_boundary`、`test_cli_maps_a_controlled_input_error_to_exit_two`、`test_cli_rejects_phase_arguments_that_do_not_belong_to_the_action` |
| 不存在的 EDA 工具转为可审计 Command failure | `test_missing_tool_is_recorded_as_a_command_failure_in_its_log` |
| 完整 TC demo 的跨角色菱形 include 去重诊断、递归环境、args、tag、unknown fields 与 two-step hooks | `test_complete_tc_demo_composes_every_configuration_layer` |
| 完整 three-step demo 的 build/analyze/elaborate/run hooks 与 CLI 阶段参数 | `test_complete_three_step_demo_runs_every_nested_hook_and_cli_argument` |
| common Rules selector fallback 与环境化 DTB filelist | `test_logical_rules_fall_back_to_a_runnable_common_configuration` |
| 完整 demo 的条件 flat filelist、默认 clean、快照、unknown field/菱形 include 诊断、日志、waiver 和 simulator artifact | `test_complete_tc_demo_publishes_every_auditable_workspace_artifact` |

其余 esim 行为将随 TDD 纵向切片加入本矩阵；在相应测试和实现完成前不视为
已验证。

## User Guide 生成验证

| 用户文档能力 | 公开验证证据 |
|---|---|
| ff/esim Markdown 一次生成两份内嵌样式的 standalone HTML | `test_generator_cli_creates_both_standalone_user_guides` |
| 质量门禁发现缺失或过期的生成 HTML | `test_generator_check_reports_each_stale_user_guide` |
| 简介与章节布局分离、中文标题使用稳定显式锚点 | `test_generator_separates_intro_and_uses_explicit_section_ids` |
| 窄屏使用原生可折叠章节导航 | `test_generator_uses_collapsible_mobile_navigation` |
| YAML/Bash fenced code 生成离线 token 颜色 | `test_generator_adds_offline_syntax_colours_to_fenced_code` |
| 页面使用多色层级并显示代码语言标签 | `test_generator_uses_multihue_palette_and_code_language_labels` |
| 无 JavaScript 时桌面章节导航保持可见 | `test_generator_keeps_desktop_navigation_visible_without_javascript` |
| H2 章、H3 节生成嵌套内容和两级导航 | `test_generator_renders_chapters_sections_and_two_level_navigation` |
| 平铺章或少于两章的指南在生成阶段失败 | `test_generator_rejects_flat_guides_without_chapter_sections`、`test_generator_rejects_guides_with_fewer_than_two_chapters` |

## ff 验证证据

| 需求类别 | 公开验证证据 |
|---|---|
| 默认/显式输出与 CLI 参数顺序 | `test_engine_writes_default_flat_filelist`、`test_cli_writes_explicit_output_filelist`、`test_cli_requires_input_to_be_the_first_argument` |
| 条件指令、宏集合、HDL define 和非活动分支 | `test_predefined_macros_select_branches_and_render_sorted_hdl_defines`、`test_cli_define_option_selects_all_named_macro_branches`、`test_elsif_*`、`test_condition_*`、`test_unselected_branch_skips_nonconditional_validation_and_side_effects` |
| `-f/-F`、基准、循环、重复和 source chain | `test_uppercase_f_*`、`test_lowercase_f_*`、`test_recursive_filelist_cycle_*`、`test_repeated_filelist_references_and_sources_are_not_deduplicated`、`test_nested_*source_chain` |
| `//`/`/* */`、尾注释与注释提升 | `test_active_blank_lines_*`、`test_multiline_block_*`、`test_filelist_reference_*comment`、`test_block_comment_*` |
| 环境变量语法、递归、缺失/空/循环及调用快照 | `test_source_path_expands_*`、`test_environment_*`、`test_source_path_rejects_malformed_environment_references`、`test_engine_can_expand_from_an_invocation_environment_snapshot` |
| 全局稳定分组、source、`-v/-y`、`+define+`、`+incdir+`、透传选项 | `test_filelist_defines_are_promoted_after_command_line_defines_stably`、`test_incdirs_are_promoted_with_comments_and_symlink_annotations`、`test_v_*`、`test_y_*`、`test_incdir_*`、`test_unknown_simulator_options_*` |
| 不支持语法：空白、glob、续行、shell、Windows/UNC | `test_source_path_rejects_*`、`test_all_recognized_path_entries_reject_glob_metacharacters`、`test_backslash_line_continuation_*` |
| UTF-8 BOM/CRLF 输入和 UTF-8 LF 输出 | `test_utf8_bom_and_crlf_input_renders_utf8_lf_without_bom`、`test_non_utf8_filelist_reports_structured_error` |
| ff 完整 demo 的条件、注释、嵌套、环境、选项、重复和稳定分组 | `test_complete_demo_combines_supported_filelist_syntax_for_vcs` |
| ff demo symlink 注释、零源码 CLI 和工作目录 `-f` | `test_complete_demo_preserves_a_symlink_source_and_annotates_its_target`、`test_demo_empty_source_case_writes_default_flat_filelist`、`test_demo_lowercase_f_case_uses_its_launch_directory` |
| ff demo 受控错误的 source chain 和 environment expansion chain | `test_demo_nested_error_reports_source_and_environment_chains` |
| symlink 逻辑路径、target annotation 和真实身份 | `test_symlinked_*`、`test_all_recognized_simulator_paths_annotate_symlink_targets`、`test_output_symlink_to_nested_input_is_rejected_by_real_identity` |
| 可读性、输出父目录、原子替换和权限 | `test_unreadable_*`、`test_output_parent_*`、`test_success_atomically_*`、`test_new_output_permissions_*`、`test_flatten_failure_preserves_*` |
| onelog、`-l`、`--debug`、summary 和日志安全 | `test_cli_log_*`、`test_cli_debug_*`、`test_cli_controlled_failure_*`、`test_cli_rejects_log_*`、`test_cli_replaces_log_symlink_*` |
| 发布物使用带 PEP 561 内联类型的 onelogg 0.1.2 依赖且不混入 vendor 缓存；本地 wheel 构建不修改 checkout 中的构建产物；开发环境具备 `--no-build-isolation` 所需的精确版本构建工具；wheelhouse 不覆盖非空目录 | `test_local_wheel_build_leaves_project_build_artifacts_unchanged`、`test_esim_wheel_preserves_the_standalone_ff_command`、`test_wheel_uses_typed_onelogg_dependency`、`test_wheelhouse_builder_preserves_and_rejects_nonempty_output` |
| 退出码 0/1/2/3 | CLI 成功测试、`test_cli_reports_flatten_error_without_python_traceback`、`test_cli_requires_input_to_be_the_first_argument`、`test_cli_returns_three_for_unexpected_internal_failure` |

## 回归选择

```bash
# 全量回归
.venv/bin/python -m pytest

# 一个稳定能力
.venv/bin/python -m pytest tests/test_engine_conditions.py

# 一条精确用例
.venv/bin/python -m pytest \
  tests/test_engine_conditions.py::test_elsif_keeps_first_matching_alternative_branch

# 一次性的跨文件筛选
.venv/bin/python -m pytest tests/test_engine_*.py -k 'symlink or output_parent'
```

最终验收命令：

```bash
.venv/bin/python -m compileall -q src
bash tools/quality/check.sh
FF_PYTHON=.venv/bin/python \
  bash tools/packaging/build-wheelhouse.sh /tmp/esim-wheelhouse
```
