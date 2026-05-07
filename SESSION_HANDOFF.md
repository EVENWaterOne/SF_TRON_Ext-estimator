# SF_TRON_Ext Estimator Session Handoff

## 1. 一句话状态

当前工作目录是 `E:\SF_TRON_Ext-estimator`。这个目录已经集成了历史扰动估计器 `Disturbance_Estimator`，并把估计出的 `f_hat / z_hat` 拼接到 Stage 2 residual policy 的输入中。轻量测试和完整 Isaac Sim headless smoke test 都已经跑通过。

`CODEX_HANDOFF.md` 中写的 `smoke_test.py BLOCKED` 已经过时。最新状态是：`smoke_test.py` 已通过，`run_tests.bat quick` 也已通过。

## 2. 目录与环境

关键路径：

```text
当前项目目录: E:\SF_TRON_Ext-estimator
原始项目目录: E:\SF_TRON_Ext-main
Isaac Sim 5.1.0: E:\IsaacSim-5.1.0
IsaacLab 链接: E:\SF_TRON_Ext-estimator\isaaclab_repo -> E:\SF_TRON_Ext-main\isaaclab
```

运行前需要设置：

```powershell
$env:PYTHONEXE="E:\IsaacSim-5.1.0\kit\python\python.exe"
$env:PYTHONPATH="E:\SF_TRON_Ext-estimator;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_assets;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_tasks;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_rl;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_mimic"
```

推荐直接用：

```powershell
cd E:\SF_TRON_Ext-estimator
.\run_tests.bat quick
```

完整 Isaac Sim headless smoke test：

```powershell
.\run_tests.bat full
```

注意：曾经执行过 `isaaclab.bat -i none`，但日志显示 Windows 路径解析有问题，且它没有正确把依赖装进 Isaac Sim Python。后续为了跑通 smoke test，明确给 Isaac Sim Python 安装过：

```text
flatdict
h5py
```

用户检查过 Python 3.12 user site，里面没有 `torch`、`torchvision`、`torchaudio` 残留。后续不要随便再跑安装脚本，尤其不要在没确认解释器和路径的情况下跑 `isaaclab.bat -i`。

## 3. 项目背景和设计决策

`Final-Year-Project-Midterm-Report.pdf` 是项目核心说明文档。它说明了原始项目目标：基于 IsaacLab / Isaac Sim，用 PPO 训练 SF_TRON 双足机器人在平地和 stepping-stone / 梅花桩地形上行走。

原始控制框架：

- Stage 1: blind walking gait，在平地上学习基础行走。
- Stage 2: depth-based residual policy，使用 `11 x 18` depth map 适应不连续地形。
- 动作融合：

```text
a_total = 0.25 * a_base + 0.75 * a_residual
```

本轮新增想法：

- 增加一个非 RL 的历史扰动估计器。
- 它是 state estimation / system identification 模块，不是 policy。
- 输入历史 `q, q_dot, action, IMU, cmd`。
- 输出外部扰动或隐变量 `z_hat`。
- v1 将 `z_hat` 具体定义为随机推力估计：

```text
f_hat = [Fx, Fy, Fz]
```

重要决策：

- 第一版不预测 mass/friction latent。
- 第一版不做无监督 next-state prediction。
- 第一版只用随机推力脉冲作为监督标签。
- `f_hat` 只拼接到 Stage 2 residual policy 输入。
- Stage 1 base policy 不改，不重训，不改变旧 `actor0.pth / critic0.pth` 输入维度。

## 4. 当前实现内容

当前 estimator 输入历史长度为 10，每步 31 维：

```text
q(8), q_dot(8), body_ori(3), body_ang_vel(3), previous_action(8), vel_cmd(1)
```

因此 estimator 输入为：

```text
history: [agents_num, 10, 31]
```

输出为：

```text
f_hat: [agents_num, 3]
```

residual policy 输入维度从原始：

```text
33 + 18 * 11 = 231
```

扩展为：

```text
231 + 3 = 234
```

实现要点：

