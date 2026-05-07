# Formal Evaluation Plan

## Summary

This document defines the next formal evaluation stage for the SF_TRON estimator integration. Current smoke and sanity checks prove that the engineering path is runnable; they do not prove that the estimator improves walking performance. Formal evaluation must compare the same saved model set under clearly named modes and report stable metrics before any performance claim is made.

## Evaluation Modes

| Mode | Policy input | Meaning |
|---|---:|---|
| `Legacy231` | 231 | Old `actor1.pth` residual policy without estimator input |
| `Baseline234` | 234 | Current estimator-input residual policy with `f_hat=0` |
| `Estimator` | 234 | Current estimator-input residual policy with predicted `f_hat` |

Do not mix `Legacy231` with `Baseline234`. `Baseline234` is the fair ablation for the current estimator-input policy; `Legacy231` is a legacy reference point.

## Minimum Formal Run

Use this as the first formal evaluation after smoke tests:

```powershell
$env:PYTHONEXE="E:\IsaacSim-5.1.0\kit\python\python.exe"
$env:PYTHONPATH="E:\SF_TRON_Ext-estimator;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_assets;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_tasks;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_rl;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_mimic"
$env:WARP_CACHE_PATH="E:\SF_TRON_Ext-estimator\artifacts\warp_cache"
& "E:\IsaacSim-5.1.0\python.bat" evaluate_comparison.py 5 --agents 100 --steps 50 --terrain-rows 3 --terrain-cols 3 --include-legacy
```

If this run is stable, expand to more episodes and then multiple seeds or repeated runs. Keep Isaac Sim commands outside the Codex sandbox because Isaac/Kit/GPU caches are written outside the workspace.

## Metrics

Report these metrics for each mode:

- fall rate
- average reward per step
- average episode length
- termination reward
- velocity tracking reward
- force MSE during push
- force MSE with no push

Record the exact command, commit hash, model source, terrain rows/cols, agents, steps, episodes, and any warnings that affect interpretation.

## Interpretation Rules

- Treat smoke tests and sanity checks as engineering stability evidence only.
- Claim estimator performance improvement only if `Estimator` consistently improves over `Baseline234` across formal runs.
- Use `Legacy231` as historical context, not as the only baseline.
- If results are mixed or unstable, write: “The estimator integration is runnable, but this run does not show a stable performance improvement.”

## Current Defaults

- Runtime assets come from root `model/...`.
- `SF_TRON_Ext/model/` remains ignored duplicate candidate data.
- Deprecated `set_external_force_and_torque` warning remains technical debt and is not part of this formal evaluation.
