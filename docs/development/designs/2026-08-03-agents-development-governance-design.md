# 项目代理开发规范设计

## 目标

在仓库根目录建立唯一的 `AGENTS.md`，为整个项目提供简洁、强制且可执行的代理开发规范；同时按读者和用途统一文档目录，避免目录结构受具体技能名称影响。

## 适用范围

- 根目录 `AGENTS.md` 适用于整个仓库。
- 具体领域事实仍由 `CONTEXT.md`、需求、ADR、设计和用户文档分别维护；`AGENTS.md` 只定义读取顺序、变更流程和质量门禁，不复制正文。
- 本次立即迁移现有文档并更新仓库内引用，保留所有未提交内容。

## 文档结构

```text
docs/
├── requirements/
│   └── ff.md
├── user/
│   └── ff-user-guide.html
└── development/
    ├── adr/
    ├── designs/
    ├── plans/
    ├── research/
    └── verification.md
```

`README.md` 和 `CONTEXT.md` 保留在仓库根目录。

正式设计和实施计划分别进入 `docs/development/designs/` 与 `docs/development/plans/`。`$planning-with-files` 的 `task_plan.md`、`findings.md` 和 `progress.md` 只进入已被 Git 忽略的 `.planning/<task-id>/`。同一任务两层路径使用相同日期和 slug；重名时增加 `-02`、`-03` 后缀，禁止覆盖。

## 开发流程

代理开始工作前读取 `AGENTS.md`、`CONTEXT.md`、相关需求和 ADR，并检查工作区状态。新增功能、缺陷修复和任何可观察行为变化必须使用 `$tdd`，先确认 public seam，再按一个失败测试、最小实现、下一条测试的纵向切片推进。纯文档、注释、格式和不改变行为的配置变更豁免 TDD。

非简单行为变更先形成设计；需要正式实施步骤时再形成计划。预计超过三个阶段或五次工具操作的任务使用 `$planning-with-files` 保存临时执行状态。

## 决策门禁

Python 版本、最低支持版本以及任何运行时依赖的新增、删除或升级，必须先向用户说明动机、替代方案、兼容性和部署影响，由用户决定。批准后同步更新项目元数据、README、用户文档、需求和相关 ADR，并完成验证。

## Git 与验证

提交遵循英文 Conventional Commits；一个提交只包含一个逻辑变更。代理只有在用户明确要求时才能提交、推送、变基或改写历史。较大功能或脏工作区优先使用独立 worktree；不得覆盖、回滚或顺带提交用户已有改动。

任务完成前运行最小相关测试和完整 `.venv/bin/python -m pytest`（虚拟环境不存在时使用当前已激活 Python 的 `python -m pytest`），并检查迁移后的路径引用。没有实际验证不得宣称完成；受环境限制的未验证项必须明确报告。