- `Tron_Env` 中维护 `history_obs_buffer`。
- `Tron_Env` 中维护 `external_force_label` 作为 estimator 监督标签。
- `Tron_Env` 中维护 `push_time_remaining` 和 `push_force_xy`。
- `push_force_xy` 修复了一个重要问题：一个推力脉冲期间力的方向和大小保持不变，不再每帧随机改变。
- `Actor_Critic` 根据 index 分流输入维度：
  - `index=0`: base policy，state dim 231。
  - `index=1` 且 estimator enabled: residual policy，state dim 234。
- residual policy 模型保存使用 `_est` 后缀，例如：

```text
actor1_est.pth
critic1_est.pth
actor1_est_f.pth
critic1_est_f.pth
```

- `Run_2.py` 中流程已经改为：
  1. 获取当前 `state`。
  2. 更新 estimator history。
  3. estimator 预测 `f_hat`。
  4. 拼接 `residual_state = concat(state, f_hat)`。
  5. base policy 使用 blind state。
  6. residual policy 使用 extended residual state。
  7. 执行动作融合。
  8. 用真实 `external_force_label` 更新 estimator。
  9. PPO 存储和更新 residual policy。

## 5. 文件说明

文档文件：

- `PROJECT_DESCRIPTION.md`: 项目背景、PDF 报告摘要、扰动估计器设计和 TODO。
- `CODEX_HANDOFF.md`: Claude Code 早期交接。里面关于 `smoke_test.py BLOCKED` 的结论已经过时，不应作为最新真相来源。
- `CLAUDE.md`: Claude Code 的通用行为指南，不是项目实现说明。
- `SESSION_HANDOFF.md`: 当前文件，作为新 session 的最新交接入口。

测试和运行文件：

- `run_tests.bat`: 当前推荐测试入口。`quick` 不跑完整仿真，`full` 会启动 Isaac Sim headless。
- `check_env.py`: 检查 Python、PyTorch、CUDA、`isaacsim`、`isaaclab`。
- `test_shapes.py`: 纯 PyTorch shape/unit test，不启动 Isaac Sim。已验证 28/28 PASS。
- `tools/smoke_check_estimator.py`: 快速检查 estimator 输出、base/residual policy state dim。
- `smoke_test.py`: 启动 Isaac Sim headless，跑小规模完整训练链路。
- `evaluate_comparison.py`: baseline vs estimator 对比评估脚本。注意这里 baseline 是 `f_hat=0` 的 estimator-input policy，不是旧 `actor1.pth` 原始 baseline。

核心实现文件：

- `SF_TRON_Ext/utils/Config/Config.py`
  - 新增 `Robot_Config.DisturbanceCfg`。
  - 新增 `PPO_Config.EstimatorParam`。
  - 新增 `base_state_dim=231` 和 `residual_state_dim=234`。

- `SF_TRON_Ext/utils/Env/Tron_Env.py`
  - 新增 history buffer。
  - 新增随机推力标签和外力注入。
  - 新增 `update_estimator_history()`。
  - 新增 `augment_state_with_estimate()`。
  - 新增 `push_force_xy`，确保一个 push 脉冲期间标签稳定。

- `SF_TRON_Ext/utils/Estimator/Disturbance_Estimator.py`
  - MLP estimator。
  - 输入 `[agents_num, history_len, obs_dim]`。
  - 输出 `[agents_num, 3]`。
  - 支持 `update()`、`save_model()`、`load_model()`、`save_checkpoint()`。

- `SF_TRON_Ext/utils/PPO/Actor_Critic.py`
  - 支持 base/residual 不同 state dim。
  - residual 模型使用 `_est` 后缀。
  - 新增 `save_checkpoint(episode)`。

- `SF_TRON_Ext/Run_2.py`
  - Stage 2 入口。
  - 已接入 estimator。
  - 每 100 episode 保存 actor/critic 和 estimator checkpoint。

## 6. 测试命令与结果

推荐 quick 测试：

```powershell
cd E:\SF_TRON_Ext-estimator
.\run_tests.bat quick
```

已验证结果：

```text
[PASS] All requested tests passed.
```

其中包括：

- Python 编译检查通过。
- `check_env.py`: 6/6 PASS。
- `test_shapes.py`: 28/28 PASS。
- `tools/smoke_check_estimator.py`: PASS。

