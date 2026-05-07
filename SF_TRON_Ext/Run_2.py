from SF_TRON_Ext.utils.Env.Tron_Env import Tron_Env
from SF_TRON_Ext.utils.PPO.Actor_Critic import Actor_Critic
from SF_TRON_Ext.utils.Config.Config import *
from SF_TRON_Ext.utils.Estimator.Disturbance_Estimator import Disturbance_Estimator

maximum_step = PPO_Config.PPOParam.maximum_step
episode = PPO_Config.PPOParam.episode
train = Env_Config.EnvParam.train
AC_trained = Actor_Critic(PPO_Config, Env_Config,index=0)
AC_trained.load_best_model()
AC = Actor_Critic(PPO_Config, Env_Config,index=1)
estimator = Disturbance_Estimator(PPO_Config.EstimatorParam, Env_Config.EnvParam.device)
if not train:
    AC.load_best_model()
    estimator.load_model()
env = Tron_Env(Env_Config, Robot_Config, PPO_Config)
import torch

env.prim_initialization(reset_all=True)
for epi in range(episode):
    print(f"===================episode: {epi}===================")
    env.resample_command(activate = False)
    for step in range(maximum_step):
        """获取当前状态"""
        state = env.get_current_observations()
        history = env.update_estimator_history(state)
        f_hat = estimator.predict(history)
        residual_state = env.augment_state_with_estimate(state, f_hat.detach())

        state_trained = state.clone()
        state_trained[:,33:] = 0

        """做动作"""

        action1, scaled_action1 = AC_trained.sample_action(state_trained,deterministic=True)
        action2, scaled_action2 = AC.sample_action(residual_state,deterministic=not train)

        """更新环境"""
        env.update_world(action=scaled_action1*0.25+scaled_action2*0.75)
        if train:
            estimator_loss, _ = estimator.update(history, env.external_force_label.clone())

        """获取下一个状态"""

        next_state = env.get_next_observations()
        next_residual_state = env.augment_state_with_estimate(next_state, f_hat.detach())

        """计算奖励 判断是否结束"""

        reward, over, extra_over = env.compute_reward()

        """存储经验"""
        if train:
            AC.store_experience(residual_state,
                                action2,
                                next_residual_state,
                                reward,
                                over,
                                step)

        """重置挂掉的机器人"""
        over += extra_over
        env.prim_initialization(torch.nonzero(over.flatten()).flatten())

    """每个回合结束后训练一次"""
    if train:
        AC.update()
        estimator.save_model()
        if epi % 100 == 0 and epi > 0:
            AC.save_checkpoint(epi)
            estimator.save_checkpoint(epi)
            print(f"Checkpoint saved at episode {epi}")
        print(f"Estimator Loss: {estimator_loss:.6f}")
        env.print_reward_sum()
