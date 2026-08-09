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
`botticelle-onelog`、Rich、PyYAML 及其依赖；
onelog 0.1.0 对应 [v0.1.0](https://github.com/BottiCelle/onelog/releases/tag/v0.1.0)。

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

不指定 `-o` 时，默认在当前目录生成 `flattened.f`。
每个 `-d/--define` 宏既选择 filelist 条件分支，也会在输出开头生成同名
`+define+MACRO`，供 VCS 编译 HDL 时使用。

## 详细文档

- [ff User Guide](docs/user/ff-user-guide.html)
- [esim User Guide](docs/user/esim-user-guide.md)
- [VS Code 与 Vim/gVim 语法高亮](editors/README.md)
- [ff 需求与行为契约](docs/requirements/ff.md)
- [esim TC/Rules 与仿真流程需求](docs/requirements/esim.md)
- [开发指南](docs/development/development-guide.md)
- [变更记录](CHANGELOG.md)