完整 headless 仿真测试：

```powershell
cd E:\SF_TRON_Ext-estimator
.\run_tests.bat full
```

已经手动跑通过一次，等价于运行：

```powershell
& "E:\IsaacSim-5.1.0\python.bat" smoke_test.py
```

smoke test 做了：

- 启动 Isaac Sim headless。
- 创建 `Tron_Env`。
- 生成 `15 x 15` terrain。
- 跑 10 个 RL step。
- 每一步检查 `state/history/f_hat/residual_state/next_state/reward` shape。
- 检查 estimator loss 非 NaN。
- 检查 PPO buffer。
- 执行一次 `AC.update()`。
- 保存/加载 estimator。
- 保存 checkpoint。

关键通过输出：

```text
=== All smoke tests passed! ===
```

一次 smoke test 中 PPO update 输出过：

```text
Best Model Saved
std_mean tensor(0.5000, device='cuda:0')
Experience Collected: 100
Critic Loss: 0.3772
Actor Loss: 0.0189
reward: -0.11173828691244125
```

这只是短仿真 smoke test，不代表正式训练效果已经验证。

## 7. 已知问题和注意事项

`CODEX_HANDOFF.md` 的旧结论已经过时：

- 旧结论：`smoke_test.py` blocked by `isaaclab.app` import。
- 当前真实状态：通过正确 `PYTHONPATH` 和补齐 `flatdict/h5py` 后，`smoke_test.py` 已通过。

重要 warning：

- IsaacLab 警告 `set_external_force_and_torque` deprecated。当前不影响测试，但后续可以迁移到新的 `permanent_wrench_composer.set_forces_and_torques`。
- IsaacLab 警告 `enable_external_forces_every_iteration=False`。如果训练中发现外力引起速度噪声，可以考虑在 PhysX 配置里开启该选项，并适当提高 velocity iterations。

当前生成物：

- smoke test 生成过 `model/NN_Model/actor1_est*.pth`。
- smoke test 生成过 `model/NN_Model/critic1_est*.pth`。
- smoke test 生成过 `model/NN_Model/estimator.pth`。
- smoke test 生成过 `training_log.csv`。

git 状态：

- 首次提交已完成，基线 commit 为 `128671e Initial estimator integration baseline`。
- 当前 tracked 工作区干净，剩余显示项均为 ignored 验证产物或本机链接。
- `__pycache__`、`artifacts/`、`training_log.csv`、测试 checkpoint、`SF_TRON_Ext/model/` 和 `isaaclab_repo/` 不进入提交。
- 根目录 `model/...` 已作为当前运行资产源纳入首次提交。

环境风险：

- 不建议再次直接跑 `isaaclab.bat -i`，之前它触发过 torch/torchvision 下载，并有 Windows 路径截断日志。
- 如果新 session 需要安装依赖，先明确使用的是 Isaac Sim Python 还是 conda/base Python。
- C 盘 Python 3.12 user site 经用户检查没有 torch 残留，但不要再随意安装大包。

实现风险：

- `Run_2.py` 只通过短仿真 smoke test，还没有做长时间训练验证。
- `evaluate_comparison.py` 还没有验证实际结果质量。
- 当前 estimator 训练目标是随机外力标签，不能直接宣称已经提升 sim-to-real，只能说链路已跑通。

## 8. 下一步建议

建议下一步按这个顺序做：

1. 先确认提交后基线。
   - 重新跑 `.\run_tests.bat quick`。
   - 确认 tracked 工作区仍然干净，ignored 产物没有进入提交。
   - 不在 Codex 沙盒内跑 Isaac Sim full/smoke，避免 cache 写权限造成假卡住。

2. 跑一次更长但仍小规模的训练 sanity check。
   - 建议 `agents_num=100`、`maximum_step=50`、`episode=20`。
   - 观察 reward、estimator loss、fall/reset、NaN 和 checkpoint 写入情况。
   - 该阶段只验证链路稳定性，不宣称性能提升或 sim-to-real 改善。

