# SF_TRON_Ext 项目描述与扰动估计器 TODO

## 1. 项目概述

本项目是一个基于 IsaacLab / Isaac Sim 的 SF_TRON 双足机器人强化学习控制项目，核心目标是让双足机器人在平地和不连续 stepping-stone / 梅花桩地形上稳定行走。

当前控制框架使用 Proximal Policy Optimization (PPO)，并采用两阶段训练思路：

- Stage 1: 训练 blind walking gait。关闭或屏蔽地形深度输入，只使用机器人本体状态学习稳定平地行走。
- Stage 2: 训练 depth-based residual policy。启用深度相机，将地形感知输入 residual policy，使机器人适应 stepping-stone terrain。

现有 Stage 2 的动作融合方式为：

```text
a_total = 0.25 * a_base + 0.75 * a_residual
```

其中 `a_base` 来自 Stage 1 的已训练 blind policy，`a_residual` 来自 Stage 2 的残差策略。

## 2. 当前代码结构

当前目录中存在两份相近代码：

- 根目录下的 `Run_1.py`, `Run_2.py`, `utils`, `model`
- 子目录 `SF_TRON_Ext/` 下的 `Run_1.py`, `Run_2.py`, `utils`, `model`

建议后续主要以 `SF_TRON_Ext/` 子目录作为 package 版本维护，因为入口导入路径与 `from SF_TRON_Ext...` 更一致。

重要模块：

- `SF_TRON_Ext/Run_1.py`: Stage 1 或单策略 PPO 训练/推理入口。
- `SF_TRON_Ext/Run_2.py`: Stage 2 residual policy 训练/推理入口。
- `SF_TRON_Ext/utils/Env/Tron_Env.py`: IsaacLab 环境封装、观测构造、仿真 step、reward 计算。
- `SF_TRON_Ext/utils/Env/Scene_Initialization.py`: 地形、机器人、传感器、domain randomization 初始化。
- `SF_TRON_Ext/utils/PPO/Actor_Critic.py`: PPO actor / critic 网络、采样、更新、模型保存加载。
- `SF_TRON_Ext/utils/PPO/Buffer.py`: PPO rollout buffer 和 GAE 计算。
- `SF_TRON_Ext/utils/Config/Config.py`: 环境、机器人和 PPO 参数。
- `SF_TRON_Ext/model/`: USD 机器人模型、PTH/ONNX 权重和部署相关文件。

## 3. Isaac Sim / IsaacLab 环境

当前 Isaac Sim 版本需求为 Isaac Sim 5.1.0。

本机已将 Isaac Sim 放在：

```text
E:\IsaacSim-5.1.0
```

项目中的 IsaacLab 通过 junction 链接查找 Isaac Sim：

```text
E:\SF_TRON_Ext-main\isaaclab\_isaac_sim -> E:\IsaacSim-5.1.0
```

已验证：

- `isaacsim` 可以 import。
- `isaaclab` 可以 import。
- PyTorch 为 `2.7.0+cu128`。
- CUDA 可用。

由于 `E:\IsaacSim-5.1.0\python.bat` 默认会尝试将 `kit\python\python.exe` 复制为 `kit.exe`，而当前目录权限可能不允许复制，建议运行前显式设置：

```powershell
$env:PYTHONEXE="E:\IsaacSim-5.1.0\kit\python\python.exe"
```

然后使用 Isaac Sim 自带 Python 运行项目：

```powershell
cd E:\SF_TRON_Ext-main
& "E:\IsaacSim-5.1.0\python.bat" .\SF_TRON_Ext\Run_1.py
```

或运行 Stage 2：

```powershell
& "E:\IsaacSim-5.1.0\python.bat" .\SF_TRON_Ext\Run_2.py
```

## 4. Midterm Report 摘要

`Final-Year-Project-Midterm-Report.pdf` 是当前项目的重要说明文档。它描述了该项目的研究目标、训练方法和实验问题。

报告核心内容：

- 研究对象是 bipedal locomotion on discontinuous stepping-stone terrain。
- 使用 depth camera 直接观测地形，不依赖显式 SLAM 或地图构建。
- 观测包括机器人本体状态和 `11 x 18` depth image。
- 训练算法为 PPO。
- 训练框架为 two-stage training:
  - Stage 1: 在平地上学习 blind walking gait。
  - Stage 2: 引入深度相机和 stepping-stone terrain，使用 residual learning 适应不连续地形。
