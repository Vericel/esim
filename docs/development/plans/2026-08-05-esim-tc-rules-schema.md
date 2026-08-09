# esim TC/Rules schema 设计访谈计划

状态：已完成（需求见 `docs/requirements/esim.md`）

## 目标

通过逐项设计访谈，明确 TC、Rules 的领域边界、YAML schema、嵌套与合并语义，以及 esim 从命令行输入到仿真器调用的处理流程。本计划只产出经用户确认的需求文档与必要的领域术语/ADR，不实现代码。

## 访谈与记录方式

1. 核对现有权威文档、调研证据和代码现状。
2. 每次只提出一个需要用户决策的问题，同时给出推荐答案和取舍。
3. 术语一经确认就同步到 `CONTEXT.md`；只在符合项目标准时新增 ADR。
4. 用户结束设计访谈后，将已确认的可观察行为整理为权威需求 `docs/requirements/esim.md`；未确认的实现细节不擅自补入。

## 设计分支

- TC 与 Rules 的领域定义和身份。
- Rules 搜索、TC/Rules include 与循环处理。
- 字段归属、合并优先级和列表/标量合并规则。
- ff、build/analyze/elaborate、simulate 阶段模型。
- hooks 生命周期、失败与 shell 执行语义。
- 命令行入口、有效配置生成、诊断与可复现性。

## 验证

- 对照 `CONTEXT.md`、`docs/requirements/ff.md`和已接受 ADR，确认无术语或架构冲突。
- 检查设计文档的内部链接、`git diff --check` 和 `git status --short`。
- 本计划不改变可观察行为，不运行 TDD 或代码测试。