3. 验证外力标签是否真的稳定。
   - 记录某几个 agent 的 `external_force_label`。
   - 确认一个 push duration 内 `Fx/Fy` 不抖动。

4. 评估 `evaluate_comparison.py`。
   - 明确 baseline 定义：当前脚本 baseline 是 `f_hat=0`。
   - 如果要比较旧 residual policy，需要单独写 legacy baseline，因为旧 `actor1.pth` 输入维度是 231，而 estimator residual policy 输入维度是 234。

5. 后续可以考虑优化外力 API。
   - 当前 `set_external_force_and_torque` 能跑，但已 deprecated。
   - 有空再迁移到 IsaacLab 推荐的新 wrench composer API。

## 9. 2026-05-06 Codex TODO 落地更新

已完成：

- `.gitignore` 已扩展，新增忽略 `artifacts/`、checkpoint、临时/诊断权重和递归 `__pycache__`。
- `run_tests.bat` 已把新工具脚本加入编译检查，并为 `full` smoke test 增加成功哨兵文件检查。
- `smoke_test.py` 不再把测试权重写回正式 `model/NN_Model`，改写入 `artifacts/smoke_test`。
- 新增 `tools/training_sanity_check.py`，用于短训练链路验证，默认输出到 `artifacts/sanity_check`。
- 新增 `tools/force_label_diagnostic.py`，用于抽样检查 `external_force_label / push_time_remaining / push_force_xy`。
- `evaluate_comparison.py` 已明确 baseline 语义：baseline 是 234 维 estimator-input residual policy 下的 `f_hat=0`，不是旧 231 维 `actor1.pth`。
- `evaluate_comparison.py` 已修复为单个 Isaac Sim app/environment 内依次评估 baseline 和 estimator，避免同进程重复启动 Isaac app。
- 新增 `Env_Config.EnvParam.terrain_num_rows / terrain_num_cols`，正式默认仍是 `15 x 15`；smoke/sanity/diagnostic 默认覆盖为 `3 x 3` 以加快验证。
- `Software_Setup.py` 改用 `parse_known_args()`，避免工具脚本参数与 IsaacLab `AppLauncher` 参数冲突。

已验证：

- `.\run_tests.bat quick` 通过。
- Isaac Sim smoke test 在沙盒外通过，输出 `=== All smoke tests passed! ===`，使用 CUDA。
- 短训练 sanity check 通过：`100 agents x 50 steps x 5 episodes`，reward/loss 非 NaN，平均 fall rate 约 `0.02832`。
- 外力标签诊断通过：`active_agent_steps=342`，同一个 push pulse 内标签保持稳定。
- `evaluate_comparison.py 1 --agents 10 --steps 10 --terrain-rows 3 --terrain-cols 3` 通过并打印 comparison table。

注意：

- 完整 Isaac Sim 类测试需要写 Isaac/Kit/GPU cache。Codex 沙盒内运行会因为不能写 `E:\IsaacSim-5.1.0\kit\cache` 等目录而卡住或报 cache 错；这类命令需要在沙盒外运行。
- `model/` 与 `SF_TRON_Ext/model/` 大部分资产重复；当前运行配置使用根目录 `model/...`。Estimator 新权重只存在于根目录 `model/NN_Model`。本轮没有删除任何重复资产，后续如要统一路径应单独规划。

## 10. 提交边界收尾记录

新增 `COMMIT_BOUNDARY.md` 作为首次提交前的 staging guide。

模型资产对比结果：

- `model/` 与 `SF_TRON_Ext/model/` 之间有 31 个 byte-identical duplicate。
- 4 个同名 base 权重内容不同：
  - `NN_Model/actor0.pth`
  - `NN_Model/actor0_f.pth`
  - `NN_Model/critic0.pth`
  - `NN_Model/critic0_f.pth`
- 7 个 estimator 相关权重只存在于根目录 `model/NN_Model/`：
  - `actor1_est.pth`
  - `actor1_est_ckpt0.pth`
  - `actor1_est_f.pth`
  - `critic1_est.pth`
  - `critic1_est_ckpt0.pth`
  - `critic1_est_f.pth`
  - `estimator.pth`