- 仿真使用 IsaacLab 的大规模并行能力，报告中提到可并行模拟 4000 个 agent，每轮收集 `4000 x 50 = 200000` 条经验。
- Stage 2 中 residual policy 对 base gait 进行补偿，而不是从零重新学习基本行走能力。

报告提到的 sim-to-real 问题：

- IMU angular velocity 和 joint angular velocity 噪声较大，直接输入神经网络会导致动作输出震荡。
- 简单滤波可能产生明显 phase delay。
- body pose 对策略输出影响很大，例如 pitch 小幅变化可能导致动作接近饱和。
- 空心水泥砖侧面黑洞会影响深度相机判断，导致机器人在梅花桩实验中偶尔踩空。
- 使用泡沫板遮住空心水泥砖孔洞后，实机踏石效果改善。

## 5. 历史扰动估计器想法

计划在现有 PPO 双足机器人控制框架中增加一个基于历史观测的深度学习扰动估计器。

该估计器不是 reinforcement learning policy，而是 state estimation / system identification 模块。它使用历史 `q, q_dot, action, IMU, cmd` 等信息预测外部扰动或隐变量：

```text
z_hat 或 f_hat
```

推荐第一版将 `z_hat` 具体定义为外力估计：

```text
f_hat = [Fx, Fy, Fz]
```

整体数据流：

```text
history: [q, q_dot, IMU, previous_action, velocity_cmd] over last H steps
        |
        v
disturbance estimator
        |
        v
f_hat / z_hat
        |
        v
residual policy input = current_state + depth + z_hat
```

建议第一版设置：

- `history_len = 10`
- 单步 estimator 输入：`q(8), q_dot(8), body_ori(3), body_ang_vel(3), previous_action(8), vel_cmd(1)`
- 单步维度：`31`
- 总输入维度：`10 x 31 = 310`
- estimator 输出维度：`3`
- 第一版网络结构：MLP `310 -> 256 -> 128 -> 3`

## 6. 可行性与理论收益

该想法在当前系统中不是基础行走的必要条件，但对实机鲁棒性有明确价值。

如果目标只是仿真中的平地行走或规则 stepping-stone terrain，现有 PPO + depth residual policy 已经能够完成主要任务，扰动估计器不是必须的。

如果目标是提升以下能力，该模块值得加入：

- 抗外力推扰。
- 抗 IMU / joint velocity 噪声。
- 适应摩擦、质量、质心、电机输出差异。
- 缩小 sim-to-real gap。
- 提升复杂实机环境下 residual policy 的稳定性。

理论依据是：真实机器人控制问题更接近 POMDP，而不是完全可观测 MDP。外力、摩擦、质量偏差、传感器 bias、电机延迟等因素通常不是单帧观测可直接确定的 hidden state / latent dynamics parameter。

当前策略近似为：

```text
a_t = pi(o_t)
```

加入历史估计器后变为：

```text
z_hat_t = f(o_{t-H:t}, a_{t-H:t-1})
a_t = pi(o_t, z_hat_t)
```

如果 `z_hat_t` 能提供当前单帧观测中没有的动力学信息，那么 residual policy 的输入会更接近 Markov state，从理论上有机会提升鲁棒性和性能上界。

风险：

- 如果 estimator 训练不好，`z_hat` 可能放大噪声。
- 如果训练时扰动分布和实机误差不一致，收益会变小。
- 如果 residual policy 过度依赖 `z_hat`，可能在 estimator 误差较大时失稳。

因此第一版建议只做低维 `f_hat`，并通过随机推力脉冲构造清晰监督信号。

## 7. 实施 TODO

### 7.1 整理新工程目录

- 新建 git 工作目录，例如：

```text
E:\SF_TRON_Ext-estimator
```

- 复制精简项目内容：
  - `SF_TRON_Ext/` 主代码
  - `model/` 权重与 USD
  - `Final-Year-Project-Midterm-Report.pdf`
  - README / 项目说明
  - Isaac Sim / IsaacLab 环境说明
- 不复制：
  - `__pycache__`
  - `.idea`
  - 重复的根目录 `utils/model`
  - 临时缓存和训练输出
- 初始化 git。
- 添加 `.gitignore`，忽略缓存、IDE 文件、训练日志、临时输出和大型中间模型。

