# ff 需求验证矩阵

以 `docs/ff-requirements.md` 为权威契约，验收面只使用公开 Python 引擎和
真实 `ff` CLI，文件系统用 pytest `tmp_path`，不 mock 自有解析模块。

| 需求类别 | 公开验证证据 |
|---|---|
| 默认/显式输出与 CLI 参数顺序 | `test_engine_writes_default_flat_filelist`、`test_cli_writes_explicit_output_filelist`、`test_cli_requires_input_to_be_the_first_argument` |
| 条件指令、宏集合和非活动分支 | `test_ifdef_*`、`test_elsif_*`、`test_condition_*`、`test_unselected_branch_skips_nonconditional_validation_and_side_effects` |
| `-f/-F`、基准、循环、重复和 source chain | `test_uppercase_f_*`、`test_lowercase_f_*`、`test_recursive_filelist_cycle_*`、`test_repeated_filelist_references_and_sources_are_not_deduplicated`、`test_nested_*source_chain` |
| `//`/`/* */`、尾注释与注释提升 | `test_active_blank_lines_*`、`test_multiline_block_*`、`test_filelist_reference_*comment`、`test_block_comment_*` |
| 环境变量语法、递归、缺失/空/循环 | `test_source_path_expands_*`、`test_environment_*`、`test_source_path_rejects_malformed_environment_references` |
| source、`-v/-y`、`+incdir+`、透传选项 | `test_v_*`、`test_y_*`、`test_incdir_*`、`test_unknown_simulator_options_*` |
| 不支持语法：空白、glob、续行、shell、Windows/UNC | `test_source_path_rejects_*`、`test_all_recognized_path_entries_reject_glob_metacharacters`、`test_backslash_line_continuation_*` |
| UTF-8 BOM/CRLF 输入和 UTF-8 LF 输出 | `test_utf8_bom_and_crlf_input_renders_utf8_lf_without_bom`、`test_non_utf8_filelist_reports_structured_error` |
| symlink 逻辑路径、target annotation 和真实身份 | `test_symlinked_*`、`test_all_recognized_simulator_paths_annotate_symlink_targets`、`test_output_symlink_to_nested_input_is_rejected_by_real_identity` |
| 可读性、输出父目录、原子替换和权限 | `test_unreadable_*`、`test_output_parent_*`、`test_success_atomically_*`、`test_new_output_permissions_*`、`test_flatten_failure_preserves_*` |
| onelog、`-l`、`--debug`、summary 和日志安全 | `test_cli_log_*`、`test_cli_debug_*`、`test_cli_controlled_failure_*`、`test_cli_rejects_log_*`、`test_cli_replaces_log_symlink_*` |
| 发布物使用正式 onelog 依赖且不混入 vendor 缓存 | `test_wheel_uses_versioned_onelog_dependency` |
| 退出码 0/1/2/3 | CLI 成功测试、`test_cli_reports_flatten_error_without_python_traceback`、`test_cli_requires_input_to_be_the_first_argument`、`test_cli_returns_three_for_unexpected_internal_failure` |

最终验收命令：

```bash
python -m compileall -q src
pytest -q
python -m pip wheel . --no-build-isolation --no-deps
python -m pip install --no-index --find-links WHEELHOUSE esim==0.1.0
```
