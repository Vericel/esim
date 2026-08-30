# ff User Guide

`ff` 从一份顶层 Verilog/SystemVerilog filelist 出发，处理条件分支、嵌套
引用、环境变量和路径，生成可查阅、可调试、全部使用绝对路径的 flat
filelist。本文面向 Linux/WSL2 上的 ff CLI 用户。

## 第一章 入门 {#getting-started}

### 了解 ff {#overview}

`ff` 是 filelist 预处理工具。它把多层 filelist 中的有效条目展开，将自己
识别的路径规范化，并按全局编译配置与其余内容稳定分组。权威输出是一份
UTF-8 + LF 的纯文本 flat filelist。

| 能力 | 行为 |
|---|---|
| 条件 | 处理 `` `ifdef``、`` `ifndef``、`` `elsif``、`` `else``、`` `endif`` |
| 嵌套 | 递归展开 `-f`/`-F`，保留完整 source chain |
| 路径 | 展开环境变量，校验类型，输出规范化绝对逻辑路径 |
| 输出 | 稳定组织 define、incdir 和其余内容，保留有效重复项 |

> **范围边界：** ff 只处理 Verilog/SystemVerilog filelist，不替代仿真器，
> 不处理 mixed-language 或 logical library，也不生成 JSON、依赖文件或
> source map。

### 安装 {#install}

ff 与 esim 位于同一个 `esim` Python 包中，需要 CPython 3.11+，支持 Linux
和 WSL2。目标 EDA 机器推荐从离线 wheelhouse 安装：

```bash
python3 -m pip install \
  --no-index \
  --find-links ./wheelhouse \
  esim==0.2.0
```

wheelhouse 应包含：

- `esim` 0.2.0 wheel；
- `onelogg` 0.1.2 wheel；
- PyYAML 6.x wheel；
- Rich 及其运行时传递依赖。

安装后检查命令：

```bash
ff --help
esim --help
```

### 快速开始 {#quick-start}

假设 `/proj/tb/top.f` 内容为：

```text
../rtl/top.sv
+incdir+../rtl/include
```

执行：

```bash
cd /proj/tb/run
ff /proj/tb/top.f
```

默认在当前目录产生 `flattened.f`：

```text
+incdir+/proj/rtl/include
/proj/rtl/top.sv
```

可以显式指定输出和预定义宏：

```bash
ff /proj/tb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

相对输出以 ff 启动时的当前目录为基准。宏既用于选择条件分支，也会在
输出开头生成 `+define+MACRO`，供 VCS 编译 HDL 时使用。

### CLI 参数 {#cli}

命令格式固定为：

```text
ff INPUT [OPTIONS]
```

`INPUT` 必须是第一个参数。

| 参数 | 是否必需 | 行为 |
|---|---|---|
| `INPUT` | 是 | 顶层 filelist |
| `-o`, `--output` | 否 | 输出路径，默认 `./flattened.f` |
| `-d`, `--define` | 否 | 一次接收一个或多个无值宏，可重复使用 |
| `-l`, `--log` | 否 | 开启日志；可选路径，默认 `./ff.log` |
| `--debug` | 否 | 在终端输出 INFO、WARNING、ERROR 和 DEBUG trace |

#### 输出路径

- 显式相对输出以当前工作目录为基准。
- 输出父目录必须已经存在；ff 不创建父目录。
- 成功时即使内容不变也替换原输出。

#### 预定义宏

以下三种写法等价：

```bash
ff top.f -d FPGA USE_DDR
ff top.f -d FPGA -d USE_DDR
ff top.f --define FPGA --define USE_DDR
```

- 所有值合并为集合，重复项去重，名称区分大小写。
- 名称匹配 `[A-Za-z_][A-Za-z0-9_$]*`。
- 命令行宏按名称排序生成 `+define+`，保证输出确定。
- 不支持 `WIDTH=32`，也不使用逗号分隔。
- 输入 filelist 中原有的 `+define+` 不改变 ff 的条件宏集合。
- 命令行宏不与 filelist 宏去重，同名定义可以保留多次。

#### 日志组合

| 命令 | 终端 | 日志文件 |
|---|---|---|
| `ff top.f` | WARNING / ERROR | 不生成 |
| `ff top.f -l` | WARNING / ERROR | `./ff.log` |
| `ff top.f -l ./my.log` | WARNING / ERROR | `./my.log` |
| `ff top.f --debug` | INFO / WARNING / ERROR / DEBUG | 不生成 |
| `ff top.f --debug -l` | 完整 DEBUG 级别 | `./ff.log` |

