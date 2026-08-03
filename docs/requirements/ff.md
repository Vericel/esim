# ff 需求架构

状态：ff 已实现，作为需求和验收的权威契约
最后更新：2026-08-03

## 1. 目标与边界

`ff` 是 Verilog/SystemVerilog filelist 预处理工具。它读取一个顶层 filelist，处理条件分支、嵌套 filelist、环境变量和路径，生成一个语义等价的 flat filelist。

权威持久化产物是纯文本 flat filelist，不是 source manifest。第一版不考虑 mixed-language 和 logical library，不生成 JSON、依赖文件或 source map sidecar。

`ff` 不读取 TC YAML。`esim` 拥有 TC configuration，负责解析并把 filelist 和预定义宏传给展平引擎。TC YAML 的字段命名、合并和优先级留待 esim 讨论。

## 2. 软件架构

```text
                    ┌─ ff CLI
flattening engine ─┤
                    └─ esim
```

- 展平引擎不理解 CLI 或 YAML，接收结构化输入并返回结构化结果/错误。
- ff CLI 是引擎的薄适配层。
- esim 在进程内直接调用同一引擎，不启动 ff 子进程。
- 实现基线为 CPython 3.11+，支持 Linux 和 WSL2。
- CLI 使用正式打包、版本化的 `BottiCelle/onelog` 及其 Rich 依赖；它们随 ff/esim 发行，目标机无需联网安装。
- onelog 在 ff 和 esim 中均关闭 summary。
- 展平引擎不配置 root logger，不调用 `log.fatal()`。

## 3. CLI 契约

```text
ff INPUT [OPTIONS]
```

`INPUT` 必须是第一个参数。主要用法：

```bash
ff /aaa/bbb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

### 3.1 输出

- `-o/--output` 可选。
- 未指定时默认为当前工作目录的 `./flattened.f`。
- 显式相对输出路径也以当前工作目录为基准。
- 输出父目录必须已存在，`ff` 不创建目录。

### 3.2 预定义宏

```bash
ff top.f -d FPGA USE_DDR
ff top.f -d FPGA -d USE_DDR
ff top.f --define FPGA --define USE_DDR
```

- `-d/--define` 可重复，每次至少一个宏名，所有值合并为集合。
- 重复宏去重，宏名区分大小写。
- 宏是无值的“已定义/未定义”标记：既用于选择 filelist 条件分支，也在 flat filelist 开头生成为同名 `+define+MACRO`，供 VCS 编译 HDL 时使用。
- 命令行宏按宏名升序生成，保证集合输入得到确定输出。
- 宏名匹配 `[A-Za-z_][A-Za-z0-9_$]*`。
- 不支持 `WIDTH=32`。
- 不以逗号分割多个宏。

### 3.3 日志

```bash
ff top.f -l
ff top.f -l ./my.log
ff top.f --debug
ff top.f --debug -l ./my.log
```

- `-l/--log` 使用可选路径；不带路径时为 `./ff.log`。
- `--debug` 未指定日志时只把 INFO、WARNING、ERROR 和 DEBUG/trace 输出到终端。
- `--debug -l [PATH]` 把同样的完整内容同时输出到终端和日志。
- 无 `--debug` 时，终端及已启用的日志只记录 WARNING/ERROR。
- trace 暂使用 `log.debug()`，不新增 TRACE 等级。
- 每次 invocation 覆盖旧日志，不追加。
- 日志先写同目录临时文件，在成功或可控失败时均发布到目标路径。
- 日志不得与输出或任一输入 filelist 是同一文件。
- 日志目标是 symlink 时替换 symlink 节点，不修改 symlink target。

### 3.4 退出码

```text
0  成功
1  filelist 处理失败
2  CLI 参数用法错误
3  ff 内部程序错误
```

## 4. Filelist 语法

### 4.1 Logical entry

- 一个物理行只能包含一个 logical entry。
- 普通源码行只能包含一个路径。
- 不支持反斜杠续行。
- 不支持引号包裹的含空白路径；所有路径均不得包含空格或制表符。
- 不支持 `*`、`?`、`[...]` glob，遇到则报错。
- 路径语义只支持 Linux/POSIX，不自动转换 Windows 盘符或 UNC 路径。`/mnt/c/...` 是合法 POSIX 路径。

### 4.2 条件指令

支持任意层级嵌套：

```text
`ifdef MACRO
`ifndef MACRO
`elsif MACRO
`else
`endif
```

- 只做条件筛选，不做宏文本替换。
- 输入 filelist 原有的 `+define+...` 是仿真器选项，不改变 `ff` 的预定义宏集合，因此不会自行选择条件分支；有效条目原样保留并提升到输出的 filelist define 分组。
- 指令必须是行内第一个非空白内容，允许尾部注释，去除注释后不得有多余 token。
- 指令名和宏名区分大小写。
- 未知反引号指令一律报错，不透传。
- 缺少/多余参数、无匹配 `else`/`elsif`/`endif`、重复 `else`、`else` 后 `elsif` 和 EOF 未闭合均为错误。
- 未选中分支仍校验条件嵌套，但不展开环境变量、不读取子 filelist、不校验其他内容。
- 条件指令自身及其尾部注释不写入输出。

### 4.3 注释

- 支持 `//` 和不可嵌套的 `/* ... */`。
- 尾部注释前必须有至少一个空白字符，路径 token 内的 `//` 不是注释。
- 块注释可跨行，但必须在同一 filelist 内闭合，不跨 `-f/-F` 边界。
- 有效分支中的原始注释和空行保留；无效分支中的注释删除。
- 普通 path entry 的尾部注释保留在规范化路径后。
- `-f/-F` 的尾部注释提升为展开内容前的独立注释。
- 多目录 `+incdir+` 的尾部注释提升为拆分组之前的独立注释，并与该 include 目录组一起移动到输出前部。
- 除 symlink target annotation 外，`ff` 不主动增加其他注释。

