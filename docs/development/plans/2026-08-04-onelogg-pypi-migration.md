# onelogg PyPI 分发迁移实施计划

对应设计：
[2026-08-04-onelogg-pypi-migration-design.md](../designs/2026-08-04-onelogg-pypi-migration-design.md)

## 目标

让 esim 0.2.0 从 PyPI 正式分发 `onelogg` 0.1.1 解析日志运行时依赖，同时保持
`onelog` 导入 API、日志行为和离线安装能力不变。

## 实施步骤

1. 在 `tests/test_distribution.py` 通过 wheel `METADATA` public seam 添加失败
   断言，要求 `onelogg<0.2,>=0.1.1`，先运行精确测试确认因旧依赖名失败。
2. 最小修改 `pyproject.toml` 使分发测试通过；不修改 `src/ff/cli.py` 或类型
   stub。
3. 把 `.github/workflows/ci.yml`、`scripts/build-wheelhouse.sh` 和开发安装命令
   从固定 Git commit 迁移为 PyPI 精确版本 `onelogg==0.1.1`。
4. 新增 ADR，并同步 `AGENTS.md`、需求、README、用户手册、开发指南、发布
   清单、验证矩阵和 CHANGELOG。历史设计与计划保留不变。
5. 搜索当前仓库中的旧分发身份，排除被忽略的历史 worktree 和生成物后确认只
   剩有意保留的历史记录。
6. 依次运行分发测试、完整 pytest、`bash scripts/check.sh`、`git diff --check`
   以及使用空目录的完整离线 wheelhouse 验证；最后检查工作区状态。

## TDD seam

- Public seam：构建后的 esim wheel 标准元数据，以及
  `scripts/build-wheelhouse.sh` 提供的离线安装入口。
- 独立期望值：已发布分发的规范名称和兼容范围字面值
  `Requires-Dist: onelogg<0.2,>=0.1.1`。
- 不 mock pip、文件系统或内部模块；使用现有真实 wheel 构建测试和临时目录。

## 完成标准

- wheel 元数据只声明新分发身份，源码仍导入 `onelog`。
- CI 和 wheelhouse 不再引用旧 commit 或 `botticelle-onelog`。
- 当前权威文档完整描述新分发身份、版本及同名导入冲突风险。
- 项目完整质量门禁和离线 wheelhouse smoke test 实际通过。
