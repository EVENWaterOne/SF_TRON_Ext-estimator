class Env_Config:
    class EnvParam:  # 训练环境的参数
        agents_num = 4000
        agents_num_in_play = 10
        file_path = "model/Robot_Model/SF_TRON1A.usd"  # abs path, not relative path
        dt = 0.02
        sub_step = 4
        friction_coef = 1
        device = 'cuda'
        backend = "torch"
        headless = True  # True: no GUI, False: GUI
        train = headless
        terrain_num_rows = 15
        terrain_num_cols = 15


class Robot_Config:
    class ActuatorParam:  # 机器人的参数
        Kp = [60, 60, 60, 60, 60, 60, 30, 30]
        Kd = [5, 5, 5, 5, 5, 5, 2.5, 2.5]  # Do not try to reduce Kd, because the action scale is not 0.25 but 1
        default_PD_angle = [0, 0,
                            -0, 0,
                            0, 0,
                            0, 0]
        actuator_num = 8

    class InitialState:
        initial_height = 0.85
        initial_body_linear_vel_range = 0.2
        initial_body_angular_vel_range = 0.2
        initial_joint_pos_range = 0.2
        initial_joint_vel_range = 0.2
        initial_joint_angle = [0, 0,
                               -0, 0,
                               0, 0,
                               0, 0]

    class DomainRandomizationCfg:
        # relative
        mass_range = 0.1
        com_range = 0.1
        inertia_range = 0.1
        # abs
        friction_range = 1  
        restitution_range = 0.05 

    class ObservationNoiseCfg:
        # relative
        Kp_range = 0.1
        Kd_range = 0.1

        # abs noise
        joint_angle_noise = 0.02
        joint_angular_vel_noise = 0.5
        body_ori_noise = 0.05
        body_angular_vel_noise = 0.2
        depth_camera_noise = 0.2

    class DisturbanceCfg:
        enable_push = True
        push_interval = 1.0
        push_duration = 0.12
        max_force = 120.0
        body_id = 0


class PPO_Config:
    class EstimatorParam:
        enabled = True
        history_len = 10
        obs_dim = 31
        latent_dim = 3
        hidden_layers = [256, 128]
        lr = 1e-3
        model_path = "model/NN_Model/estimator.pth"

    class CriticParam:  # Critic 神经网络 参数
        base_state_dim = 33 + 18 * 11  # 机器人本体与外部指令感知
        residual_state_dim = base_state_dim + 3
        state_dim = base_state_dim
        critic_layers_num = 256
        critic_lr = 2e-4
        critic_update_frequency = 200

    class ActorParam:  # Actor 神经网络 参数
        action_scale = 1
        std_scale = 0.5
        act_layers_num = 256
        actuator_num = Robot_Config.ActuatorParam.actuator_num
        actor_lr = 2e-4
        actor_update_frequency = 100

    class PPOParam:  # 强化学习 PPO算法 参数
        gamma = 0.99
        lam = 0.95
        epsilon = 0.2
        maximum_step = 50
        episode = 3000
        entropy_coef = -0.02  # positive means std increase, else decrease
        batch_size = 20000