- 没有只存在于 `SF_TRON_Ext/model/` 的文件。

当前默认策略：不盲删任何模型目录。首次提交已选择根目录 `model/` 作为运行资产源；后续如要清理重复资产，应单独明确选择：

1. 以根目录 `model/` 作为运行资产源。
2. 改配置统一到 `SF_TRON_Ext/model/...` 并补齐 estimator 资产。
3. 暂时保留双份并在提交说明中解释原因。

## 11. 2026-05-07 提交策略决策

已决定：

- 根目录 `model/` 是当前运行资产源。
- 保持 `Env_Config.EnvParam.file_path = "model/Robot_Model/SF_TRON1A.usd"`。
- 保持 `PPO_Config.EstimatorParam.model_path = "model/NN_Model/estimator.pth"`。
- `SF_TRON_Ext/model/` 暂不删除，但作为重复候选资产默认忽略。
- `isaaclab_repo/` 是 junction，指向 `E:\SF_TRON_Ext-main\isaaclab`，默认忽略，不提交到本仓库。
- `model/NN_Model/*_ckpt*.pth` 仍视为测试 checkpoint，不提交。

首次提交已纳入根目录 `model/NN_Model` 中这些 estimator runtime 文件：

- `actor1_est.pth`
- `actor1_est_f.pth`
- `critic1_est.pth`
- `critic1_est_f.pth`
- `estimator.pth`

## 12. 2026-05-07 首次提交后状态

已完成：

- 首次提交已创建：`128671e Initial estimator integration baseline`。
- 提交前 `.\run_tests.bat quick` 已通过。
- 根目录 `model/...` 已作为当前运行资产源提交。
- 当前 tracked 工作区干净，剩余状态项均为 ignored 产物或本机 junction。
- 提交后 `.\run_tests.bat quick` 已重新通过。
- 提交后 20 episode sanity check 已通过：`100 agents x 50 steps x 20 episodes`，无 NaN，`reward_mean_avg=0.030518`，`estimator_loss_last=346.513184`，`fall_rate_avg=0.029230`。
- 提交后评估 smoke 已通过：`evaluate_comparison.py 1 --agents 10 --steps 10 --terrain-rows 3 --terrain-cols 3` 输出 comparison table；baseline 仍定义为 234 维 estimator-input policy 下的 `f_hat=0`。

当前 ignored 项包括：

- `artifacts/`
- `training_log.csv`
- `__pycache__/`
- `model/NN_Model/*_ckpt*.pth`
- `SF_TRON_Ext/model/`
- `isaaclab_repo/`

下一步入口：

- 先 review 并提交本次 `SESSION_HANDOFF.md` 更新。
- 下一步可选择更长 sanity check 或 legacy baseline 设计。
- 以上短验证结果只记录链路稳定性和脚本语义，不作为 estimator 性能提升结论。

注意：

- Isaac Sim 脚本直接用 `E:\IsaacSim-5.1.0\python.bat` 运行时，需要显式设置项目 `PYTHONPATH`，否则会报 `ModuleNotFoundError: No module named 'isaaclab.app'`。
- 已验证的沙盒外命令使用了 `PYTHONPATH` 指向本仓库和 `isaaclab_repo\source\...` 各模块。

## 13. 2026-05-07 Legacy Baseline 与更长 Sanity Check

已完成：

- `evaluate_comparison.py` 新增 `--include-legacy`，可选评估旧 `actor1.pth` 的 231 维 residual policy。
- 默认 `evaluate_comparison.py` 语义保持不变：baseline 仍是 234 维 estimator-input residual policy 下的 `f_hat=0`。
- `tools/smoke_check_estimator.py` 已检查三种维度：
  - base policy: 231
  - estimator residual policy: 234
  - legacy residual policy: 231
- `.\run_tests.bat quick` 已通过，输出包含 `legacy residual policy state_dim: 231`。
- 三路评估 smoke 已通过：
  - 命令：`evaluate_comparison.py 1 --agents 10 --steps 10 --terrain-rows 3 --terrain-cols 3 --include-legacy`
  - 输出列明确为 `Legacy231`、`Baseline234`、`Estimator`。
  - 本次 smoke fall rate 均为 `0.0000`，只说明流程和标签语义跑通。
