# esim hooks 层级简化实施计划

## 目标

将 TC/Rules 中所有 phase 的 hooks schema 简化为 hooks 级的
`before`/`after` 命令列表和共享 `continue_on_error`，并同步需求、
领域术语、快照、fixture 与用户文档。

## 实施步骤

1. 先在配置编译 public seam 增加新 schema 的失败测试。
2. 最小修改配置模型、解码、合并与快照，使测试通过。
3. 在执行 public seam 验证共享 `continue_on_error` 的失败语义。
4. 迁移所有受管 fixture 和文档示例，更新变更记录。
5. 运行受影响测试、Ruff 与差异健全检查。

## 验证

- `.venv/bin/python -m pytest tests/test_esim_configuration_compilation.py`
- `.venv/bin/python -m pytest tests/test_esim_execution.py`
- 对本次修改的 Python 文件运行 Ruff format/check
- `git diff --check`
