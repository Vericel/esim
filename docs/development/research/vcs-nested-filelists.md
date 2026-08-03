# VCS 嵌套 filelist 支持调查

调查日期：2026-07-31  
重点核实版本：Synopsys VCS W-2024.09-SP1_Full64  
对照版本：VCS X-2005.06、Y-2026.03

## 结论

VCS W-2024.09-SP1 本身支持嵌套 filelist，但 `-f` 与 `-F` 的路径语义不同：

- `-f <filelist>` 可以出现在 `-f` 载入的 filelist 中，指向另一份 filelist。
- `-F <filelist>` 也可以出现在 `-F` 载入的 filelist 中；该类 filelist 内还明确允许 `-f`。
- `-f` 不会按 filelist 所在目录重定位相对路径；相对路径仍以 VCS 进程的当前工作目录为基准。
- `-F` 会把 filelist 的目录前缀加到其中的相对路径内容上，因此适合位置可迁移的分层 filelist。
- W-2024.09-SP1 的手册说明 `-f`、`-F` 均不支持 UUM（Unified Use Model）flow；UUM 应使用 `-file`。

因此，`esim` 只暴露一个顶层 `filelist` 字段、再由 `ff` 脚本展平嵌套 filelist，是合理且更稳健的接口设计。即使 W-2024.09-SP1 能直接处理嵌套，预先展平仍能统一 VCS/Xcelium 行为、消除工作目录差异，并降低跨版本风险。历史版本的 `-F` 嵌套能力确实不同，不能把 W-2024.09-SP1 的行为无条件外推到所有版本。

## 官方依据

第一方来源为本机 VCS 安装自带的官方文档：