- 更长 sanity check 已通过：
  - 命令：`tools\training_sanity_check.py --agents 100 --steps 50 --episodes 50`
  - `reward_mean_avg=0.138678`
  - `estimator_loss_last=192.888153`
  - `fall_rate_avg=0.026684`
  - 无 NaN，checkpoint 写入 `artifacts/sanity_check`。

注意：

- 50 episode sanity check 仍不是正式性能实验，只能作为链路稳定性证据。
- legacy baseline 是旧 231 维 `actor1.pth`，不要和 `f_hat=0` 的 234 维 baseline 混用。
- 外力 API deprecated warning 仍存在，暂不迁移。

下一步入口：

- 提交 `evaluate_comparison.py`、`tools/smoke_check_estimator.py` 和本 handoff 更新。
- 后续可规划正式评估：多 episode、多 seed、固定扰动设置，并分别报告 `Legacy231`、`Baseline234`、`Estimator`。

## 14. 2026-05-07 总体进度与正式评估入口

已完成：

- `b16a84c Add legacy baseline evaluation path` 已提交。
- `PROJECT_PROGRESS_TODO.md` 已更新为当前总体进度表：项目约 70%，系统搭建、工程验证、评估语义修正已完成，正式实验和结果分析待做。
- 新增 `FORMAL_EVALUATION_PLAN.md`，固定正式评估的三组对象、指标、最小 formal run 命令和结果解释规则。

下一步入口：

- 先跑 `.\run_tests.bat quick`。
- 再沙盒外跑 `FORMAL_EVALUATION_PLAN.md` 中的 minimum formal run：
  - `evaluate_comparison.py 5 --agents 100 --steps 50 --terrain-rows 3 --terrain-cols 3 --include-legacy`
- 只有正式实验多次结果稳定时，才写 estimator 性能提升结论。

## 15. 2026-05-07 Formal Evaluation Plan 提交后状态

已完成：

- `acda0d9 Document formal evaluation plan` 已提交。
- `PROJECT_PROGRESS_TODO.md` 已同步到当前状态：正式实验设计基本完成，下一步是运行 minimum formal run。
- `FORMAL_EVALUATION_PLAN.md` 已记录当前文档基线 commit，并继续作为正式评估入口。

下一步入口：

- 必跑 `.\run_tests.bat quick`。
- 沙盒外运行 minimum formal run：
  - `evaluate_comparison.py 5 --agents 100 --steps 50 --terrain-rows 3 --terrain-cols 3 --include-legacy`
- 将结果按 `Legacy231`、`Baseline234`、`Estimator` 分别记录；仍不得把单次 formal run 写成最终性能结论。

## 16. 2026-05-07 Minimum Formal Run 结果

已完成：

- `.\run_tests.bat quick` 已通过。
- minimum formal run 已在沙盒外通过：
  - `evaluate_comparison.py 5 --agents 100 --steps 50 --terrain-rows 3 --terrain-cols 3 --include-legacy`
- 新增 `FORMAL_EVALUATION_RESULTS.md`，记录正式实验 Run 1。

Run 1 summary:

- `Legacy231` fall rate: `0.0103`
- `Baseline234` fall rate: `0.0276`
- `Estimator` fall rate: `0.0288`
- `Estimator - Baseline234` avg reward delta: `-0.0137`
- `Estimator` force MSE during push: `302.5451`
- `Estimator` force MSE no push: `0.0012`

当前解释：

- 三路正式评估流程跑通，模式标签没有混淆。
- 本次 minimum formal run 不显示 estimator 相对 `Baseline234` 的性能提升；fall rate 和 avg reward 都略差。
- 当前只能写：estimator integration runnable, but this run does not show a stable performance improvement.

下一步入口：

- 提交 `FORMAL_EVALUATION_PLAN.md`、`FORMAL_EVALUATION_RESULTS.md`、`SESSION_HANDOFF.md`。
- 后续正式评估应扩大 episodes 或 repeated seeds，再判断性能趋势。
