# 项目总体进度 TODO 表

## Summary

当前项目整体处于 **“系统集成完成，工程验证通过，评估语义已修正，正式实验已启动但尚未形成最终结论”** 阶段。原始 locomotion baseline 和 estimator 原型都已经可运行；Run 1 minimum formal evaluation 已完成，但结果暂未显示 estimator 相对 `Baseline234` 的性能提升。

## Progress Table

| 阶段 | 状态 | 当前说明 | 下一步 |
|---|---:|---|---|
| 1. 原始项目理解与环境复现 | 已完成 | PDF、原始 Stage 1/Stage 2、Isaac Sim/IsaacLab 环境已梳理；quick/full smoke 均已跑通 | 仅在环境变化时复查 |
| 2. Git 与资产边界 | 已完成 | 已有提交到 `8131981`；根目录 `model/...` 是运行资产源；产物被 `.gitignore` 收住 | 仅在新实验/文档改动后提交 |
| 3. Estimator 原型实现 | 已完成 | 已实现 history buffer、外力标签、`Disturbance_Estimator`、`f_hat` 拼接、234 维 residual policy | 暂不扩展 mass/friction latent |
| 4. 链路级工程验证 | 已完成 | `quick`、Isaac smoke、外力标签诊断、20/50 episode sanity check 均通过；无 NaN | 继续只把 sanity 当稳定性证据 |
| 5. 评估语义修正 | 已完成 | 已区分 `Legacy231`、`Baseline234`、`Estimator`；三路评估 smoke 已通过并提交 | 后续保持标签语义不混用 |
| 6. 正式实验设计 | 已完成 | `FORMAL_EVALUATION_PLAN.md` 已固定对比对象、指标、最小 formal run 和解释规则 | 后续按同一口径扩展实验 |
| 7. 正式实验运行 | 已启动 | Run 1 minimum formal evaluation 已完成并记录到 `FORMAL_EVALUATION_RESULTS.md`；当前未显示 estimator 提升 | 重复/扩大 formal evaluation |
| 8. 结果分析与报告 | 早期 | Run 1 只能支持“工程可运行但未显示稳定提升”的谨慎结论 | 等更多 formal runs 后再写最终结论 |
| 9. 技术债与清理 | 暂缓 | deprecated 外力 API、`SF_TRON_Ext/model/` 重复资产仍保留 | 正式实验前不优先处理 |

## Immediate TODO

- **重复/扩大 formal evaluation**
  - 继续使用三组对比：`Legacy231`、`Baseline234`、`Estimator`。
  - 下一步建议先重复 Run 1 设置，或扩大到 `episodes=10`，确认趋势是否稳定。
  - 每次都记录 commit、命令、terrain 设置、agents/steps/episodes、三组结果表格和 warning。

- **保持谨慎结论**
  - Run 1 结果：`Estimator` fall rate `0.0288`，`Baseline234` fall rate `0.0276`，avg reward delta `-0.0137`。
  - 当前不能写 “estimator improves performance”。
  - 当前可写：estimator integration runnable, but Run 1 does not show a stable performance improvement.

## Assumptions

- 当前总体进度约为 **72%**。
- 已完成的是“系统搭建、工程可信度、评估语义修正、第一条 formal evaluation 记录”；未完成的是“重复正式实验、稳定性统计、论文结论”。
- 根目录 `model/...` 继续作为运行资产源。
- Isaac Sim 实验默认沙盒外运行，并显式设置项目 `PYTHONPATH`。

## 2026-05-12 更新

- `.\run_tests.bat quick` 已重新通过，轻量工程基线仍然有效。
- 扩大 formal evaluation 到 `episodes=10` 的 Run 2 已尝试两次，但两次都在 Isaac Sim 启动阶段发生 Windows access violation，未产生 comparison table。
- 因为 Run 2 没有有效指标，当前性能结论不变：Run 1 仍是唯一有效 formal result，暂未显示 estimator 相对 `Baseline234` 的稳定性能提升。
- 当前总体进度仍约为 **72%**：工程链路和评估语义完成，正式实验已开始，但扩大实验被 Isaac Sim/RTX-Hydra 启动崩溃阻塞。
- 下一步优先级从“直接扩大 episode”调整为“先稳定 Isaac Sim 启动环境，再重复 10 episode formal run”。
