# esim 代码架构规划

状态：已完成（架构设计已由用户确认）

## 目标

以 `docs/requirements/esim.md` 为行为契约，结合现有 `ff` 展平引擎，设计可以逐纵向切片实施的 esim Python 代码架构。输出应明确模块职责、interface、seam、依赖方向、包目录、执行数据流和建议实施顺序，不写生产代码。

## 工作项

1. 核对当前代码、需求、ADR 和发布约束。
2. 识别领域模型、用例编排、外部 adapter 与持久化的 seam。
3. 评估模块深度，避免通过层和为单个实现预设无价值 seam。
4. 编写 `docs/development/designs/2026-08-08-esim-code-architecture-design.md`。
5. 检查与需求、术语和现有 ff 架构一致性，运行文档验证。

## 交付物

- esim 模块图与依赖规则。
- 每个深模块的 interface、隐藏复杂度与错误边界。
- 建议的 `src/esim/` 和测试目录布局。
- 主运行、Stage action 和 `esim check` 的调用流。
- 按 public seam 组织的 TDD 实施顺序。

## 验证

- `python3 scripts/check_docs.py`
- `git diff --check`
- `git status --short`

本任务为纯架构文档，不运行代码测试。
