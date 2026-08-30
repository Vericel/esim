# ff 人工发布清单

CI 不创建 tag 或 GitHub Release。发布由维护者人工确认以下项目。

## 版本与变更

- [ ] 根据 SemVer 决定版本号；`pyproject.toml` 是唯一代码版本源。
- [ ] 把 `CHANGELOG.md` 的相关 Unreleased 条目移入带日期的版本章节。
- [ ] 同步 README、用户文档、需求、ADR 和安装示例中的版本或依赖变化。
- [ ] 确认 Python 最低版本及所有运行依赖变化已经用户批准。

## 验证与制品

- [ ] 在干净 CPython 3.11 环境安装固定 onelog commit（`onelogg` 0.1.2）和 `.[dev]`。
- [ ] 在创建 release tag 前执行 `npm ci` 和 `bash scripts/check.sh`；确认
  90% branch coverage 门禁通过。
- [ ] 确认 ff/esim User Guide 的 Markdown 与 standalone HTML 均存在，且
  `scripts/generate_user_guides.py --check` 通过。
- [ ] 两份 User Guide 均显示章标题、章内节卡片和两级章节导航；没有退化为
  同级主题平铺。
- [ ] 使用空目录执行：

  ```bash
  FF_PYTHON=.venv/bin/python \
    bash scripts/build-wheelhouse.sh dist/wheelhouse
  ```

- [ ] 检查 wheelhouse 只包含 esim、onelogg、Rich、PyYAML 和运行时传递依赖。
- [ ] 在独立干净 venv 中再次使用 `--no-index` 安装并运行
  `ff --help` 与 `esim --help`。
- [ ] 使用 `sha256sum -c dist/wheelhouse/SHA256SUMS` 校验全部 wheel。
- [ ] 把 wheelhouse 压缩包和 `SHA256SUMS` 作为发布制品保留。
- [ ] 确认源码制品保留 `.vscode/settings.json` 和 `editors/`；如果只分发
  wheelhouse，额外附上 `editors/` 目录。
- [ ] 面向用户的发布包同时包含 `docs/user/` 下四份 User Guide 文件。

## 人工发布

- [ ] 审查 CI 的 Python、quality 和 package jobs 全部通过。
- [ ] 取得明确授权后创建签名或 annotated tag；tag 必须与版本一致。
- [ ] 推送 tag，人工创建 GitHub Release，并附上 CHANGELOG 摘要与校验和制品。
- [ ] 在新的干净环境从最终发布制品完成一次离线安装 smoke test。
