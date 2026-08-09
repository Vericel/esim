# ff 完整特性 demo 设计

## 背景

现有 `tests/fixtures/esim-demo-project` 已能展示 esim 的配置、执行和审计能力，
但其 filelist 仅覆盖了 ff 的嵌套引用、预定义宏和简单条件分支。后续测试
需要一套可直接复用的完整正向 fixture，同时不破坏 VCS Y-2026.03 仿真。

## 设计目标

- 在 yyy 的 complete/full 路径中展示 ff 所有可成功组合的用户能力。
- 通过独立顶层 filelist 表达冲突、错误和输出安全等不能进入正常
  VCS 编译路径的能力。
- 以已知 flat filelist 字面值作为回归证据，避免按实现算法重新计算期望值。
- 保持正常 demo 无非法语法、无损坏链接、无缺失路径，可继续供 esim/VCS
  真实运行。

## 场景结构

1. `xxx/yyy/tb/full.f` 作为 esim complete 的正向综合入口，组合：
   - 命令行预定义宏和输入 `+define+`；
   - `ifdef/ifndef/elsif/else/endif` 嵌套条件；
   - `-f` 工作目录引用和 `-F` filelist-relative 引用；
   - 普通源码、`-v`、`-y`、多目录 `+incdir+`、未知仿真器选项；
   - 环境变量的 `$NAME`/`${NAME}`、多变量和递归展开；
   - 行注释、块注释、尾注释、空行、重复条目和重复 filelist 引用；
   - symlink 逻辑路径与 target annotation。
2. `tb/ff_features/` 收纳可读的子 filelist、include 目录、library 目录、
   源码和 symlink，不把演示细节堆在一个文件。
3. `tb/ff_cases/` 收纳不参与 VCS 正常仿真的顶层输入，用于后续测试 CLI
   日志、输出发布、编码、空源码结果和受控错误。非法内容按一场景一文件隔离。

## Public seam 提案

- `ff` CLI：默认/显式输出、`-d/--define`、`-l/--log`、`--debug`、退出码。
- 公开 flattening engine：用环境快照展开正向综合 filelist 和隔离的受控错误场景。
- flat filelist 文本产物：分组顺序、注释、逻辑路径、symlink annotation、
  UTF-8 LF 与原子替换的可观察结果。
- esim 只用于证明同一正向 filelist 能在 complete/full 路径中被消费，不通过
  esim 内部实现验证 ff。

## 非目标

- 不展示契约明确不支持的 mixed-language、logical library、glob、shell 展开、
  Windows/UNC 路径转换或 source-map sidecar。
- 不为 demo 新增 ff 生产功能或改变已确认契约。
- 不将输出/日志冲突、循环引用等运行时条件固化成会破坏仓库的常驻状态；
  测试需要可变文件系统时复制到 `tmp_path`。

## 验收

- `docs/requirements/ff.md` 每项已支持行为都映射到 demo 文件、操作命令或公开
  seam 测试。
- 正向综合场景的 flat filelist 与已知字面值一致，并可被 VCS Y-2026.03 消费。
- 相关回归、完整 pytest、`scripts/check.sh` 和真实 esim/VCS smoke 通过。
