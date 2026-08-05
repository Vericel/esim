# 使用 PyPI onelogg 分发

ff/esim 的日志运行时依赖使用正式 PyPI 分发
`onelogg>=0.1.1,<0.2`，Python 导入名保持 `onelog`。开发、CI 和离线
wheelhouse 固定使用 `onelogg==0.1.1`，不再从 Git commit 构建临时
`botticelle-onelog` 分发。该决策取代 ADR-0003 和 ADR-0004 中关于 onelog
分发身份、依赖范围及固定源码来源的部分；既有日志所有权、summary 配置、
原子日志发布、Python 3.11 和离线 wheelhouse 决策继续有效。

`onelogg` 0.1.1 是经过发布工作流和干净环境安装验证的正式制品，要求
Python 3.8 或更高版本并声明 `rich>=13,<15`。使用索引中的不可替换版本文件，
可以让普通 `pip install` 解析 esim 的依赖，也让 CI 和 wheelhouse 使用同一个
分发身份。wheelhouse 仍生成 SHA-256 清单并在无索引的干净虚拟环境执行
`pip check` 和 `ff --help`，因此目标 EDA 机器不依赖网络或 PyPI 可用性。

PyPI 上无关的 `onelog`、旧 `botticelle-onelog` 和新的 `onelogg` 是不同分发，
但可能安装同一个 `onelog` 导入路径。开发和部署必须使用干净环境，不支持将
这些分发混装；源码和调用者继续使用 `from onelog import get_logger`。
