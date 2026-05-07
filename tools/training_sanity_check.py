"""Short training sanity check for the estimator residual policy.

Run with Isaac Sim:
    & "E:\\IsaacSim-5.1.0\\python.bat" tools\\training_sanity_check.py

This is a stability check, not a performance benchmark.
"""

import argparse
import math
import os
from pathlib import Path

import torch

from SF_TRON_Ext.utils.Config import Config


def parse_args():
    parser = argparse.ArgumentParser(description="Run a short estimator training sanity check.")
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--terrain-rows", type=int, default=3)
    parser.add_argument("--terrain-cols", type=int, default=3)
    parser.add_argument("--output-dir", default="artifacts/sanity_check")
    return parser.parse_args()


def configure(args):
    Config.Env_Config.EnvParam.agents_num = args.agents
    Config.Env_Config.EnvParam.agents_num_in_play = args.agents
    Config.Env_Config.EnvParam.headless = True
    Config.Env_Config.EnvParam.train = True
    Config.Env_Config.EnvParam.terrain_num_rows = args.terrain_rows
    Config.Env_Config.EnvParam.terrain_num_cols = args.terrain_cols
    Config.PPO_Config.PPOParam.maximum_step = args.steps
    Config.PPO_Config.PPOParam.episode = args.episodes
    Config.PPO_Config.PPOParam.batch_size = min(20000, args.agents * args.steps)
    Config.PPO_Config.EstimatorParam.model_path = str(Path(args.output_dir) / "estimator.pth")


def patch_ac_save_paths(ac, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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


def main():
    args = parse_args()
    configure(args)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    from SF_TRON_Ext.utils.Config.Config import Env_Config, PPO_Config, Robot_Config
    from SF_TRON_Ext.utils.Env.Tron_Env import Tron_Env
    from SF_TRON_Ext.utils.Estimator.Disturbance_Estimator import Disturbance_Estimator
    from SF_TRON_Ext.utils.PPO.Actor_Critic import Actor_Critic

    base_ac = Actor_Critic(PPO_Config, Env_Config, index=0)
    base_ac.load_best_model()
    residual_ac = Actor_Critic(PPO_Config, Env_Config, index=1)
    patch_ac_save_paths(residual_ac, args.output_dir)
    estimator = Disturbance_Estimator(PPO_Config.EstimatorParam, Env_Config.EnvParam.device)
    env = Tron_Env(Env_Config, Robot_Config, PPO_Config)
    env.prim_initialization(reset_all=True)

    reward_means = []
    estimator_losses = []
    fall_rates = []

    print("=== Training Sanity Check ===")
    print(f"agents={args.agents}, steps={args.steps}, episodes={args.episodes}")
    print(f"outputs={os.path.abspath(args.output_dir)}")

    for epi in range(args.episodes):
        env.resample_command(activate=False)
        episode_rewards = []
        episode_falls = 0

        for step in range(args.steps):
            state = env.get_current_observations()
            history = env.update_estimator_history(state)
            f_hat = estimator.predict(history)
            residual_state = env.augment_state_with_estimate(state, f_hat.detach())

            state_trained = state.clone()
            state_trained[:, 33:] = 0

            _, scaled_action1 = base_ac.sample_action(state_trained, deterministic=True)
            action2, scaled_action2 = residual_ac.sample_action(residual_state, deterministic=False)

            env.update_world(action=scaled_action1 * 0.25 + scaled_action2 * 0.75)
            estimator_loss, _ = estimator.update(history, env.external_force_label.clone())

            next_state = env.get_next_observations()
            next_residual_state = env.augment_state_with_estimate(next_state, f_hat.detach())
            reward, over, extra_over = env.compute_reward()

            if not math.isfinite(float(estimator_loss)):
                raise RuntimeError(f"Estimator loss became non-finite at episode {epi}, step {step}")
            if torch.isnan(reward).any().item():
                raise RuntimeError(f"Reward became NaN at episode {epi}, step {step}")

            residual_ac.store_experience(residual_state, action2, next_residual_state, reward, over, step)
            episode_rewards.append(reward.mean().item())
            episode_falls += int(over.sum().item())

            over_all = over + extra_over
            env.prim_initialization(torch.nonzero(over_all.flatten()).flatten())

        residual_ac.update()
        estimator.save_model()
        residual_ac.save_checkpoint(epi)
        estimator.save_checkpoint(epi)

        reward_mean = sum(episode_rewards) / max(len(episode_rewards), 1)
        fall_rate = episode_falls / max(args.agents * args.steps, 1)
        reward_means.append(reward_mean)
        estimator_losses.append(estimator_loss)
        fall_rates.append(fall_rate)
        print(
            f"episode={epi} reward_mean={reward_mean:.6f} "
            f"estimator_loss={estimator_loss:.6f} fall_rate={fall_rate:.6f}"
        )

    print("=== Sanity Summary ===")
    print(f"reward_mean_avg={sum(reward_means) / len(reward_means):.6f}")
    print(f"estimator_loss_last={estimator_losses[-1]:.6f}")
    print(f"fall_rate_avg={sum(fall_rates) / len(fall_rates):.6f}")
    print("PASS: short training sanity check completed")


if __name__ == "__main__":
    main()
