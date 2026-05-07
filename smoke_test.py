"""Smoke test for the estimator integration.
Run with Isaac Sim: & "E:\IsaacSim-5.1.0\python.bat" smoke_test.py

Verifies:
- Completes at least one episode without crash
- No shape mismatches
- PPO buffer stores extended state correctly
- Estimator loss is computable and non-NaN
"""

import torch
from pathlib import Path

# Override config BEFORE importing anything that reads it
from SF_TRON_Ext.utils.Config import Config

SMOKE_OUTPUT_DIR = Path("artifacts/smoke_test")
SMOKE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Config.Env_Config.EnvParam.agents_num = 10
Config.Env_Config.EnvParam.agents_num_in_play = 10
Config.Env_Config.EnvParam.headless = True
Config.Env_Config.EnvParam.train = True
Config.Env_Config.EnvParam.terrain_num_rows = 3
Config.Env_Config.EnvParam.terrain_num_cols = 3
Config.PPO_Config.PPOParam.maximum_step = 10
Config.PPO_Config.PPOParam.episode = 3
Config.PPO_Config.PPOParam.batch_size = 500
Config.PPO_Config.EstimatorParam.model_path = str(SMOKE_OUTPUT_DIR / "estimator.pth")

from SF_TRON_Ext.utils.Env.Tron_Env import Tron_Env
from SF_TRON_Ext.utils.PPO.Actor_Critic import Actor_Critic
from SF_TRON_Ext.utils.Estimator.Disturbance_Estimator import Disturbance_Estimator
from SF_TRON_Ext.utils.Config.Config import *

AGENTS = Config.Env_Config.EnvParam.agents_num
BASE_STATE_DIM = PPO_Config.CriticParam.base_state_dim
RESIDUAL_STATE_DIM = PPO_Config.CriticParam.residual_state_dim
HISTORY_LEN = PPO_Config.EstimatorParam.history_len
OBS_DIM = PPO_Config.EstimatorParam.obs_dim
LATENT_DIM = PPO_Config.EstimatorParam.latent_dim


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if not condition:
        raise AssertionError(f"Shape check failed: {name}")


print("=== Smoke Test ===\n")


def patch_ac_save_paths(ac, output_dir):
    output_dir = Path(output_dir)

    def save_best_model():
        torch.save(ac.actor.state_dict(), output_dir / f"actor{ac.index}{ac.model_suffix}.pth")
        torch.save(ac.critic.state_dict(), output_dir / f"critic{ac.index}{ac.model_suffix}.pth")

    def save_each_epi_model():
        torch.save(ac.actor.state_dict(), output_dir / f"actor{ac.index}{ac.model_suffix}_f.pth")
        torch.save(ac.critic.state_dict(), output_dir / f"critic{ac.index}{ac.model_suffix}_f.pth")

    def save_checkpoint(episode):
        torch.save(ac.actor.state_dict(), output_dir / f"actor{ac.index}{ac.model_suffix}_ckpt{episode}.pth")
        torch.save(ac.critic.state_dict(), output_dir / f"critic{ac.index}{ac.model_suffix}_ckpt{episode}.pth")

    ac.save_best_model = save_best_model
    ac.save_each_epi_model = save_each_epi_model
    ac.save_checkpoint = save_checkpoint

# --- Step 1: Create components ---
print("[1] Creating components...")
AC_trained = Actor_Critic(PPO_Config, Env_Config, index=0)
AC = Actor_Critic(PPO_Config, Env_Config, index=1)
patch_ac_save_paths(AC, SMOKE_OUTPUT_DIR)
estimator = Disturbance_Estimator(PPO_Config.EstimatorParam, Env_Config.EnvParam.device)
env = Tron_Env(Env_Config, Robot_Config, PPO_Config)
env.prim_initialization(reset_all=True)
print("  Components created.\n")

# --- Step 2: Run one episode ---
print("[2] Running smoke episode...")
env.resample_command(activate=False)

for step in range(Config.PPO_Config.PPOParam.maximum_step):
    state = env.get_current_observations()
    check(f"step {step}: state.shape", tuple(state.shape) == (AGENTS, BASE_STATE_DIM))

    history = env.update_estimator_history(state)
    check(f"step {step}: history.shape", tuple(history.shape) == (AGENTS, HISTORY_LEN, OBS_DIM))

    f_hat = estimator.predict(history)
    check(f"step {step}: f_hat.shape", tuple(f_hat.shape) == (AGENTS, LATENT_DIM))
    check(f"step {step}: f_hat not NaN", not torch.isnan(f_hat).any().item())

    residual_state = env.augment_state_with_estimate(state, f_hat.detach())
    check(f"step {step}: residual_state.shape", tuple(residual_state.shape) == (AGENTS, RESIDUAL_STATE_DIM))

    state_trained = state.clone()
    state_trained[:, 33:] = 0

    action1, scaled_action1 = AC_trained.sample_action(state_trained, deterministic=True)
    action2, scaled_action2 = AC.sample_action(residual_state, deterministic=False)

    env.update_world(action=scaled_action1 * 0.25 + scaled_action2 * 0.75)

    estimator_loss, _ = estimator.update(history, env.external_force_label.clone())
    check(f"step {step}: estimator_loss not NaN", not torch.isnan(torch.tensor(estimator_loss)))

    next_state = env.get_next_observations()
    check(f"step {step}: next_state.shape", tuple(next_state.shape) == (AGENTS, BASE_STATE_DIM))

    next_residual_state = env.augment_state_with_estimate(next_state, f_hat.detach())
    check(f"step {step}: next_residual_state.shape", tuple(next_residual_state.shape) == (AGENTS, RESIDUAL_STATE_DIM))

    reward, over, extra_over = env.compute_reward()
    check(f"step {step}: reward.shape", tuple(reward.shape) == (AGENTS, 1))

    AC.store_experience(residual_state, action2, next_residual_state, reward, over, step)

    over += extra_over
    env.prim_initialization(torch.nonzero(over.flatten()).flatten())

print("  Episode completed.\n")

# --- Step 3: Verify buffer ---
print("[3] Checking PPO buffer...")
buf = AC.Buffer
check("buffer state shape", tuple(buf.state_buffer.shape) == (Config.PPO_Config.PPOParam.maximum_step, AGENTS, RESIDUAL_STATE_DIM))
check("buffer action shape", tuple(buf.action_buffer.shape) == (Config.PPO_Config.PPOParam.maximum_step, AGENTS, 8))
check("buffer next_state shape", tuple(buf.next_state_buffer.shape) == (Config.PPO_Config.PPOParam.maximum_step, AGENTS, RESIDUAL_STATE_DIM))
check("buffer reward shape", tuple(buf.reward_buffer.shape) == (Config.PPO_Config.PPOParam.maximum_step, AGENTS, 1))
print()

# --- Step 4: Test PPO update ---
print("[4] Testing PPO update...")
AC.update()
print("  PPO update completed.\n")

# --- Step 5: Test save/load ---
print("[5] Testing save/load...")
estimator.save_model()
estimator.load_model()
AC.save_checkpoint(0)
print("  Save/load completed.\n")

print("=== All smoke tests passed! ===")
(SMOKE_OUTPUT_DIR / "success.txt").write_text("passed\n", encoding="utf-8")
