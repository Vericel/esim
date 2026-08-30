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
`onelogg`、Rich、PyYAML 及其依赖；
onelogg 0.1.2 对应 [v0.1.2](https://github.com/BottiCelle/onelog/releases/tag/v0.1.2)。

## 基础用法

```bash
export DV_HOME=/proj/aaa/dv
export DV_TMP=/proj/aaa/dv_tmp

esim xxx.yyy:func.smoke
esim xxx.yyy:func.smoke -f coverage -r "+ntb_random_seed=17"
esim xxx.yyy:func.smoke -a run -r "+UVM_VERBOSITY=UVM_HIGH"
esim check /proj/aaa/dv_tmp/xxx.yyy/default/func.smoke

ff /aaa/bbb/testbench.f
ff /aaa/bbb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

`esim` 从 TC 和 Rules YAML 合成 Effective TC，在
`$DV_TMP/<dtb>/<rules>/<test>/` 内执行 ff→build→run，并保存
`tc.yaml`、`rules.yaml`、`result.yaml`、完整日志及合并后的 waiver。
当 `-b/-e/-r` 的值以 `-` 开头时，可直接作为后一个已引用的
shell 参数传入，也可使用 `-b='-full64 -debug_access+all'` 形式。

需要编写复杂 TC 或查看 two-step TC 全部受支持字段时，可参考
[`complete.tc`](tests/fixtures/esim-demo-project/dv/xxx/yyy/tests/features/complete.tc)。
`complete.yaml` 是指向该文件的兼容符号链接。

不指定 `-o` 时，默认在当前目录生成 `flattened.f`。
每个 `-d/--define` 宏既选择 filelist 条件分支，也会在输出开头生成同名
`+define+MACRO`，供 VCS 编译 HDL 时使用。

## 详细文档

- ff User Guide：[Markdown](docs/user/ff-user-guide.md) ·
  [离线 HTML](docs/user/ff-user-guide.html)
- esim User Guide：[Markdown](docs/user/esim-user-guide.md) ·
  [离线 HTML](docs/user/esim-user-guide.html)
- [VS Code 与 Vim/gVim 语法高亮](editors/README.md)
- [变更记录](CHANGELOG.md)
