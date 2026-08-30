# esim 完整特性 demo 扩展计划

## 目标

将 `tests/fixtures/esim-demo-project` 从最小 smoke fixture 扩展为可阅读、可执行、可审计的完整示范工程，覆盖 `docs/requirements/esim.md` 中首版全部用户可观察能力，同时保持真实 VCS Y-2026.03 可运行。

## Public seam

用户已确认固定为：

- `esim` CLI，包括逻辑/绝对 selector、Rules selector、完整运行、keep、Stage action 和 Log recheck；
- 公开应用引擎 API，仅用于不依赖真实 EDA license 的稳定自动测试；
- `$DV_TMP` 下的 flat filelist、配置快照、phase logs、waiver 汇总、simulator artifact 和 Result snapshot。

不通过私有方法、内部调用次数或实现模块结构验证。

## 实施阶段

1. 从权威需求建立“能力—demo 场景—测试证据”矩阵。
2. 逐个纵向切片扩展共享 Rules、两个 DTB、TC、hooks、filelists 和脚本；每个切片先红后绿。
3. 覆盖 two-step/three-step、两类后缀、include/merge、环境展开、args、全部 phase hooks、waiver、快照与诊断。
4. 用同一 demo 覆盖默认清理、keep、build/run Stage action、Log recheck、逻辑/绝对 selector 等 invocation 能力。
5. 更新 demo README、项目验证文档和特性矩阵。
6. 执行相关回归、完整 pytest、质量门禁及真实 VCS Y-2026.03 代表性仿真。

## 范围边界

- 不实现需求第 16 节明确排除的 Xcelium、suite/regression、timeout/environment/cwd/enabled、自动 cache fingerprint 或 built-in waiver。
- 不为“展示错误”向正常工程混入无法运行的非法配置；受控错误能力由独立测试临时构造输入验证。
- 不修改 esim 生产行为，除非红测试证明现有实现违反已确认需求；若发现此类冲突，先报告用户。
- 不提交、推送或改动用户已有的其他工作区修改。

## 验收

- 特性矩阵中每项首版能力都有 demo 文件、命令或自动测试证据；不以单个超大 TC 冒充覆盖。
- yyy 保持 YAML/two-step，zzz 保持 `.tc/.rules`/three-step，并各自展示不同能力组合。
- 自动测试通过公共 seam 验证已知字面值和产物。
- `.venv/bin/python -m pytest`、`bash tools/quality/check.sh` 和真实 Y-2026.03 代表性运行有实际结果记录。
