# ff/esim 双格式 User Guide 设计

日期：2026-08-09

状态：用户已于 2026-08-09 确认

## 目标

为 `ff` 和 `esim` 同时提供 Markdown 与可离线打开的 standalone HTML，消除
当前 `ff` 只有 HTML、`esim` 只有 Markdown 以及内容格式长期漂移的问题。

## 文档接口

- `docs/user/ff-user-guide.md` 与 `docs/user/esim-user-guide.md` 是唯一内容源。
- 同目录的 `.html` 是确定性生成并纳入版本控制的用户制品。
- `python scripts/generate_user_guides.py` 更新两份 HTML；`--check` 只检查并在
  生成物过期时返回非零状态。
- README 同时链接每份指南的 Markdown 和 HTML。

## 内容与视觉

- 两份指南均覆盖安装、快速开始、CLI、核心配置/输入规则、产物、错误排查和
  速查，并只描述已实现行为。
- Markdown 使用 H2 章、H3 可导航节和 H4 局部小节；生成 HTML 使用章容器、
  章内卡片与两级目录，不把全部主题平铺为同级卡片。
- HTML 使用蓝/紫主视觉、琥珀点缀和独立深色代码面，提供响应式侧栏、
  可读正文、代码语言标签、构建期语法高亮、表格、focus 样式和打印布局。
- 所有 CSS 内嵌；不引用 CDN、字体、图标、图片或外部脚本。
- 只使用少量原生 JavaScript 提供代码复制和当前章节高亮；无 JavaScript 时
  正文、导航和锚点仍完整可用，并尊重 `prefers-reduced-motion`。
- 不引入 Canvas UI、React、WebGL 或调研列表中的任何效果库。

## 生成设计

- 生成器使用开发依赖 `markdown-it-py` 渲染 CommonMark 并启用表格，使用
  `Pygments` 在构建期为 YAML/Bash fenced code 生成内嵌 token 标记。
- 一级标题提供页面标题；H2 生成章容器，H3 生成章内卡片和两级导航项。
- 每份指南至少包含两个 H2 章，每章至少包含一个 H3 节；生成器对违反该
  结构的输入返回受控错误。既有主题的显式 ID 在调整章节归属时保持不变。
- HTML 模板、样式和小型原生脚本由生成器统一管理，生成物不依赖附加资源。
- `--root` 允许在临时目录和独立工作树中通过同一 CLI seam 验证行为。
- 质量门禁运行 `--check`，防止 Markdown 修改后忘记更新 HTML。

## 范围边界

- 不改变 `ff`、`esim` CLI 或运行时行为。
- `markdown-it-py` 与 `Pygments` 只进入 `.[dev]`，不进入运行依赖或
  wheelhouse。
- 不把需求、设计、测试或开发过程加入用户发布包。
- 不增加客户端框架、WebGL、远程资源或构建时网络要求。

## 验证

- 通过生成器 CLI seam 做红绿测试：生成双份 standalone HTML、`--check`
  识别过期内容。
- 校验 HTML 语法、内部锚点、离线资源边界和 Markdown/HTML 同步。
- 桌面与窄屏渲染检查导航、正文、表格和代码块。
- 运行项目完整质量门禁。
