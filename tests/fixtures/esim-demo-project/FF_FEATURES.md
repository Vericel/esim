# ff 完整特性矩阵

本矩阵以 `docs/requirements/ff.md` 为权威契约。可同时成功的语法集成在
`xxx/yyy/tb/full.f`；需要特定启动目录、零源码或故意失败的场景放在
`xxx/yyy/tb/ff_cases/`。输出权限、symlink 替换等需要可变状态的场景必须
在 `tmp_path` 或 `/tmp` 副本上运行。

| ff 契约能力 | demo 输入/操作 | 公开验证证据 |
|---|---|---|
| CLI 默认/显式输出 | `ff_cases/empty.f`、README 完整命令 | `test_demo_empty_source_case_writes_default_flat_filelist`、`test_cli_writes_explicit_output_filelist` |
| `-d/--define` 重复使用、去重与确定排序 | yyy complete Rules 的四个宏、`full.f` | `test_complete_demo_combines_supported_filelist_syntax_for_vcs`、CLI define tests |
| `-l/--log`、`--debug`、覆盖与原子发布 | README debug/log 命令 | `test_cli_logging.py` |
| CLI 退出码 0/1/2/3 | 正向 full/empty、environment-cycle 与 README 错误命令 | `test_cli_errors.py`、`test_distribution.py` |
| 一行一 logical entry、POSIX 路径 | 所有 `tb/**/*.f` | `test_engine_inputs.py`、`test_engine_path_validation.py` |
| `ifdef/ifndef/elsif/else/endif` 及嵌套 | `ff_features/conditions.f` | complete-demo engine test、`test_engine_conditions.py` |
| 非活动分支跳过环境/路径校验 | `conditions.f`、`ff_cases/empty.f`、`full.f` 中的 `inactive_missing.sv` | complete-demo engine/CLI tests |
| 行注释、空行、单/多行块注释、尾注释 | `full.f`、`conditions.f`、`nested/root.f` | complete-demo engine test、`test_engine_comments.py` |
| 顶层默认 filelist-relative 基准与 `-F` | `full.f` 到 `ff_features/` 的多层引用 | complete-demo engine test |
| `-f` 启动工作目录基准 | `ff_cases/working-directory/` | `test_demo_lowercase_f_case_uses_its_launch_directory` |
| 重复 filelist/源码不去重 | `nested/root.f` 两次引用 `repeated.f` | complete-demo engine test |
| 引用循环与完整 source chain | `ff_cases/environment-cycle/` 展示三层 chain；循环 filelist 由临时变体构造 | demo environment-chain test、`test_engine_filelists.py` |
| `$NAME`、`${NAME}`、多层递归环境快照 | `feature_setup.sh`、`full.f`、`options.f` | complete-demo engine/esim tests |
| 缺失、空值和环境循环 | `ff_cases/environment-cycle/` 及其 `environment` 快照 | demo environment-chain test、`test_engine_environment.py` |
| 普通源码、`-v`、`-y`、多 `+incdir+` | `options.f`、`full.f`、`include/`、`library/` | complete-demo engine test |
| 仿真器透传选项与输入 `+define+` | `options.f` 的 `-notice/+libext+`、top/nested define | complete-demo engine test、`test_engine_options.py` |
| 命令行 define、输入 define、incdir、其他内容四组稳定渲染 | yyy complete `flattened.f` | complete-demo engine/esim artifact tests |
| 路径绝对化与读取/类型校验 | 所有正向资源；临时副本用于权限变体 | `test_engine_inputs.py`、`test_engine_options.py` |
| symlink 逻辑路径和物理 target annotation | `ff_features/symlink.f`、`sources/repeated_link.sv` | `test_complete_demo_preserves_a_symlink_source_and_annotates_its_target` |
| UTF-8 BOM/CRLF 输入与 UTF-8 LF 输出 | README `/tmp` 编码配方 | `test_utf8_bom_and_crlf_input_renders_utf8_lf_without_bom` |
| 原子替换、失败保留、rw 保留/清除 x、umask | README `/tmp` 输出安全配方 | `test_engine_output.py` |
| 输出/log symlink 节点替换和真实输入同一性拒绝 | README `/tmp` symlink/冲突配方 | `test_engine_output.py`、`test_cli_errors.py` |
| 空源码结果 | `ff_cases/empty.f` | demo empty CLI test |
| 结构化 `FlattenError`、source/environment chain | `ff_cases/environment-cycle/` | demo environment-chain test |
| esim 共用同一 engine 和 invocation environment | yyy `features.complete/full` | complete-yaml workspace artifact test |

## 明确拒绝的输入

mixed-language、logical library、glob、反斜杠续行、含空白路径、shell 展开和
Windows/UNC 路径不是正向特性。它们作为受控拒绝行为由
`test_engine_path_validation.py` 与条件/选项测试使用 `tmp_path` 变体验证，
不混入可运行的 VCS filelist。
