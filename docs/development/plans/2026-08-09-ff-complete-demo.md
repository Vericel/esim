# ff 完整特性 demo 实施计划

## 目标

在 `tests/fixtures/esim-demo-project` 中建立 ff 完整特性 fixture，作为后续 ff CLI、
flattening engine、flat filelist 产物和 esim 集成测试的统一输入。

## 实施顺序

1. 从 `docs/requirements/ff.md` 建立逐项能力矩阵，区分正向可组合、独立正向和
   受控错误场景。
2. 确认 public seam 与设计。
3. 按纵向 TDD 切片扩展 yyy complete/full filelist，每次先观察预期红灯，再增加最小
   fixture 转绿。
4. 增加不能进入正常 VCS 编译路径的 CLI/输出安全/受控错误场景。
5. 更新 demo README、FEATURES 和项目验证矩阵。
6. 运行相关回归、完整门禁与 VCS Y-2026.03 代表性实跑。

## 范围边界

- 仅覆盖 `docs/requirements/ff.md` 已确认为支持的行为；明确不支持的语法只保留为
  受控拒绝证据，不作为正向 feature。
- 不修改生产行为；如红测试证明当前实现与需求冲突，先向用户报告。
- 不覆盖、删除或提交用户已有的工作区变更。

## 验收

- 能力矩阵无未映射的已支持 ff 行为。
- 至少一个正向综合 filelist 可同时通过 ff CLI、engine 和 esim/VCS 路径。
- 自动测试不依赖 EDA license，真实仿真作为独立验收。
- `.venv/bin/python -m pytest`、`bash scripts/check.sh` 和 Git 边界检查实际通过。
