# ff/esim 双格式 User Guide 实施计划

**目标：** 以 Markdown 为唯一内容源，为 ff/esim 生成并验证 standalone HTML。

**设计：** `docs/development/designs/2026-08-09-user-guide-formats-design.md`

## 阶段一：生成器 seam

1. 为 `tools/docs/generate_user_guides.py` 写失败的 CLI 测试。
2. 实现最小 Markdown→standalone HTML 生成。
3. 为 `--check` 过期检测写失败测试并实现。

## 阶段二：双份内容源

1. 把 ff 现有完整用户内容整理为 `ff-user-guide.md`。
2. 按 `docs/requirements/esim.md` 补全 `esim-user-guide.md` 的用户任务章节。
3. 生成两份 HTML，并更新 README 的双格式入口。

## 阶段三：质量门禁与文档

1. 把生成同步检查接入 `tools/quality/check.sh`。
2. 更新开发指南、发布清单和验证矩阵。
3. 校验 HTML 语法、链接、离线边界和生成幂等性。

## 阶段四：视觉与完整回归

1. 渲染桌面和窄屏页面并检查布局。
2. 运行相关测试、完整 pytest、`tools/quality/check.sh` 和 `git diff --check`。
3. 核对工作区范围，不纳入本地 EDA 产物。

## 阶段五：视觉质量返工

1. 通过生成器 CLI seam 复现并锁定单色代码缺陷。
2. 在构建期加入 YAML/Bash token 高亮、代码语言标签和多色页面层级。
3. 修复桌面与手机导航的无 JavaScript 可用性，重新截图并执行完整门禁。

## 阶段六：章节体系

1. 通过生成器 CLI seam 为 H2 章、H3 节和两级导航建立红绿测试。
2. 把 ff 整理为四章、esim 整理为六章，并保留既有主题锚点。
3. 拒绝少于两章或任一章没有 H3 节的 Markdown，把规范接入现有质量门禁。
