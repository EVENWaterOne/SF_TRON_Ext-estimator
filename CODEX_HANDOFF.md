# Codex Handoff: 扰动估计器集成进展

## 已完成的工作

### 1. Bug 修复：推力随机化 (`Tron_Env.py`)

原 `_update_external_force_label()` 每次调用都重新生成 `force_xy`，导致一个推力脉冲期间力的方向和大小每帧都在变，estimator 收到的监督标签是噪声。

修复：新增 `self.push_force_xy` 缓冲区，推力开始时生成一次力，整个脉冲期间复用。

改动位置：
- `__init__` 中新增 `self.push_force_xy = torch.zeros((self.agents_num, 2), device=self.device)`
- `prim_initialization` 中新增 `self.push_force_xy[agent_index] = 0`
- `_update_external_force_label` 中 `force_xy` 只在 `start_push` 时生成

### 2. Checkpoint 保存

原来只有 "best model" 和 "latest each episode" 两种保存，训练中断就丢进度。

改动：
- `Actor_Critic.py` 新增 `save_checkpoint(episode)` 方法，保存 `actor{index}{suffix}_ckpt{episode}.pth`
- `Disturbance_Estimator.py` 新增 `save_checkpoint(episode)` 方法，保存 `estimator_ckpt{episode}.pth`
- `Run_2.py` 每 100 个 episode 自动 checkpoint

### 3. 测试脚本

| 脚本 | 用途 | 依赖 Isaac Sim |
|------|------|----------------|
| `test_shapes.py` | 纯 PyTorch shape 检查（28 项全过） | 否 |
| `check_env.py` | 环境检查（6/6 全过） | 是 |
| `smoke_test.py` | 小规模完整训练流程验证 | 是 |
| `evaluate_comparison.py` | baseline vs estimator 对比评估 | 是 |

## 未解决的问题

### `isaaclab.app` import 失败

`smoke_test.py` 和 `Run_2.py` 都卡在这个 import 上。

**根因**：`isaaclab` 是一个 namespace package，实际 Python 包在 `isaaclab_repo/source/isaaclab/` 里。`python.bat` 没有把 `isaaclab_repo/source` 加到 `sys.path`。

**已尝试但未成功**：
- 重命名 `isaaclab` → `isaaclab_repo`（消除了 namespace 遮挡）
- 在 `Software_Setup.py` 中动态插入 `isaaclab_repo/source` 到 `sys.path`
- `from isaaclab.app import AppLauncher` 仍然报 `No module named 'isaaclab.app'`

**需要进一步排查**：
1. 确认 `isaaclab_repo/source/isaaclab/` 里是否有 `__init__.py` 和 `app` 子模块
2. 确认正确的 import 路径（可能需要 `isaaclab_repo/source/isaaclab` 而不是 `isaaclab_repo/source`）
3. 参考原项目 `E:\SF_TRON_Ext-main` 的运行方式，看它是怎么处理这个 import 的
4. 可能需要 `pip install -e isaaclab_repo/source/isaaclab` 来正确安装包

## 文件改动清单

```
SF_TRON_Ext/utils/Env/Tron_Env.py          # push_force_xy 缓冲区 + 修复推力逻辑
SF_TRON_Ext/utils/Env/Software_Setup.py     # 尝试动态添加 isaaclab source 路径（可能需要回滚）
SF_TRON_Ext/utils/PPO/Actor_Critic.py       # 新增 save_checkpoint()
SF_TRON_Ext/utils/Estimator/Disturbance_Estimator.py  # 新增 save_checkpoint()
SF_TRON_Ext/Run_2.py                        # 每 100 episode 自动 checkpoint
test_shapes.py                              # 新增：shape 单元测试
smoke_test.py                               # 新增：smoke test
evaluate_comparison.py                      # 新增：对比评估
check_env.py                                # 新增：环境检查
```

## 测试结果

- `test_shapes.py`: 28/28 PASS
- `check_env.py`: 6/6 PASS（Python 3.11.13, PyTorch 2.7.0+cu128, RTX 3060 Laptop, isaacsim OK, isaaclab OK）
- `smoke_test.py`: BLOCKED（`isaaclab.app` import 失败）
- `Run_2.py`: BLOCKED（同上）
