# esim 完整实现计划

状态：已完成

## 目标

以 `docs/requirements/esim.md` 为可观察行为契约，按
`docs/development/designs/2026-08-08-esim-code-architecture-design.md` 的深模块边界，
通过 TDD 纵向切片实现首版 esim 的全部功能，并保留现有 `ff` 命令与公开
engine interface。

## 已确认的 public seams

- CLI：`esim TC ...` 与 `esim check ABS_SIM_DIR`。
- Configuration：`ConfigurationCompiler.locate/compile`。
- Application：`EsimApplication.run/check`。
- 文件产物：Simulation directory 中的快照、日志、waiver 和 artifact。
- 外部进程边界：测试使用 Scripted Process Runner，不 mock 自有模块。

## 实施切片

1. Configuration 入口：logical/absolute TC、Rules 默认/搜索、最小可编译调用。
2. Configuration 组合：include graph、合并、schema、args、provenance、unknown fields。
3. Workspace：路径布局、内核锁、clean/keep、原子快照和 waiver 发布。
4. VCS two-step：ff、build、run、声明式 plan 与 PASS/FAIL result。
5. Hooks 与 Log Policy：before/after、失败截断、finding、waiver。
6. VCS three-step：analyze/elaborate 顺序、日志和失败语义。
7. Stage action：build/run 缓存兼容性、artifact 验证与 NOT_RUN。
8. Log recheck：`esim check`、waiver 重建、主日志重判和 result 原子更新。
9. CLI/发布：entry point、退出码、User Guide、wheel/wheelhouse 与全部质量门禁。

## 实施约束

- 每个切片按“一个失败测试 → 最小实现 → 相关回归”推进。
- 测试只通过上述 public seams 观察行为。
- 每个可观察行为切片同步更新 `docs/development/verification.md`。
- 任何新 runtime dependency 先按仓库规范获得用户批准。
- 保护工作区中现有未提交的需求、架构和 demo 文件。

## 验证

- 每个红绿循环运行最小相关 pytest node/file。
- 切片完成后运行所有 esim 相关测试。
- 最终运行 `.venv/bin/python -m pytest`、`bash tools/quality/check.sh`、
  离线 wheelhouse 验证、`git diff --check` 与需求逐项审计。
