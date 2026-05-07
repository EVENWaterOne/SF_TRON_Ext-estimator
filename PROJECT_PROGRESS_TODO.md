# 项目总体进度 TODO 表

## Summary

当前项目整体处于 **“系统集成完成，工程验证通过，正式实验尚未开始”** 阶段。原始 locomotion baseline 和 estimator 原型都已经可运行；现在最重要的是区分“已完成工程工作”和“还不能写最终结论的实验工作”。

## Progress Table

| 阶段 | 状态 | 当前说明 | 下一步 |
|---|---:|---|---|
| 1. 原始项目理解与环境复现 | 已完成 | PDF、原始 Stage 1/Stage 2、Isaac Sim/IsaacLab 环境已梳理；quick/full smoke 均已跑通 | 仅在环境变化时复查 |
| 2. Git 与资产边界 | 已完成 | 已有初始提交 `128671e` 和验证记录提交 `ed2f463`；根目录 `model/...` 是运行资产源；产物被 `.gitignore` 收住 | 先提交当前三文件改动 |
| 3. Estimator 原型实现 | 已完成 | 已实现 history buffer、外力标签、`Disturbance_Estimator`、`f_hat` 拼接、234 维 residual policy | 暂不扩展 mass/friction latent |
| 4. 链路级工程验证 | 已完成 | `quick`、Isaac smoke、外力标签诊断、20/50 episode sanity check 均通过；无 NaN | 继续只把 sanity 当稳定性证据 |
| 5. 评估语义修正 | 基本完成 | 已区分 `Legacy231`、`Baseline234`、`Estimator`；三路评估 smoke 已通过 | 提交当前评估脚本改动 |
| 6. 正式实验设计 | 未开始 | 还没有固定多 seed、多 episode、扰动设置和统计口径 | 下一阶段重点规划 |
| 7. 正式实验运行 | 未开始 | 目前只有 smoke/sanity，不能证明 estimator 性能提升 | 跑 formal evaluation 后再写结论 |
| 8. 结果分析与报告 | 未开始 | 还不能写“estimator improves performance”的结论 | 等正式实验数据 |
| 9. 技术债与清理 | 暂缓 | deprecated 外力 API、`SF_TRON_Ext/model/` 重复资产仍保留 | 正式实验前不优先处理 |

## Immediate TODO

- **提交当前工程进度**
  - 提交 `evaluate_comparison.py`、`tools/smoke_check_estimator.py`、`SESSION_HANDOFF.md`。
  - 提交信息建议：`Add legacy baseline evaluation path`。

- **建立正式实验计划**
  - 固定三组对比：`Legacy231`、`Baseline234`、`Estimator`。
  - 固定指标：fall rate、avg reward、episode length、termination reward、force MSE。
  - 固定实验规模：先小规模 formal run，再扩大到多 seed。

- **运行正式评估**
  - 不再只跑 `1 episode smoke`。
  - 至少使用多 episode、固定扰动配置，记录完整表格。
  - 结果只在统计足够后写入报告结论。

## Assumptions

- 当前总体进度约为 **65%-70%**。
- 已完成的是“系统搭建与工程可信度”；未完成的是“实验可信度与论文结论”。
- 根目录 `model/...` 继续作为运行资产源。
- Isaac Sim 实验默认沙盒外运行，并显式设置项目 `PYTHONPATH`。
