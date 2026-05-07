# Formal Evaluation Results

## Run 1: Minimum Formal Run

Date: 2026-05-07

Commit: `6957518 Update progress after formal plan commit`

Purpose: First formal evaluation record after smoke and sanity checks. This run checks the three named evaluation modes under the same command and does not by itself prove performance improvement.

Command:

```powershell
$env:PYTHONEXE="E:\IsaacSim-5.1.0\kit\python\python.exe"
$env:PYTHONPATH="E:\SF_TRON_Ext-estimator;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_assets;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_tasks;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_rl;E:\SF_TRON_Ext-estimator\isaaclab_repo\source\isaaclab_mimic"
$env:WARP_CACHE_PATH="E:\SF_TRON_Ext-estimator\artifacts\warp_cache"
& "E:\IsaacSim-5.1.0\python.bat" evaluate_comparison.py 5 --agents 100 --steps 50 --terrain-rows 3 --terrain-cols 3 --include-legacy
```

Settings:

- episodes: 5
- agents: 100
- steps: 50
- terrain rows/cols: 3 x 3
- runtime assets: root `model/...`

Results:

| Metric | Legacy231 | Baseline234 | Estimator | Est-B |
|---|---:|---:|---:|---:|
| Fall Rate | 0.0103 | 0.0276 | 0.0288 | +0.0013 |
| Avg Episode Length | 112.0 | 37.3 | 35.1 | -2.1 |
| Avg Reward per Step | 0.7814 | 0.1154 | 0.1017 | -0.0137 |
| Velocity Tracking | 0.2804 | 0.1695 | 0.1758 | +0.0063 |
| Termination Reward | -0.1028 | -0.2756 | -0.2884 | -0.0128 |
| Force MSE push | NaN | NaN | 302.5451 | NaN |
| Force MSE no push | NaN | NaN | 0.0012 | NaN |

Warnings:

- `set_external_force_and_torque` is deprecated; still not treated as a blocker for this run.
- `enable_external_forces_every_iteration=False` warning remains present.
- Isaac/Kit shutdown warnings were printed after evaluation, but the command exited successfully.

Interpretation:

- The minimum formal run completed successfully and the three mode labels remained clear.
- This run does not show estimator performance improvement over `Baseline234`: fall rate and average reward were slightly worse for `Estimator`.
- Current conclusion should be: the estimator integration is runnable, but this run does not show a stable performance improvement.

Next:

- Repeat formal evaluation with more episodes and/or repeated seeds before making a final performance claim.
- Keep reporting `Legacy231`, `Baseline234`, and `Estimator` separately.