- 文档：*VCS Command Reference Guide*
- 版本：W-2024.09-SP1
- 章节：Compile Options → Compiler Options → Compilation/Elaboration Options → `-f <filename>`、`-F <filename>`
- HTML：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/html/vcs_cmd_ref/compiler_options/compilation_elaboration_options_compiler.html`
- PDF：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/UserGuide/pdf/vcs_cmd_ref.pdf`
- 官方在线文档入口：[Synopsys SolvNetPlus](https://solvnetplus.synopsys.com/)（通常需要客户账号和相应产品权限）

本机安装还包含官方简要帮助：

- W-2024.09-SP1：
  `/opt/synopsys/vcs/W-2024.09-SP1/doc/help_vcs.txt`，约第 277–284 行
- Y-2026.03：
  `/opt/synopsys/vcs/Y-2026.03/doc/help_vcs.txt`，约第 277–284 行

两版简要帮助均确认命令行 `-f`、`-F` 仍存在，并将 `-F` 描述为与 `-f` 相同但允许为 filelist 指定路径、其中源文件不必使用绝对路径。简要帮助没有说明嵌套组合，W-2024.09-SP1 的嵌套结论来自同版本更详细的 Command Reference Guide。

手册在 `-f` 章节明确说明：

1. `-f` 指定的文件可包含源文件及编译期选项；
2. 可以在该文件内再次使用 `-f` 指向另一文件；
3. 以 `-` 开头的允许项列表包含 `-f`、`-y`、`-l`、`-u`、`-v`、`-sverilog`；
4. `-f` 不支持 UUM flow。

手册在 `-F` 章节明确说明：

1. `-F` 与 `-f` 类似，但会将 filelist 路径作为其中内容的搜索路径；
2. filelist 路径会作为前缀加到 filelist 内容；
3. 可以在该文件内再次使用 `-F` 指向另一文件；
4. 以 `-` 开头的允许项列表同时包含 `-f` 与 `-F`；
5. `-F` 不支持 UUM flow。

手册给出的 `-F ../<filelist>` 示例说明：若 filelist 内有 `a.v`、`b.v`，VCS 会查找 `../a.v`、`../b.v`。

`-file <filename>` 章节则说明它接受 VCS compilation/elaboration options，用于突破 `-f` 对以 `-` 开头选项的限制，并支持 UUM flow。

## `-f` 与 `-F` 的路径差异

假设目录如下：

```text
project/
  rtl/
    top.sv
    lists/
      top.f
      sub/
        block.f
        block.sv
```

### 使用 `-f`

```text
vcs -f project/rtl/lists/top.f
```

若 `top.f` 写：

```text
-f sub/block.f
```

`sub/block.f` 是相对于 **VCS 启动时的当前工作目录** 解析，而不是自动相对于 `top.f` 所在的 `project/rtl/lists/`。

本机 W-2024.09-SP1 最小验证从 `/tmp` 启动 VCS，命令行以绝对路径传入外层 `-f`，外层文件含 `-f sub/inner-lower-f.f`。VCS 报告：

```text
Cannot open file
Unable to open 'sub/inner-lower-f.f'
```

这与手册用 `-F` 专门提供路径前缀能力的说明一致。

### 使用 `-F`

```text
vcs -F project/rtl/lists/top.f
```

若 `top.f` 写：

```text
-F sub/block.f
```

外层 `-F` 会先把 `project/rtl/lists/` 应用于外层内容，定位到 `sub/block.f`；内层 `-F` 再以其目录作为内层内容的前缀。按手册规则，`block.f` 中的 `block.sv` 因而定位到：

```text
project/rtl/lists/sub/block.sv
```

本机最小验证中，这组嵌套 `-F` 路径均通过 filelist 打开阶段，VCS 随后才停在 license acquisition 阶段，未出现 file-open 错误。该验证只用于印证手册的路径规则，没有完成 HDL 编译。

## 支持矩阵

以下矩阵按 W-2024.09-SP1 手册中“filelist 内允许的 `-` 选项”整理：

| 外层载入方式 | filelist 内写 `-f child.f` | filelist 内写 `-F child.f` |
|---|---:|---:|
| `vcs -f outer.f` | 明确支持 | 未列入该章节的允许项；不要依赖 |
| `vcs -F outer.f` | 明确支持 | 明确支持 |

这里的“未列入”不等于断言所有版本都会立即报错，而是表示 W-2024.09-SP1 官方文档没有把这种组合纳入 `-f` filelist 的受支持语法。为了可移植性，`ff` 不应依赖该组合。

## 对 `ff` 展平器的建议

展平器至少需要保留以下语义：

1. 维护“VCS 启动工作目录”和“当前 filelist 目录”两个不同基准：
   - `-f` 的相对路径按启动工作目录解析；
   - `-F` 的相对内容按当前 filelist 目录解析。
2. 递归处理 `-f`/`-F`，并检测循环引用。
3. 将最终源文件路径、子 filelist 路径、`+incdir+...` 路径规范化为绝对路径或相对于展平输出位置的稳定路径。
4. 保留顺序。宏、库目录、库文件和源文件的先后顺序可能影响编译结果。
5. 正确处理 Verilog 注释。手册允许 `//` 和 `/* ... */`，同时特别说明路径中间的 `//` 不应被当成注释。
6. 不要把任意以 `-` 开头的 token 都当成 `-f` filelist 的合法内容；W-2024.09-SP1 对允许项有限制。
7. 输出依赖清单和诊断链，例如：

```text
top.f:12 -> -F sub/block.f:8 -> rtl/block.sv
```

这会比仅生成一个扁平文件更利于定位缺失文件和错误的相对路径。

## 版本风险

本结论经官方 W-2024.09-SP1 文档和该版本本机软件输出核实，不能自动外推到所有旧版或未来版本。

历史官方文档给出了一个明确反例：

- 文档：*VCS/VCSi User Guide*
- 版本：X-2005.06，August 2005
- 章节：Chapter 3, “Compiling Your Design” → “File Containing Source Filenames and Options”
- 页码：3-56–3-57
- `-f` 段明确允许在 filelist 内再次写 `-f`。
- 紧随其后的 `-F` 段说明以该文件路径作为 Verilog 源文件路径，但同时明确注明当时不支持 nested files。

这说明 `-F` 嵌套能力曾随版本变化。Y-2026.03 的当前简要帮助仍确认 `-f`/`-F` 及其基本路径差异，但没有足够文字单独确认嵌套组合；若未来切换到 Y-2026.03，应以该版本完整 Command Reference、release notes 或最小兼容测试重新确认。

尤其需要注意：

- `-f`/`-F` 的 UUM 限制；
- filelist 中允许的以 `-` 开头选项集合；
- 混用外层 `-f` 与内层 `-F` 的支持边界；
- 其他仿真器的相对路径和注释规则可能不同。

`esim` 可以在工具适配层按实际 VCS 版本选择调用方式，但公共 YAML schema 不应暴露这些 VCS 特有差异。公共输入保留单一顶层 filelist 即可。

## 本机版本出处

本机第一方命令输出：

```text
vcs script version : W-2024.09
Compiler version = VCS W-2024.09-SP1_Full64
VCS Build Date = Dec 03 2024 20:20:03
```

命令：

```text
vcs -full64 -ID
```
