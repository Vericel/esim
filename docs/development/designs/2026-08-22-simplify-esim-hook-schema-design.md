# esim hooks 层级简化设计

## 背景

现有 TC/Rules 将 `before`/`after` 定义为包含 `commands` 和
`continue_on_error` 的 mapping，使常用 hook 需要多一层结构。

## 已确认设计

所有 phase 的 `hooks` 统一使用：

```yaml
hooks:
  before:
    - echo prepare
  after:
    - echo finish
  continue_on_error: false
```

- `before` 和 `after` 是可选 `list[str]`；缺失或空列表不增加命令。
- `continue_on_error` 是 hooks 级的可选布尔值，同时作用于该 phase 的 before 和 after。
- 列表按 Rules→TC 合并顺序追加；`continue_on_error` 由后层显式值覆盖，最终缺省为 `false`。
- 非零命令仍会使当前 hook 失败；`true` 只表示继续当前 before/after 列表的剩余命令，不放过失败或继续后续节点。
- 旧的 `before.commands`/`after.commands` 嵌套形式不再是受支持 schema。

## 公开验证 seam

通过 `ConfigurationCompiler.compile` 验证 TC/Rules 合并和快照，通过
`ExecutionEngine.execute` 验证命令继续与失败截断。
