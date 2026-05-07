# Commit Boundary Notes

This repository is still mostly untracked. Use this file as the staging guide
before creating the first meaningful commit.

## Include

- Source code under `SF_TRON_Ext/`.
- Root-level helper scripts: `run_tests.bat`, `check_env.py`, `test_shapes.py`,
  `smoke_test.py`, `evaluate_comparison.py`, and `tools/*.py`.
- Project documentation: `README.md`, `PROJECT_DESCRIPTION.md`,
  `SESSION_HANDOFF.md`, `CODEX_HANDOFF.md`, `AGENTS.md`, and `CLAUDE.md`.
- Root-level `model/` assets required by the current runtime path.

## Exclude

- `artifacts/`
- `__pycache__/` and `*.py[cod]`
- `training_log.csv`
- `isaaclab_repo/` because it is a local junction to `E:\SF_TRON_Ext-main\isaaclab`
- `SF_TRON_Ext/model/` because root `model/` is the selected runtime asset source
- Test checkpoint files such as `model/NN_Model/*_ckpt*.pth`
- Temporary or diagnostic weights matching `*_tmp.pth`, `*_debug.pth`,
  `*_sanity*.pth`, or `*_smoke*.pth`

## Model Directory Status

The selected runtime asset source is root-level `model/...`. Keep
`Env_Config.EnvParam.file_path = "model/Robot_Model/SF_TRON1A.usd"` and
`PPO_Config.EstimatorParam.model_path = "model/NN_Model/estimator.pth"`.

Comparison between root `model/` and `SF_TRON_Ext/model/`:

- 31 files are byte-identical duplicates.
- 4 files exist in both locations but differ:
  - `NN_Model/actor0.pth`
  - `NN_Model/actor0_f.pth`
  - `NN_Model/critic0.pth`
  - `NN_Model/critic0_f.pth`
- 7 estimator-related files exist only in root `model/NN_Model/`:
  - `actor1_est.pth`
  - `actor1_est_ckpt0.pth`
  - `actor1_est_f.pth`
  - `critic1_est.pth`
  - `critic1_est_ckpt0.pth`
  - `critic1_est_f.pth`
  - `estimator.pth`
- No files exist only in `SF_TRON_Ext/model/`.

Do not delete `SF_TRON_Ext/model/` blindly. It is ignored for now as duplicate
candidate data, while root `model/` remains the source to stage and review.

Root `model/NN_Model/*_ckpt*.pth` files are test checkpoints and should remain
ignored. The estimator runtime files to review for staging are:

- `actor1_est.pth`
- `actor1_est_f.pth`
- `critic1_est.pth`
- `critic1_est_f.pth`
- `estimator.pth`

The old base/residual policy files and robot/deploy assets under root `model/`
are also part of the selected runtime asset source.

## Isaac Sim Verification Note

Isaac Sim tests must run outside the Codex sandbox because Isaac/Kit writes GPU
and application caches under the Isaac Sim installation and user cache
directories. Inside the sandbox, these tests can hang or fail on cache writes.
