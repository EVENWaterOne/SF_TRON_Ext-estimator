# SF_TRON_Ext Estimator

本项目基于 SF_TRON / IsaacLab 双足机器人 locomotion 框架，在原 Stage 2 depth-based residual policy 中加入一个历史扰动估计器 `Disturbance_Estimator`。该 estimator 使用短时间历史状态估计外部扰动 `f_hat = [Fx, Fy, Fz]`，并把估计结果拼接到 Stage 2 residual policy 的输入中。

当前状态：工程集成、quick test、Isaac Sim smoke、sanity checks、三路评估语义和第一条 formal evaluation 都已跑通。需要注意的是，Run 1 minimum formal evaluation **没有显示 estimator 相对 `Baseline234` 的性能提升**；因此当前结论应保持为：estimator integration runnable, but Run 1 does not show a stable performance improvement.

## Project Motivation

原始 SF_TRON 控制框架采用两阶段训练：

- Stage 1: blind walking gait，在平地上学习基础行走。
- Stage 2: depth-based residual policy，利用 `11 x 18` depth map 适应 stepping-stone / discontinuous terrain。

Stage 2 的动作融合方式为：

```text
a_total = 0.25 * a_base + 0.75 * a_residual
```

其中 `a_base` 来自 Stage 1 base policy，`a_residual` 来自 Stage 2 residual policy。

原始 residual policy 主要依赖当前 observation 和 depth map。面对外部推力、接触扰动、摩擦/质量/质心偏差、传感器噪声或电机响应差异时，单帧 observation 不一定能显式告诉 policy “机器人刚刚受到了什么力”。真实机器人控制更接近 POMDP：外部扰动和隐含动力学参数往往需要从历史状态变化中推断。

因此本项目加入一个 estimator：

```text
z_hat_t = estimator(o_{t-H:t}, a_{t-H:t-1})
a_t = policy(o_t, z_hat_t)
```

第一版将 `z_hat` 具体定义为外力估计：

```text
f_hat = [Fx, Fy, Fz]
```

它是 state estimation / system identification 模块，不是新的 RL policy。理论目标是让 residual policy 不只看到当前状态和地形深度，还能看到一个显式扰动估计，从而更容易学习补偿动作。

## Estimator Integration

Estimator 输入历史长度为 10，每步 31 维：

```text
q(8), q_dot(8), body_orientation(3), body_angular_velocity(3),
previous_action(8), velocity_command(1)
```

因此 estimator 输入为：

```text
history: [agents_num, 10, 31]
```

Estimator 输出为：

```text
f_hat: [agents_num, 3]
```

原 Stage 2 residual policy 输入维度为：

```text
33 + 18 * 11 = 231
```

加入 estimator 后，将 `f_hat` 拼接到 residual state 末尾：

```text
residual_state = concat(original_residual_state, f_hat)
231 + 3 = 234
```

Stage 1 base policy 保持不变，不重训、不修改旧 `actor0.pth / critic0.pth`。Estimator 只接入 Stage 2 residual policy。

## Control Pipeline

整体链路如下：

```text
current observation
        |
        v
update history buffer
        |
        v
Disturbance_Estimator(history) -> f_hat
        |
        v
residual_state = concat(current_state, depth, f_hat)
        |
        +--------------------------+
        |                          |
        v                          v
base policy                  residual policy
actor0.pth                   actor1_est.pth
        |                          |
        v                          v
     a_base                  a_residual
        |                          |
        +-----------+--------------+
                    v
      a_total = 0.25 * a_base + 0.75 * a_residual
                    |
                    v
             Isaac Sim / IsaacLab environment
```

训练时，环境通过随机推力脉冲维护真实监督标签：

```text
external_force_label = [Fx, Fy, Fz]
```

Estimator 使用 `MSE(f_hat, external_force_label)` 更新。Residual policy 仍通过 PPO 更新；estimator 不参与 GAE，也不是 reward function 的一部分。

## Evaluation Modes

当前评估脚本显式区分三种模式：

