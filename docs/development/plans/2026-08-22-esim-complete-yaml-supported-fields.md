# esim complete YAML 支持字段覆盖计划

## 目标

让 `tests/fixtures/esim-demo-project/dv/xxx/yyy/tests/features/complete.tc`
只包含 esim 首版支持的 TC 字段，并尽可能覆盖全部支持字段；将未支持
字段移到独立 fixture，专门验证 WARNING 和 `ignored_fields` 记录。
`complete.yaml` 仅作为指向该实体文件的兼容符号链接。

## 范围

1. 以 `docs/requirements/esim.md` 和配置 schema 实现交叉核对 TC 支持字段。
2. 调整 complete YAML fixture 及其相关断言。
3. 新增或调整独立 unknown-fields fixture，覆盖所有当前不支持字段的 WARNING。
4. 同步 fixture 功能矩阵，运行相关测试和完整质量门禁。

## 实施步骤

1. 盘点 TC 所有支持字段和现有 fixture 覆盖。
2. 先调整测试，使其要求 complete fixture 无忽略字段，独立 fixture 产生完整 WARNING。
3. 运行最小测试并确认预期失败。
4. 最小化修改 fixture 使测试通过，同步说明。
5. 运行相关回归和 Ruff；全量测试与 `tools/quality/check.sh` 留到 pre-push/PR 边界。

## 后续：完整 TC 参考入口

1. 将实体文件改名为 `complete.tc`，保留相对符号链接
   `complete.yaml -> complete.tc`。
2. 在该参考 TC 中统一使用不带花括号的 `$NAME` 环境变量写法，
   并将 `continue_on_error` 放在 `before`/`after` 之后。
3. 通过 fixture 文件系统 seam 验证实体与链接关系，并使用
   `complete.tc` 运行现有 Configuration/Application 回归。
4. 在根 README、esim User Guide、demo README 和特性矩阵中公开该参考路径。