### 7.2 加入随机推力脉冲扰动

- 在配置中新增 `DisturbanceCfg`：
  - `enable_push = True`
  - `push_interval`
  - `push_duration`
  - `max_force`
  - 作用位置为 base / body link
- 在 `Tron_Env` 中维护每个 agent 当前外力标签：

```text
external_force_label: [agents_num, 3]
```

- 第一版只施加水平随机推力：

```text
Fz = 0
```

- 无推力时 `external_force_label` 置零。
- 在仿真 step 中注入随机推力脉冲，同时保存真实外力作为 estimator 的监督标签。

### 7.3 实现历史扰动估计器

- 新增模块：

```text
SF_TRON_Ext/utils/Estimator/Disturbance_Estimator.py
```

- 实现 MLP estimator：

```text
input_dim = history_len * 31
hidden = [256, 128]
output_dim = 3
loss = MSE(f_hat, external_force_label)
```

- estimator 单独保存：

```text
model/NN_Model/estimator.pth
```

- estimator 不是 PPO，不参与 GAE 或 reward 计算。

### 7.4 维护 history buffer

- 在 `Tron_Env` 初始化时创建：

```text
history_obs_buffer: [agents_num, history_len, 31]
```

- 每个 RL step 更新一次 history。
- reset agent 时清空对应 agent 的 history。
- estimator 输入不包含 depth map，避免把地形视觉问题和动力学扰动估计混在一起。

### 7.5 接入 residual policy

- base policy 保持原样，不改 Stage 1 权重。
- `state_trained[:, 33:] = 0` 的 blind policy 输入逻辑继续保留。
- residual policy 输入改为：

```text
residual_state = concat(current_state, f_hat)
```

- residual policy 的 `state_dim` 从：

```text
33 + 18 * 11
```

扩展为：

```text
33 + 18 * 11 + 3
```

- 旧的 `actor1.pth / critic1.pth` 与新输入维度不兼容，新增命名：

```text
actor1_est.pth
critic1_est.pth
estimator.pth
```

### 7.6 训练流程

Stage 1:

- 保持现有流程。
- 训练或加载 `index=0` 的 blind base policy。

Stage 2:

1. 加载 frozen base policy `AC_trained(index=0)`。
2. 初始化 residual policy `AC(index=1)`，输入包含 `f_hat`。
3. 每个 step 获取当前 state。
4. 更新 history buffer。
5. estimator 输出 `f_hat`。
6. 拼接 `residual_state = concat(state, f_hat)`。
7. residual policy 输出 `action2`。
8. 执行动作融合：

```text
a_total = 0.25 * a_base + 0.75 * a_residual
```

9. PPO 更新 residual policy。
10. 用真实随机推力标签监督更新 estimator。
11. 分别打印 PPO loss / reward / estimator MSE。

## 8. 测试与评估指标

### 8.1 环境检查

- Isaac Sim 5.1.0 可以启动。
- `isaacsim` 和 `isaaclab` 可以 import。
- PyTorch CUDA 可用。

### 8.2 单元级检查

- `history_obs_buffer` shape 正确。
- reset 后对应 agent 的 history 清零。
- `external_force_label` shape 为 `[agents_num, 3]`。
- `f_hat` shape 为 `[agents_num, 3]`。
- `residual_state` shape 为 `[agents_num, 33 + 18 * 11 + 3]`。

### 8.3 Smoke test

使用较小规模快速测试：

```text
agents_num_in_play = 10
maximum_step = 50
```

确认：

- 能完成至少一个 episode。
- 不出现 shape mismatch。
- PPO buffer 正常存储扩展后的 state。
- estimator loss 正常下降或至少可计算。

### 8.4 对比评估

对比两组：

- baseline: 原 residual policy，不使用 estimator。
- estimator: residual policy 输入拼接 `f_hat`。

评估指标：

- 随机推力下摔倒率。
- 平均 episode length。
- 平均 reward。
- velocity tracking reward。
- termination reward。
- 推力期间和非推力期间的 `force_mse`。
- 更高 IMU / joint velocity noise 下的稳定性。

第一版成功标准：

- 无推力时性能不明显下降。
- 有随机推力时摔倒率降低或 episode length 增加。
- estimator 的 `force_mse` 在训练中可观察到下降趋势。
- residual policy 能在加入 `f_hat` 后正常训练和保存。
