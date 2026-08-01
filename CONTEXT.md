# Filelist Flattening

该上下文定义 Verilog/SystemVerilog 仿真工程中 filelist 预处理的统一语言。

## Language

**ff**:
读取一个顶层 filelist，根据预定义宏和嵌套引用生成一个语义等价的扁平 filelist 的预处理工具。范围仅包含 Verilog/SystemVerilog filelist，不包含 mixed-language 或 logical library 建模。
_Avoid_: Source Manifest Resolver, mixed-language resolver

**Top-level filelist**:
每次 `ff` 调用的唯一入口 filelist，其中可以继续引用子 filelist。其内容中的相对路径默认以该顶层 filelist 所在目录为基准。
_Avoid_: Root manifest, source manifest

**Flat filelist**:
`ff` 的权威输出：嵌套引用和条件内容已处理，且所有路径均为已通过存在性与类型校验的规范化绝对路径，可作为后续 Verilog/SystemVerilog 编译输入的 filelist。
_Avoid_: Source manifest, intermediate manifest

**Working-directory filelist reference (`-f`)**:
相对路径以 `ff` 启动时工作目录为基准的子 filelist 引用。
_Avoid_: Parent-relative include

**Filelist-relative reference (`-F`)**:
相对路径以当前 filelist 所在目录为基准的子 filelist 引用。
_Avoid_: Working-directory include

**Source chain**:
从顶层 filelist 到当前内容的完整嵌套引用路径，包含每层 filelist、行号和原始引用。所有解析错误均使用它定位内容的引入来源。
_Avoid_: Stack trace

**Symlink target annotation**:
flat filelist 中紧邻 symlink 路径条目的 `ff` 生成注释，记录该逻辑绝对路径跟随 symlink 后的物理路径。仿真器仍使用注释后保留 symlink 的逻辑路径。
_Avoid_: Original path, source expression

**Predefined macro**:
由 `ff` 调用者提供、用于判定 filelist 条件分支的无值 Verilog 标识符。它仅表达“已定义”或“未定义”，可以来自直接命令行调用，也可以由 esim 从 TC 配置中读取后传入。
_Avoid_: HDL compilation define

**Conditional directive**:
filelist 中由 `` `ifdef``, `` `ifndef``, `` `elsif``, `` `else`` 和 `` `endif`` 构成的条件结构。`ff` 根据预定义宏保留选中分支，但不执行宏文本替换；未选中分支只参与条件结构校验，其他内容不解析。
_Avoid_: Macro substitution

**Environment path reference**:
filelist 路径中以 `$NAME` 或 `${NAME}` 引用运行 `ff` 时的进程环境变量。引用会递归展开，直到不再包含环境变量，并在 flat filelist 中转换为绝对路径；任一引用不存在、值为空或形成循环时，展平失败。
_Avoid_: Shell expression

**Environment expansion chain**:
从 path entry 直接引用的环境变量到递归引用的各层变量所构成的链路。环境变量错误同时展示它与 source chain。
_Avoid_: Shell expansion

**Pass-through option**:
`ff` 不拥有其语义的仿真器 filelist 选项。`ff` 不因为无法识别该选项而拒绝它，而是将其原样保留在 flat filelist 中。
_Avoid_: Invalid option, ff option

**Path entry**:
`ff` 拥有其路径语义的 filelist 内容，包括普通非选项源码 token、`-f`/`-F`、`-v`/`-y` 和 `+incdir+`。普通源码 token 不通过文件扩展名判定。
_Avoid_: Known extension

**Include directory entry**:
flat filelist 中只包含一个规范化绝对目录的 `+incdir+` logical entry。输入行中以 `+` 连写的多个 include 目录按原始顺序拆成多个该条目。
_Avoid_: Combined include path

**Logical entry**:
filelist 中占据一行的一个完整内容单元，可以是源码路径、带参数的选项、条件指令、注释或空行。`ff` 不支持一行包含多个独立的逻辑条目。
_Avoid_: Arbitrary token stream

**TC configuration**:
由 esim 读取的测试用例描述，可以指定传给 `ff` 的顶层 filelist 和预定义宏。`ff` 本身不读取或解释 TC configuration。
_Avoid_: ff configuration
