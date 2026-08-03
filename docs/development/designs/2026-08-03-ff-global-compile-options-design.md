# ff 全局编译选项排序设计

日期：2026-08-03

## 目标

扩展 `ff` 的输出契约，使调用者通过 `-d/--define` 提供的预定义宏既参与
filelist 条件分支选择，也作为同名 HDL 编译宏传给 VCS；同时将全局宏和
include 搜索目录集中放在 flat filelist 开头。

输出按以下分组依次渲染：

1. `-d/--define` 生成的 `+define+MACRO`；
2. 有效输入 filelist 中原有的 `+define+...`；
3. 有效输入 filelist 中的 `+incdir+...`；
4. 其余有效内容。

该变更有意用“全局编译配置优先”的新契约取代原先对所有 logical entry
保持全局原序的契约。

## 宏语义

`-d STUB_XXX` 同时产生两种效果：

- `ff` 将 `STUB_XXX` 加入 predefined macro 集合，用它选择 filelist 中
  `` `ifdef`/`ifndef`/`elsif`` 的有效分支；
- flat filelist 开头生成 `+define+STUB_XXX`，VCS 因而在编译 HDL 时定义
  同名无值宏。

命令行宏沿用现有集合语义：重复的 `-d` 参数去重、宏名区分大小写，最终
按宏名升序渲染，以保证同一请求产生确定输出。不支持的 `WIDTH=32` 形式
仍在展平前失败。

命令行生成的宏不与输入 filelist 原有宏去重。若两处都有
`STUB_XXX`，输出保留两个 `+define+STUB_XXX`。本机 VCS Y-2026.03
最小实验已验证：相同无值宏出现两次时，编译和仿真均成功，且没有重复宏
warning 或 error。VCS W-2024.09-SP1 的实验在解析前受许可证限制，未完成
该版本验证。

## 输入条目分类与排序

`ff` 先完成条件筛选、环境变量展开、嵌套 `-f/-F` 展开、路径校验和路径
绝对化，再对全部有效输出条目做全局稳定分组。嵌套 filelist 中选中的宏与
include 目录和顶层条目使用相同规则，因此也会提升到对应的全局分组。

- 原有 `+define+...` 条目以 `+define+` 前缀识别，内容原样保留。
- `+incdir+...` 继续按现有规则展开路径，并将多目录形式拆成每行一个绝对
  目录。
- 每个分组内部保持展开后的原顺序和重复次数。
- 普通源码、`-v/-y`、未知透传选项、独立注释和空行属于“其余内容”，
  继续保持彼此的展开后原序。

排序不得改变分支选择、路径基准、存在性校验、嵌套循环检测或输出原子
替换规则。

## 注释与生成注释

条目携带的尾部注释随条目移动。多目录 `+incdir+` 的尾部注释仍只输出
一次，并与拆分得到的整个 include 目录组一起移动。紧邻 include 目录的
symlink target annotation 与对应目录一起移动。

独占一行的普通用户注释和空行不根据邻近关系推断归属，属于“其余内容”。
这避免 `ff` 猜测一个独立注释究竟描述前一条还是后一条内容。

## 模块接口与实现边界

公共接口保持不变：

- CLI 仍使用 `ff INPUT [OPTIONS]` 和可重复、多值的 `-d/--define`；
- 引擎仍通过 `FlattenRequest.predefined_macros` 接收宏集合；
- `flatten_filelist()` 仍将 flat filelist 原子写入
  `FlattenResult.output_filelist`。

排序属于展平引擎的输出渲染实现。CLI 不自行拼接 `+define+`，这样 ff CLI
与未来在进程内调用同一引擎的 esim 得到完全相同的结果。

实现应在内部保留条目类别及其关联行，避免仅根据最终字符串二次排序而使
尾部注释或 symlink annotation 与条目分离。这是内部 seam，不扩大公共
接口。

## TDD 验证 seam

测试只通过两个既有公共 seam 观察行为：

1. `flatten_filelist(FlattenRequest(...))`：验证分支选择、命令行宏渲染、
   四组输出顺序、分组内稳定性、重复项和关联注释；
2. `ff.cli.main(argv)`：验证真实 `-d` 参数从 CLI 进入引擎，并在最终文件
   中同时产生分支选择和 HDL 宏定义。

按垂直切片执行红—绿循环：先实现命令行宏渲染，再实现原有宏提升，最后
实现 include 目录提升及其关联注释。每个切片先新增一个通过公共 seam
观察的失败测试，只加入使该测试通过的最小实现。

## 文档交付

实现完成后同步更新：

- `CONTEXT.md`：区分 predefined macro 的两项效果，并定义全局编译选项
  分组；
- `docs/requirements/ff.md`：更新宏、条目顺序和输出渲染的权威契约；
- `README.md`：在常用 `-d` 示例旁说明它也会生成 HDL 编译宏；
- `docs/user/ff-user-guide.html`：补充完整规则、输入—命令—结果示例和重复项
  行为；
- `docs/development/verification.md`：映射新增的引擎与 CLI 验收测试。

## 非目标

- 不新增宏值支持；
- 不对命令行宏和输入宏做跨来源去重；
- 不解析或合并原有 `+define+` 条目中的多个宏；
- 不推断独立注释与相邻条目的归属；
- 不改变 `-p` 或增加其他 CLI 选项；
- 不扩展到 VCS 之外的仿真器特有语法。
