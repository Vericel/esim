# 严格工程质量体系设计

## 目标

为 ff 建立可在本地和 GitHub Actions 中一致执行的严格工程质量体系，同时保持运行时只依赖 Python 包，不把 Node 或质量工具带入最终 wheelhouse。

## 平台与版本契约

- ff 0.2.0 要求 Python 3.11 或更高版本。
- 正式支持原生 Linux 和 WSL2；POSIX 路径、权限和 symlink 语义为权威。
- CI 验证 CPython 3.11、3.12、3.13 和 3.14。
- Node 24 只运行官方 npm Pyright，不属于 ff 运行时或发布制品。
- `botticelle-onelog>=0.1,<0.2` 保持运行时依赖；CI 和 wheelhouse 固定从 v0.1.0 对应提交 `7738cac48b383624b9b5a6bf3434a2a40210c568` 构建。

## 质量门禁

- Ruff 0.15.22 负责格式化、import 和 lint，目标 `py311`，启用 `E/F/I/UP/B/SIM/C4/PIE/RUF`。
- Pyright 1.1.411 在 Node 24 上运行；`src/` 使用 strict，测试与工程脚本使用 basic。
- pytest-cov 7.1.0 对 `src/ff` 统计 branch coverage，低于 90% 失败。
- pre-commit 4.6.0 在 commit 阶段自动格式化和执行安全修复，再运行 Pyright；pre-push 执行完整测试与覆盖率。
- `scripts/check.sh` 是本地完整质量入口；CI 调用相同命令，不维护另一套语义。

## 测试组织

测试按 public seam 和稳定能力拆分。Engine 分为 inputs、conditions、filelists、comments、environment、options、output 和 path validation；CLI 分为 output、logging 和 errors。测试函数名与断言保持不变，拆分前后收集数量必须一致。

稳定部分回归通过能力文件执行；单用例使用 pytest node ID；临时组合使用 `-k`。不增加 unit/integration 目录或重复表达 seam 的 marker。

## 新增可执行 seam

`python scripts/check_docs.py` 检查仓库 Markdown/HTML 中的本地链接和 fragment。成功返回 0；失败返回 1，并输出稳定的 `path:line: target: reason` 诊断。外部 URL、邮件链接和纯模板占位符不进行网络访问。

分发 seam 通过 wheel metadata 和干净环境离线安装验证 Python 3.11、版本 0.2.0、onelog 依赖范围及 console entry point。

## CI 与发布

GitHub Actions 在 PR、main push 和手工触发时运行 Python 矩阵、quality 和 package 三类门禁。package job 生成包含 ff、onelog、Rich 和传递依赖的完整 wheelhouse，在干净 Python 3.11 venv 中以 `--no-index` 安装并运行 smoke test，然后上传压缩包与 SHA-256 清单。

CI 不创建 tag 或 GitHub Release。版本遵循 SemVer，`pyproject.toml` 是唯一版本源，`CHANGELOG.md` 记录 Unreleased 与 0.2.0，人工发布清单控制 tag 和制品发布。
