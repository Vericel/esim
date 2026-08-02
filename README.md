# ff

`ff` 是 Verilog/SystemVerilog filelist 展平工具。它处理条件分支、递归
`-f/-F`、环境变量和已识别路径，生成一份只含绝对路径的 flat
filelist。

## 安装

```bash
python3 -m pip install .
```

项目支持 Python 3.9+，运行依赖 Rich。`BottiCelle/onelog` 上游当前没有
Python 打包元数据，因此以固定 commit
`dd41f9ac9772d9aa9d69a8a40c4ebe9420db6163` 随 `ff` wheel 发行。

## CLI

`INPUT` 必须是第一个参数：

```bash
ff /aaa/bbb/testbench.f -o testbench.f -d MACRO_1 MACRO_2
```

- 不指定 `-o/--output` 时写当前目录的 `flattened.f`。
- `-d/--define` 可重复，每次可跟一个或多个无值宏名。
- `-l/--log` 不带路径时写 `./ff.log`，也可指定路径。
- `--debug` 打印递归读取和路径解析 trace；与 `-l` 同用时也写日志。
- onelog summary 始终关闭。

退出码：`0` 成功，`1` filelist/路径可预期失败，`2` CLI 用法错误，
`3` 内部程序错误。

## Python 引擎

`esim` 应在进程内复用引擎，不启动 `ff` 子进程：

```python
from pathlib import Path

from ff import FlattenError, FlattenRequest, flatten_filelist

try:
    result = flatten_filelist(
        FlattenRequest(
            top_filelist=Path("testbench.f"),
            working_directory=Path.cwd(),
            predefined_macros=frozenset({"MACRO_1", "MACRO_2"}),
        )
    )
except FlattenError as error:
    # esim: prepare/ff 失败，跳过 build/run/check，仍执行 failure/finalize
    raise

print(result.output_filelist)
```

引擎不配置 root logger，不调用 `fatal()`。如需 trace，在 `FlattenRequest`
中传入提供 `debug(str)` 的 logger。

## 语法范围

详细契约见 [docs/ff-requirements.md](docs/ff-requirements.md)。第一版只处理
Verilog/SystemVerilog flat filelist，不考虑 mixed-language 或 logical library。

