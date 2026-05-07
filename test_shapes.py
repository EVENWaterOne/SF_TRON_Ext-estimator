"""Unit-level shape checks for the disturbance estimator integration.
Run with: python test_shapes.py
Does NOT require Isaac Sim — only PyTorch."""

import torch
import sys

# ---- Config mirroring Config.py ----
AGENTS_NUM = 10
HISTORY_LEN = 10
OBS_DIM = 31
LATENT_DIM = 3
HIDDEN_LAYERS = [256, 128]
BASE_STATE_DIM = 33 + 18 * 11  # 231
RESIDUAL_STATE_DIM = BASE_STATE_DIM + LATENT_DIM  # 234
ACTUATOR_NUM = 8
DEVICE = "cpu"

passed = 0
failed = 0


def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  PASS: {name} = {actual}")
        passed += 1
    else:
        print(f"  FAIL: {name} = {actual}, expected {expected}")
        failed += 1


# ---- 1. Estimator forward pass ----
print("\n=== 1. Disturbance_Estimator shapes ===")
sys.path.insert(0, "SF_TRON_Ext")
from utils.Estimator.Disturbance_Estimator import Disturbance_Estimator


class MockEstimatorParam:
    history_len = HISTORY_LEN
    obs_dim = OBS_DIM
    latent_dim = LATENT_DIM
    hidden_layers = HIDDEN_LAYERS
    lr = 1e-3
    model_path = "model/NN_Model/estimator.pth"


estimator = Disturbance_Estimator(MockEstimatorParam(), DEVICE)

history = torch.randn(AGENTS_NUM, HISTORY_LEN, OBS_DIM)
f_hat = estimator.predict(history)
check("f_hat.shape", tuple(f_hat.shape), (AGENTS_NUM, LATENT_DIM))

# ---- 2. Estimator update ----
print("\n=== 2. Estimator update ===")
target_force = torch.randn(AGENTS_NUM, LATENT_DIM)
loss_val, pred = estimator.update(history, target_force)
check("loss is float", isinstance(loss_val, float), True)
check("prediction shape", tuple(pred.shape), (AGENTS_NUM, LATENT_DIM))

# ---- 3. History buffer roll ----
print("\n=== 3. History buffer simulation ===")
history_buffer = torch.zeros(AGENTS_NUM, HISTORY_LEN, OBS_DIM)
for t in range(15):
    obs = torch.randn(AGENTS_NUM, OBS_DIM)
    history_buffer = torch.roll(history_buffer, shifts=-1, dims=1)
    history_buffer[:, -1, :] = obs
check("history_buffer.shape", tuple(history_buffer.shape), (AGENTS_NUM, HISTORY_LEN, OBS_DIM))
# After 15 fills with dim=10, the oldest 5 entries should be overwritten
check("history_buffer[0,0,:] != 0 (oldest overwritten)", (history_buffer[0, 0, :] != 0).any().item(), True)

# ---- 4. State augmentation ----
print("\n=== 4. State augmentation ===")
state = torch.randn(AGENTS_NUM, BASE_STATE_DIM)
residual_state = torch.concatenate((state, f_hat.detach()), dim=1)
check("residual_state.shape", tuple(residual_state.shape), (AGENTS_NUM, RESIDUAL_STATE_DIM))

# ---- 5. Actor/Critic network dims ----
print("\n=== 5. Actor_Critic network shapes ===")
from utils.PPO.Actor_Critic import Actor, Critic

# Base policy (index=0, no estimator)
actor_base = Actor(BASE_STATE_DIM, 256, ACTUATOR_NUM)
critic_base = Critic(BASE_STATE_DIM, 256)
mu_base, std_base = actor_base(state)
v_base = critic_base(state)
check("actor_base mu.shape", tuple(mu_base.shape), (AGENTS_NUM, ACTUATOR_NUM))
check("actor_base std.shape", tuple(std_base.shape), (ACTUATOR_NUM,))
check("critic_base v.shape", tuple(v_base.shape), (AGENTS_NUM, 1))

# Residual policy (index=1, with estimator)
actor_res = Actor(RESIDUAL_STATE_DIM, 256, ACTUATOR_NUM)
critic_res = Critic(RESIDUAL_STATE_DIM, 256)
mu_res, std_res = actor_res(residual_state)
v_res = critic_res(residual_state)
check("actor_res mu.shape", tuple(mu_res.shape), (AGENTS_NUM, ACTUATOR_NUM))
check("actor_res std.shape", tuple(std_res.shape), (ACTUATOR_NUM,))
check("critic_res v.shape", tuple(v_res.shape), (AGENTS_NUM, 1))

