"""Diagnose random push force-label stability.

Run with Isaac Sim:
    & "E:\\IsaacSim-5.1.0\\python.bat" tools\\force_label_diagnostic.py
"""

import argparse

import torch

from SF_TRON_Ext.utils.Config import Config


def parse_args():
    parser = argparse.ArgumentParser(description="Check whether push force labels remain stable during a pulse.")
    parser.add_argument("--agents", type=int, default=16)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--terrain-rows", type=int, default=3)
    parser.add_argument("--terrain-cols", type=int, default=3)
    parser.add_argument("--watch-agent", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    Config.Env_Config.EnvParam.agents_num = args.agents
    Config.Env_Config.EnvParam.agents_num_in_play = args.agents
    Config.Env_Config.EnvParam.headless = True
    Config.Env_Config.EnvParam.train = True
    Config.Env_Config.EnvParam.terrain_num_rows = args.terrain_rows
    Config.Env_Config.EnvParam.terrain_num_cols = args.terrain_cols
    Config.Robot_Config.DisturbanceCfg.enable_push = True

    from SF_TRON_Ext.utils.Config.Config import Env_Config, PPO_Config, Robot_Config
    from SF_TRON_Ext.utils.Env.Tron_Env import Tron_Env

    env = Tron_Env(Env_Config, Robot_Config, PPO_Config)
    env.prim_initialization(reset_all=True)

    active_force_by_agent = {}
    active_steps = 0
    unstable_events = []
    action = torch.zeros((env.agents_num, env.actuator_num), device=env.device)

    print("=== Force Label Diagnostic ===")
    print(f"agents={args.agents}, steps={args.steps}, watch_agent={args.watch_agent}")

    for step in range(args.steps):
        env.update_world(action)
        labels = env.external_force_label.detach().clone()
        remaining = env.push_time_remaining.detach().clone()
        force_xy = env.push_force_xy.detach().clone()
        active = (remaining[:, 0] > 0) & (labels[:, 0:2].abs().sum(dim=1) > 0)
        active_steps += int(active.sum().item())

        for agent_id in torch.nonzero(active, as_tuple=False).flatten().tolist():
            label_xy = labels[agent_id, 0:2]
            previous = active_force_by_agent.get(agent_id)
            if previous is None or remaining[agent_id, 0].item() >= Robot_Config.DisturbanceCfg.push_duration - env.dt:
                active_force_by_agent[agent_id] = label_xy
            elif not torch.allclose(previous, label_xy, atol=1e-5, rtol=1e-5):
                unstable_events.append((step, agent_id, previous.cpu().tolist(), label_xy.cpu().tolist()))
                active_force_by_agent[agent_id] = label_xy

        inactive_ids = torch.nonzero(~active, as_tuple=False).flatten().tolist()
        for agent_id in inactive_ids:
            active_force_by_agent.pop(agent_id, None)

        if step < 20 or active[args.watch_agent].item():
            label = labels[args.watch_agent].cpu().tolist()
            push = force_xy[args.watch_agent].cpu().tolist()
            time_left = remaining[args.watch_agent, 0].item()
            print(
                f"step={step:03d} agent={args.watch_agent} "
                f"time_left={time_left:.4f} label={label} push_force_xy={push}"
            )

    if unstable_events:
        print("FAIL: force label changed during active push pulse")
        for event in unstable_events[:10]:
            step, agent_id, previous, current = event
            print(f"  step={step} agent={agent_id} previous={previous} current={current}")
        raise RuntimeError("unstable push force labels detected")

    print(f"active_agent_steps={active_steps}")
    print("PASS: active push labels stayed stable within each pulse")


if __name__ == "__main__":
    main()
