# esim

`esim` 是 EDA 仿真项目；`ff` 是其中可独立执行的
Verilog/SystemVerilog filelist 展平工具。它处理条件分支、
嵌套 filelist、环境变量和路径，输出全部使用绝对路径的
flat filelist。

## 安装

```bash
python3 -m pip install --no-index --find-links ./wheelhouse esim==0.2.0
```

需要 CPython 3.11+，支持 Linux 和 WSL2。wheelhouse 需包含 esim、
`onelogg`、Rich 及其依赖；当前固定的 onelogg 0.1.1 对应
[PyPI 发布](https://pypi.org/project/onelogg/0.1.1/)和
[v0.1.1](https://github.com/BottiCelle/onelog/releases/tag/v0.1.1)。
分发名是 `onelogg`，Python 导入名仍是 `onelog`。请使用干净环境安装；不要与
PyPI 上无关的 `onelog` 分发或旧 `botticelle-onelog` 分发混装，因为它们可能
共同写入 `onelog` 导入路径。

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
- [开发指南](docs/development/development-guide.md)
- [变更记录](CHANGELOG.md)