| Mode | Input dim | Meaning |
|---|---:|---|
| `Legacy231` | 231 | 旧 `actor1.pth` residual policy，不含 estimator input |
| `Baseline234` | 234 | 当前 estimator-input residual policy，但设置 `f_hat=0` |
| `Estimator` | 234 | 当前 estimator-input residual policy，使用预测 `f_hat` |

`Baseline234` 是当前结构下的 ablation baseline。`Legacy231` 是历史参考，不应和 `Baseline234` 混用。

Run 1 minimum formal evaluation 结果见 `FORMAL_EVALUATION_RESULTS.md`。本次结果：

- `Legacy231` fall rate: `0.0103`
- `Baseline234` fall rate: `0.0276`
- `Estimator` fall rate: `0.0288`
- `Estimator - Baseline234` average reward delta: `-0.0137`

因此当前不能写 “estimator improves performance”。需要更多 episodes、repeated runs 或多 seed 后再判断趋势。

## Repository Layout

```text
SF_TRON_Ext/
  Run_2.py                         Stage 2 residual policy training/evaluation entry
  utils/Config/Config.py           Environment, robot, PPO, estimator config
  utils/Env/Tron_Env.py            IsaacLab environment and estimator history/force labels
  utils/Estimator/                 Disturbance estimator implementation
  utils/PPO/                       Actor-Critic and PPO buffer

model/                             Runtime robot assets and policy weights
tools/                             Smoke, sanity, and diagnostic scripts
artifacts/                         Ignored generated outputs
```

Root `model/...` is the current runtime asset source. `SF_TRON_Ext/model/` is kept ignored as duplicate candidate data and should not be deleted blindly.

## Quick Start

From the project root:

```powershell
cd E:\SF_TRON_Ext-estimator
.\run_tests.bat quick
```

This runs:

- Python compile checks
- environment import check
- shape/unit checks
- estimator smoke check

Isaac Sim / IsaacLab commands should run outside the Codex sandbox because Isaac/Kit/GPU caches are written outside this workspace.

For Isaac Sim scripts, set:

```powershell
$env:PYTHONEXE="E:\IsaacSim-5.1.0\kit\python\python.exe"
$env:PYTHONPATH="E:\SF_TRON_Ext-estimator;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_assets;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_tasks;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_rl;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_mimic"
$env:WARP_CACHE_PATH="E:\SF_TRON_Ext-estimator\artifacts\warp_cache"
```

Minimum formal evaluation:

```powershell
& "E:\IsaacSim-5.1.0\python.bat" evaluate_comparison.py 5 --agents 100 --steps 50 --terrain-rows 3 --terrain-cols 3 --include-legacy
```

## Current Progress

Overall progress is about 72%.

Completed:

- Original SF_TRON / IsaacLab environment reproduction
- Estimator prototype implementation
- Integration into Stage 2 residual policy
- External force labels and history buffer
- Quick tests, smoke tests, and sanity checks
- Stable force label diagnostic
- `Legacy231 / Baseline234 / Estimator` evaluation semantics
- First minimum formal evaluation record

Still TODO:

- Repeat or expand formal evaluation
- Run more episodes and/or repeated seeds
- Decide whether estimator shows a stable trend
- Write final result analysis for report/thesis
- Defer deprecated IsaacLab external force API migration unless it becomes blocking

## Documentation Map

- `PROJECT_PROGRESS_TODO.md`: overall progress and next TODOs
- `FORMAL_EVALUATION_PLAN.md`: formal evaluation design and command
- `FORMAL_EVALUATION_RESULTS.md`: recorded formal evaluation results
- `SESSION_HANDOFF.md`: latest session handoff and operational notes
- `PROJECT_DESCRIPTION.md`: background, design rationale, and implementation notes
- `COMMIT_BOUNDARY.md`: repository staging and asset boundary notes

## Current Conclusion

The estimator integration is runnable and the evaluation pipeline is now semantically clear. However, Run 1 did not show a performance improvement over `Baseline234`. The correct current conclusion is conservative:

```text
The estimator integration is runnable, but Run 1 does not show a stable performance improvement.
```