### 4.4 路径条目

`ff` 识别：

```text
source/path
-f child.f
-F child.f
-v library.v
-y library_dir
+incdir+dir1+dir2
```

- 普通非选项 token 就是源码路径，不使用扩展名白名单。
- `-f/-F/-v/-y` 只接受“选项 + 单个分离参数”，不接受紧凑或等号形式。
- `+incdir+` 至少一个目录，空分段是错误。
- 多目录 `+incdir+` 在输出中拆为多行，每行一个绝对目录，保留顺序和重复项。
- 其他仿真器选项原样透传；未知不等于非法。
- `ff` 只绝对化自己识别的路径，不猜测透传选项中可能隐含的路径。

## 5. 嵌套 filelist 与路径基准

- 顶层 filelist 内容默认采用 filelist-relative（`-F` 式）基准。
- `-f` 子 filelist 及其相对内容以 `ff` 启动时工作目录为基准。
- `-F` 子 filelist 及其相对内容以当前 filelist 的逻辑所在目录为基准。
- 递归展开所有 `-f/-F`，输出中不再包含它们。
- 使用当前引用栈检测循环；同一 filelist 在不同分支或位置重复引用不是循环，仍按次展开。
- 重复源码或选项不自动去重；在各自输出分组内保留展开后的原顺序和次数，DEBUG 中可提示重复来源。

## 6. 环境变量

- 支持 `$NAME` 和 `${NAME}`，变量名匹配 `[A-Za-z_][A-Za-z0-9_]*`。
- 在普通源码、`-f/-F`、`-v/-y` 和 `+incdir+` 的路径中展开。
- 支持同一路径多变量，并递归展开变量值中的变量，直到完全展开。
- 任一层缺失、空值或循环引用都是错误，报错同时显示 source chain 和 environment expansion chain。
- 不支持 `${NAME:-default}`、`$(command)`、反引号命令、`~` 或 `~user`。
- 展开后仍为相对路径时，沿用当前 logical entry 原本的路径基准。

## 7. 路径规范化与校验

- flat filelist 中所有已识别路径均输出为消除 `.`、`..` 和重复分隔符的绝对路径。
- 输出保留 symlink 逻辑路径，不替换为物理路径。
- filelist-relative 计算也使用逻辑 filelist 目录，不因读取时跟随 symlink 而切换基准。
- 内部的存在性、循环、输入/输出冲突检测使用 symlink 解析后的真实文件身份。
- 经过 symlink 的路径在条目前增加 symlink target annotation，注释记录最终物理路径，仿真器仍消费逻辑路径。
- 顶层/子 filelist、普通源码和 `-v` 必须是可读取普通文件。
- `+incdir+` 和 `-y` 必须是存在目录。
- 损坏 symlink 按路径不存在报错。
- 未选中条件分支中的路径不校验。

## 8. 输出渲染与安全

- flat filelist 按四组稳定输出：命令行预定义宏生成的 `+define+`、有效输入 filelist 原有的 `+define+`、规范化后的 `+incdir+`、其余有效内容。
- 命令行宏按名字升序；其他三组按嵌套展开后的原顺序输出，并保留重复项。
- 命令行生成的宏不与输入 filelist 原有宏去重，同名 `+define+` 可以出现多次。
- 嵌套 filelist 中的有效 `+define+` 和 `+incdir+` 同样进入全局对应分组。
- `+incdir+` 的尾部注释和 symlink target annotation 随对应 include 目录组移动；独立注释和空行属于“其余有效内容”，不推断与相邻条目的归属。
- 输入必须是 UTF-8，允许 UTF-8 BOM，接受 LF/CRLF。
- 输出固定为无 BOM 的 UTF-8 + LF，文件末尾保留一个换行。
- 展平、校验和渲染全部成功后才在同目录原子替换输出。
- 任何失败均不产生半成品，已有输出保持不变。
- 成功时始终替换原输出，即使内容完全相同也不保留旧 inode/mtime。
- 输出不得与顶层或任一子 filelist 是同一真实文件。
- 输出目标是 symlink 时，替换 symlink 节点为普通文件，不修改 symlink target。
- 替换已有普通文件时保留其读写权限但清除可执行位；新文件使用 `0666 & ~umask`。
- `ff` 不实现输出进程锁。同路径并发写定义为最后完成的成功调用获胜；esim 必须通过独立 run directory/输出路径避免冲突。
- 筛选后没有源码路径仍可成功；DEBUG 可提示零源码条目。

## 9. 错误与失败传播

- 所有解析、条件、环境变量和路径错误都展示完整 source chain。
- 错误包含原始条目、解析结果、行号和可行的修复建议。
- 展平引擎通过结构化 `FlattenError` 报告可预期失败，不退出宿主进程。
- ff CLI 在最外层捕获 `FlattenError`，完成临时文件清理后可调用 `log.fatal()` 以退出码 1 结束。
- esim 捕获同一错误后把当前 invocation 标记为 prepare/ff 失败，跳过 cache/build/run/check，但仍执行 `on_failure` 和恰好一次 `finalize`。
- regression 中一个 case 的 ff 失败不得直接终止其他独立 case。

## 10. 待后续讨论

- TC YAML 中 ff 字段的最终命名（包括 `macro`/`marco` 拼写）、默认值和配置合并优先级。
- ff 内存结构化结果与 esim 缓存指纹的详细契约。
- esim 的 TC YAML 解析、调用链、缓存与调度实现。