#### 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | filelist 处理失败 |
| `2` | CLI 参数用法错误 |
| `3` | ff 内部程序错误 |

## 第二章 Filelist 解析 {#filelist-processing}

### 条件指令 {#conditions}

支持任意层级嵌套：

```text
`ifdef MACRO
`ifndef MACRO
`elsif MACRO
`else
`endif
```

输入：

```text
`ifdef FPGA
../rtl/fpga_top.sv
`elsif ASIC
../rtl/asic_top.sv
`else
../rtl/model_top.sv
`endif
```

命令：

```bash
ff /proj/tb/top.f -d FPGA
```

结果只保留选中的路径：

```text
+define+FPGA
/proj/rtl/fpga_top.sv
```

规则：

- 条件只筛选内容，不执行宏文本替换。
- 指令必须是行内第一个非空白内容，可有尾部注释，但不得有多余 token。
- 指令和宏名称区分大小写；未知反引号指令报错，不透传。
- 无匹配的 `else`/`elsif`/`endif`、重复 `else`、`else` 后 `elsif`、
  参数数量错误以及 EOF 未闭合都会失败。
- 未选中分支仍校验条件结构，但不展开环境变量、不读取子 filelist，
  也不校验其中的路径或普通内容。
- 条件指令及其尾部注释不写入结果。

### 嵌套 filelist 与路径基准 {#nested-filelists}

```text
/proj/tb/top.f
└─ -F blocks/core.f
   └─ ../../rtl/core.sv
```

命令：

```bash
ff /proj/tb/top.f
```

结果：

```text
/proj/rtl/core.sv
```

路径基准：

| 形式 | 相对路径基准 |
|---|---|
| 顶层 filelist 的普通内容 | 顶层 filelist 的逻辑所在目录 |
| `-f child.f` | ff 启动时的工作目录 |
| `-F child.f` | 声明引用的当前 filelist 的逻辑所在目录 |

所有 `-f/-F` 都被递归展开，不写入输出。循环按当前引用栈检测并显示完整
source chain；同一 filelist 在不同位置重复引用不是循环，仍按次展开。重复
源码、define、incdir 或透传选项也不自动去重。

### 环境变量 {#environment}

支持 `$NAME` 和 `${NAME}`，变量名匹配 `[A-Za-z_][A-Za-z0-9_]*`。

输入：

```text
$RTL_HOME/top.sv
+incdir+${RTL_HOME}/include
```

命令：

```bash
export PROJECT_ROOT=/proj
export RTL_HOME='${PROJECT_ROOT}/rtl'
ff /proj/tb/top.f
```

结果：

```text
+incdir+/proj/rtl/include
/proj/rtl/top.sv
```

- 普通源码、`-f/-F`、`-v/-y` 和 `+incdir+` 都支持展开。
- 变量值可以继续引用变量，ff 会递归展开。
- 任一层变量缺失、值为空或形成循环都会失败，并同时显示 source chain
  与 environment expansion chain。
- 不支持 `${NAME:-default}`、`$(command)`、反引号命令、`~` 或 `~user`。
- 展开后仍是相对路径时，继续使用该 logical entry 原有的路径基准。

### 注释、路径与透传选项 {#comments-paths}

#### 注释

- 支持 `//` 和不可嵌套的 `/* ... */`。
- 尾部注释前必须有空白；路径 token 内的 `//` 不是注释。
- 块注释可以跨行，但必须在同一 filelist 内闭合。
- 有效分支中的注释和空行保留，无效分支中的注释删除。
- path entry 尾注释放在规范化路径之后。
- `-f/-F` 尾注释提升到展开内容之前。
- 多目录 `+incdir+` 尾注释提升到拆分后目录组之前。

#### ff 识别的路径条目

```text
source/path
-f child.f
-F child.f
-v library.v
-y library_dir
+incdir+dir1+dir2
```

- 普通非选项 token 都是源码路径，不使用扩展名白名单。
- `-f/-F/-v/-y` 只支持选项与一个分离参数。
- `+incdir+` 至少包含一个非空目录；多目录输出为多行并保留顺序和重复。
- 其他仿真器选项原样透传；ff 不猜测未知选项内部的路径语义。

#### 明确不支持

- 一个物理行中放多个 logical entry；
- 反斜杠续行；
- 含空格或制表符的路径，以及引号包裹的空白路径；
- `*`、`?`、`[...]` glob；
- `-fchild.f`、`-f=child.f` 等紧凑形式；
- Windows 盘符和 UNC 路径；`/mnt/c/...` 仍是合法 POSIX 路径。