# ---- 6. Buffer shape ----
print("\n=== 6. PPO Buffer shapes ===")
from utils.PPO.Buffer import Agent_State_Buffer

MAX_STEP = 50
buf = Agent_State_Buffer(RESIDUAL_STATE_DIM, ACTUATOR_NUM, AGENTS_NUM, MAX_STEP, DEVICE)
check("state_buffer.shape", tuple(buf.state_buffer.shape), (MAX_STEP, AGENTS_NUM, RESIDUAL_STATE_DIM))
check("action_buffer.shape", tuple(buf.action_buffer.shape), (MAX_STEP, AGENTS_NUM, ACTUATOR_NUM))
check("next_state_buffer.shape", tuple(buf.next_state_buffer.shape), (MAX_STEP, AGENTS_NUM, RESIDUAL_STATE_DIM))
check("reward_buffer.shape", tuple(buf.reward_buffer.shape), (MAX_STEP, AGENTS_NUM, 1))
check("over_buffer.shape", tuple(buf.over_buffer.shape), (MAX_STEP, AGENTS_NUM, 1))

# Store and retrieve
action = torch.randn(AGENTS_NUM, ACTUATOR_NUM)
reward = torch.randn(AGENTS_NUM, 1)
over = torch.zeros(AGENTS_NUM, 1)
buf.store_state(residual_state, 0)
buf.store_action(action, 0)
buf.store_next_state(residual_state, 0)
buf.store_reward(reward, 0)
buf.store_over(over, 0)
check("stored state matches", torch.allclose(buf.state_buffer[0], residual_state), True)

# ---- 7. External force label shape ----
print("\n=== 7. External force label shapes ===")
external_force_label = torch.zeros(AGENTS_NUM, LATENT_DIM)
push_time_remaining = torch.zeros(AGENTS_NUM, 1)
push_force_xy = torch.zeros(AGENTS_NUM, 2)

# Simulate push start
start_push = torch.zeros(AGENTS_NUM, 1, dtype=torch.bool)
start_push[0:3] = True
push_force_xy[start_push.flatten()] = 120.0 * (2 * torch.rand(3, 2) - 1)
push_time_remaining[start_push] = 0.12
active_push = push_time_remaining > 0
external_force_label[:, 0:2] = push_force_xy * active_push.float()
check("external_force_label.shape", tuple(external_force_label.shape), (AGENTS_NUM, LATENT_DIM))
check("push_force_xy.shape", tuple(push_force_xy.shape), (AGENTS_NUM, 2))
check("force applied to pushed agents", (external_force_label[0:3, 0:2] != 0).all().item(), True)
check("no force on non-pushed agents", (external_force_label[3:, :] == 0).all().item(), True)

# ---- 8. Estimator state slicing ----
print("\n=== 8. Estimator state slicing ===")
full_state = torch.randn(AGENTS_NUM, BASE_STATE_DIM)
estimator_obs = torch.concatenate(
    (
        full_state[:, 0:8],    # joint_pos
        full_state[:, 8:16],   # joint_vel
        full_state[:, 16:19],  # body_ori
        full_state[:, 19:22],  # angular_vel
        full_state[:, 24:32],  # prev_action + vel_cmd
        full_state[:, 32:33],  # vel_cmd (last dim before depth)
    ),
    dim=1,
)
check("estimator_obs.shape", tuple(estimator_obs.shape), (AGENTS_NUM, OBS_DIM))

# Verify correct data is extracted
check("joint_pos matches", torch.allclose(estimator_obs[:, 0:8], full_state[:, 0:8]), True)
check("joint_vel matches", torch.allclose(estimator_obs[:, 8:16], full_state[:, 8:16]), True)
check("body_ori matches", torch.allclose(estimator_obs[:, 16:19], full_state[:, 16:19]), True)
check("ang_vel matches", torch.allclose(estimator_obs[:, 19:22], full_state[:, 19:22]), True)
check("action+cmd matches", torch.allclose(estimator_obs[:, 22:31], full_state[:, 24:33]), True)

# ---- Summary ----
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
else:
    print("All shape checks passed!")
