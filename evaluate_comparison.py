"""Baseline vs Estimator comparison evaluation.
Run with Isaac Sim: & "E:\IsaacSim-5.1.0\python.bat" evaluate_comparison.py

Compares:
- baseline: estimator-input residual policy with f_hat = 0
- estimator: residual policy with f_hat input

This does not compare against the legacy 231-dim actor1.pth residual policy.

Metrics:
- Fall rate (termination %)
- Average episode length
- Average reward
- Velocity tracking reward
- Termination reward
- Force MSE during push vs no-push
"""

import torch
import numpy as np
import argparse

from SF_TRON_Ext.utils.Config.Config import *
from SF_TRON_Ext.utils.Env.Tron_Env import Tron_Env
from SF_TRON_Ext.utils.PPO.Actor_Critic import Actor_Critic
from SF_TRON_Ext.utils.Estimator.Disturbance_Estimator import Disturbance_Estimator


def evaluate(mode, env, AC_trained, AC, estimator=None, num_episodes=20):
    """Run evaluation episodes and collect metrics.

    Args:
        mode: 'baseline' (no estimator) or 'estimator' (with f_hat)
        num_episodes: number of episodes to evaluate
    """
    assert mode in ("baseline", "estimator"), f"Unknown mode: {mode}"

    env.prim_initialization(reset_all=True)

    maximum_step = PPO_Config.PPOParam.maximum_step
    agents_num = Env_Config.EnvParam.agents_num_in_play

    # Metrics accumulators
    total_falls = 0
    total_steps = 0
    episode_lengths = []
    reward_sum = 0
    vel_tracking_sum = 0
    termination_sum = 0
    force_mse_push = []
    force_mse_no_push = []

    for epi in range(num_episodes):
        env.resample_command(activate=False)
        ep_falls = 0
        ep_steps = 0

        for step in range(maximum_step):
            state = env.get_current_observations()
            history = env.update_estimator_history(state)

            if mode == "estimator":
                with torch.no_grad():
                    f_hat = estimator.predict(history)
                residual_state = env.augment_state_with_estimate(state, f_hat)
            else:
                f_hat = torch.zeros(env.agents_num, PPO_Config.EstimatorParam.latent_dim, device=env.device)
                residual_state = env.augment_state_with_estimate(state, f_hat)

            state_trained = state.clone()
            state_trained[:, 33:] = 0

            action1, scaled_action1 = AC_trained.sample_action(state_trained, deterministic=True)
            action2, scaled_action2 = AC.sample_action(residual_state, deterministic=True)

            env.update_world(action=scaled_action1 * 0.25 + scaled_action2 * 0.75)

            # Compute force MSE if estimator is active
            if mode == "estimator":
                with torch.no_grad():
                    f_pred = estimator.predict(history)
                mse = ((f_pred - env.external_force_label) ** 2).mean().item()
                is_pushing = (env.push_time_remaining > 0).any().item()
                if is_pushing:
                    force_mse_push.append(mse)
                else:
                    force_mse_no_push.append(mse)

            next_state = env.get_next_observations()
            next_residual_state = env.augment_state_with_estimate(
                next_state, f_hat if mode == "estimator" else torch.zeros_like(f_hat)
            )

            reward, over, extra_over = env.compute_reward()
            reward_sum += reward.mean().item()

            # Track falls
            falls = over.sum().item()
            ep_falls += falls
            ep_steps += agents_num

            over_all = over + extra_over
            env.prim_initialization(torch.nonzero(over_all.flatten()).flatten())

        total_falls += ep_falls
        total_steps += ep_steps
        episode_lengths.append(ep_steps / max(ep_falls, 1))
        vel_tracking_sum += env.vel_tracking_reward_sum
        termination_sum += env.Termination_reward_sum
        env.print_reward_sum()

    # Compute averages
    fall_rate = total_falls / max(total_steps, 1)
    avg_reward = reward_sum / (num_episodes * maximum_step)
    avg_vel_tracking = vel_tracking_sum / num_episodes
    avg_termination = termination_sum / num_episodes
    avg_ep_length = np.mean(episode_lengths)
    avg_force_mse_push = np.mean(force_mse_push) if force_mse_push else float('nan')
    avg_force_mse_no_push = np.mean(force_mse_no_push) if force_mse_no_push else float('nan')

    return {
        "mode": mode,
        "fall_rate": fall_rate,
        "avg_episode_length": avg_ep_length,
        "avg_reward": avg_reward,
        "avg_vel_tracking": avg_vel_tracking,
        "avg_termination": avg_termination,
        "force_mse_push": avg_force_mse_push,
        "force_mse_no_push": avg_force_mse_no_push,
    }


