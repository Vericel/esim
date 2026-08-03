# ff

`ff` 是 Verilog/SystemVerilog filelist 展平工具。它处理条件分支、
嵌套 filelist、环境变量和路径，输出全部使用绝对路径的
flat filelist。

## 安装

```bash
python3 -m pip install --no-index --find-links ./wheelhouse esim==0.2.0
```

需要 CPython 3.11+，支持 Linux 和 WSL2。wheelhouse 需包含 ff、
`botticelle-onelog`、Rich 及其依赖；
onelog 0.1.0 对应 [v0.1.0](https://github.com/BottiCelle/onelog/releases/tag/v0.1.0)。

## 基础用法

```bash
ff /aaa/bbb/testbench.f
ff /aaa/bbb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

不指定 `-o` 时，默认在当前目录生成 `flattened.f`。
每个 `-d/--define` 宏既选择 filelist 条件分支，也会在输出开头生成同名
`+define+MACRO`，供 VCS 编译 HDL 时使用。

## 详细文档

- [ff User Guide](docs/user/ff-user-guide.html)
- [ff 需求与行为契约](docs/requirements/ff.md)
