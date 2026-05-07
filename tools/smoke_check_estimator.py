import torch

from SF_TRON_Ext.utils.Config.Config import Env_Config, PPO_Config
from SF_TRON_Ext.utils.Estimator.Disturbance_Estimator import Disturbance_Estimator
from SF_TRON_Ext.utils.PPO.Actor_Critic import Actor_Critic


def main():
    device = Env_Config.EnvParam.device if torch.cuda.is_available() else "cpu"
    batch_size = 4
    Env_Config.EnvParam.device = device
    Env_Config.EnvParam.agents_num = batch_size

    estimator = Disturbance_Estimator(PPO_Config.EstimatorParam, device)
    history = torch.zeros(
        batch_size,
        PPO_Config.EstimatorParam.history_len,
        PPO_Config.EstimatorParam.obs_dim,
        device=device,
    )
    estimate = estimator.predict(history)

    base_ac = Actor_Critic(PPO_Config, Env_Config, index=0)
    residual_ac = Actor_Critic(PPO_Config, Env_Config, index=1)
    estimator_enabled = PPO_Config.EstimatorParam.enabled
    PPO_Config.EstimatorParam.enabled = False
    try:
        legacy_residual_ac = Actor_Critic(PPO_Config, Env_Config, index=1)
    finally:
        PPO_Config.EstimatorParam.enabled = estimator_enabled

    assert estimate.shape == (batch_size, PPO_Config.EstimatorParam.latent_dim)
    assert base_ac.state_dim == PPO_Config.CriticParam.base_state_dim
    assert residual_ac.state_dim == PPO_Config.CriticParam.residual_state_dim
    assert legacy_residual_ac.state_dim == PPO_Config.CriticParam.base_state_dim

    print("estimator output:", tuple(estimate.shape))
    print("base policy state_dim:", base_ac.state_dim)
    print("residual policy state_dim:", residual_ac.state_dim)
    print("legacy residual policy state_dim:", legacy_residual_ac.state_dim)
    print("smoke check passed")


if __name__ == "__main__":
    main()