def print_comparison(baseline, estimator_result):
    """Print a comparison table."""
    print("\n" + "=" * 60)
    print("COMPARISON: Baseline vs Estimator")
    print("=" * 60)
    metrics = [
        ("Fall Rate", "fall_rate", ".4f"),
        ("Avg Episode Length", "avg_episode_length", ".1f"),
        ("Avg Reward (per step)", "avg_reward", ".4f"),
        ("Velocity Tracking", "avg_vel_tracking", ".4f"),
        ("Termination Reward", "avg_termination", ".4f"),
        ("Force MSE (push)", "force_mse_push", ".4f"),
        ("Force MSE (no push)", "force_mse_no_push", ".4f"),
    ]
    print(f"{'Metric':<25} {'Baseline':>12} {'Estimator':>12} {'Delta':>10}")
    print("-" * 60)
    for label, key, fmt in metrics:
        b = baseline[key]
        e = estimator_result[key]
        delta = e - b
        print(f"{label:<25} {b:>12{fmt}} {e:>12{fmt}} {delta:>+10{fmt}}")
    print("=" * 60)

    # Success criteria check
    print("\nSuccess Criteria:")
    print(f"  [1] No estimator: fall rate = {baseline['fall_rate']:.4f}")
    print(f"  [2] With estimator: fall rate = {estimator_result['fall_rate']:.4f}")
    if estimator_result['fall_rate'] <= baseline['fall_rate']:
        print("      -> PASS: estimator reduces or maintains fall rate")
    else:
        print("      -> WARN: estimator increases fall rate")

    if not np.isnan(estimator_result['force_mse_push']):
        print(f"  [3] Force MSE (push) = {estimator_result['force_mse_push']:.4f}")
        print("      -> (check if decreasing during training)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare f_hat=0 baseline and estimator-input policy.")
    parser.add_argument("episodes", nargs="?", type=int, default=20)
    parser.add_argument("--agents", type=int, default=None)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--terrain-rows", type=int, default=None)
    parser.add_argument("--terrain-cols", type=int, default=None)
    args = parser.parse_args()

    if args.agents is not None:
        Env_Config.EnvParam.agents_num = args.agents
        Env_Config.EnvParam.agents_num_in_play = args.agents
    if args.steps is not None:
        PPO_Config.PPOParam.maximum_step = args.steps
    if args.terrain_rows is not None:
        Env_Config.EnvParam.terrain_num_rows = args.terrain_rows
    if args.terrain_cols is not None:
        Env_Config.EnvParam.terrain_num_cols = args.terrain_cols

    num_episodes = args.episodes

    print("Baseline definition: f_hat=0 with the 234-dim estimator residual policy input.")
    print("Legacy actor1.pth is not loaded because it expects the old 231-dim input.")
    print(f"Running {num_episodes} evaluation episodes per mode...\n")

    AC_trained = Actor_Critic(PPO_Config, Env_Config, index=0)
    AC_trained.load_best_model()

    AC = Actor_Critic(PPO_Config, Env_Config, index=1)
    AC.load_best_model()

    estimator = Disturbance_Estimator(PPO_Config.EstimatorParam, Env_Config.EnvParam.device)
    estimator.load_model()
    estimator.network.eval()

    env = Tron_Env(Env_Config, Robot_Config, PPO_Config)

    print("--- Baseline (no estimator) ---")
    baseline = evaluate("baseline", env, AC_trained, AC, estimator=None, num_episodes=num_episodes)

    print("\n--- Estimator (with f_hat) ---")
    est = evaluate("estimator", env, AC_trained, AC, estimator=estimator, num_episodes=num_episodes)

    print_comparison(baseline, est)