## 第三章 输出与诊断 {#output-and-diagnostics}

### 路径规范化与输出安全 {#output-safety}

所有 ff 识别的路径都输出为消除 `.`、`..` 和重复分隔符的绝对路径。

#### symlink

- 输出保留 symlink 逻辑路径，不替换为物理路径。
- 路径经过 symlink 时，在条目前生成 target annotation，记录最终物理路径。
- 存在性、循环和输入/输出冲突使用解析 symlink 后的真实身份判断。
- filelist-relative 基准始终使用逻辑 filelist 目录。
- 损坏 symlink 按路径不存在处理。

#### 类型和可读性

- 顶层/子 filelist、普通源码和 `-v` 必须是可读普通文件。
- `+incdir+` 和 `-y` 必须是存在目录。
- 未选中分支中的路径不校验。

#### 稳定输出分组

输出依次为：

1. CLI 预定义宏生成的 `+define+`；
2. 有效输入 filelist 原有的 `+define+`；
3. 规范化后的 `+incdir+`；
4. 其余有效内容。

CLI 宏按名称排序；其余各组保留递归展开后的原顺序和重复项。

#### 编码、原子替换和权限

- 输入必须是 UTF-8，允许 UTF-8 BOM，接受 LF 或 CRLF。
- 输出固定为无 BOM 的 UTF-8 + LF，并以一个换行结束。
- 全部处理成功后才在目标目录原子替换输出；失败不产生半成品。
- 输出不能与顶层或任一子 filelist 指向同一真实文件。
- 输出目标是 symlink 时，替换 symlink 节点，不修改 target。
- 替换普通文件时保留读写权限并清除可执行位。
- 新文件权限为 `0666 & ~umask`。
- ff 不提供输出进程锁；同路径并发写入时，最后完成的成功调用获胜。
- 条件筛选后没有源码路径仍可成功。

### 日志与错误排查 {#logging-errors}

需要保留失败现场时使用 `-l`；需要观察递归读取、条件选择和路径解析时
增加 `--debug`：

```bash
ff /proj/tb/top.f --debug -l /proj/tb/run/ff.log
```

典型 trace：

```text
DEBUG reading filelist: /proj/tb/top.f
DEBUG reading filelist: /proj/tb/blocks/core.f
DEBUG resolved source: /proj/tb/blocks/core.f:1 -> /proj/rtl/core.sv
INFO  flattened output: /proj/tb/run/flattened.f
```

日志每次覆盖、不追加，并通过同目录临时文件发布；受控失败时也会保存。
日志不能与输出或任何输入 filelist 指向同一真实文件。日志目标为 symlink
时替换节点，不修改 target。

解析、条件、环境变量和路径错误都展示完整 source chain，并尽量包含原始
条目、解析结果、行号和修复建议：

```text
FATAL source file does not exist: /proj/rtl/missing.sv
source chain:
  /proj/tb/top.f:8
  /proj/tb/blocks/core.f:12
suggestion: check the path or define the macro that selects another branch
```

排查顺序：

1. 先根据退出码区分处理失败、CLI 用法和内部错误。
2. 沿 source chain 从顶层 filelist 定位到实际声明行。
3. 环境变量失败时继续检查 environment expansion chain。
4. 使用 `--debug -l` 重跑并保留完整解析 trace。
5. 检查输出/日志是否与任一输入 filelist 指向相同真实文件。

## 第四章 参考 {#reference-chapter}

### 规则速查 {#reference}

| 类别 | 支持 | 主要约束 |
|---|---|---|
| 条件 | `ifdef`、`ifndef`、`elsif`、`else`、`endif` | 只筛选，不替换宏文本 |
| 嵌套 | `-f`、`-F` | 基准不同，全部递归展开 |
| 环境 | `$NAME`、`${NAME}` | 递归展开；缺失、空值、循环均失败 |
| 路径 | source、`-v`、`-y`、`+incdir+` | 校验并绝对化 |
| 注释 | `//`、`/* ... */` | 块注释不嵌套、不跨 filelist |
| 其他选项 | 原样透传 | 不猜测内部路径语义 |

一句话记忆路径基准：顶层普通内容和 `-F` 看当前 filelist 的逻辑目录，
`-f` 看 ff 启动时工作目录。

esim 如何调用共享展平引擎见 [esim User Guide](esim-user-guide.md)。
