# ff

`ff` 是 Verilog/SystemVerilog filelist 展平工具。它处理条件分支、
嵌套 filelist、环境变量和路径，输出全部使用绝对路径的
flat filelist。

## 安装

```bash
python3 -m pip install --no-index --find-links ./wheelhouse esim==0.1.0
```

需要 Python 3.9+。wheelhouse 需包含 ff、`botticelle-onelog`、Rich 及其依赖。

## 基础用法

```bash
ff /aaa/bbb/testbench.f
ff /aaa/bbb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

不指定 `-o` 时，默认在当前目录生成 `flattened.f`。

## 详细文档

- [ff User Guide](docs/ff-user-guide.html)
- [ff 需求与行为契约](docs/ff-requirements.md)
