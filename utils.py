import matplotlib.pyplot as plt
from ray.rllib.algorithms import Algorithm
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.models import ModelCatalog
from ray.rllib.policy.policy import PolicySpec

from env.grid_world import GridWorldEnv
from models.rl_wrappers import CustomTorchModelV2


def parse_optimizer(parser):
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--model_name', type=str, default='mppo_connect_v3')
    parser.add_argument('--config', type=str, default="default")

def plot_metrics(metrics: [[float, float]], name: str):
    mean_rewards = [m[0] for m in metrics]
    mean_lengths = [m[1] for m in metrics]
    iterations = list(range(len(metrics)))

    fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    axs[0].plot(iterations, mean_rewards, label="Mean Reward", color='blue')
    axs[0].set_ylabel("Mean Reward")
    axs[0].set_title("Training Progress")
    axs[0].grid(True)

    axs[1].plot(iterations, mean_lengths, label="Mean Episode Length", color='green')
    axs[1].set_xlabel("Iteration")
    axs[1].set_ylabel("Mean Episode Length")
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(f'{name}_metrics.png')
    plt.show()

# RLlib only
def build_config(env_config: dict, training_config: dict) -> Algorithm:
    ppo_params = dict(
        gamma=training_config['gamma'],
        lr=training_config['lr'],
        grad_clip=training_config['grad_clip'],
        train_batch_size=training_config['train_batch_size'],
        num_epochs=training_config['num_epochs'],
        minibatch_size=training_config['minibatch_size'],
        optimizer={
            "weight_decay": training_config['l2_regularization']
        }
    )

    config = use_old_API_stack(env_config, ppo_params)

    print("Multi-Agent Config:", config.is_multi_agent)

    return config.build_algo()

def use_old_API_stack(env_config: dict, ppo_params: dict) -> PPOConfig:
    ModelCatalog.register_custom_model("shared_cnn", CustomTorchModelV2)
    dummy_env = GridWorldEnv(**env_config)

    config = (
        PPOConfig()
        .environment(
            env="grid_world",
            env_config=env_config,
            is_atari=False,
        )
        .framework("torch")
        .multi_agent(
            policies={
                f"shared_policy": PolicySpec(
                    policy_class=None,  # Use default PPO
                    observation_space=dummy_env.observation_space(f"agent_0"),
                    action_space=dummy_env.action_space(f"agent_0"),
                )
            },
            policy_mapping_fn=lambda agent_id, *args, **kwargs: "shared_policy",
        )
        .training(
            model={
                "custom_model": "shared_cnn",
            },
            use_gae=True,
            use_critic=True,
            **ppo_params
        )
        .env_runners(
            num_env_runners=0,
            num_envs_per_env_runner=1,
            rollout_fragment_length=500
        )
        .resources(
            num_gpus=1
        )
        .evaluation(
            evaluation_num_env_runners=0,
            evaluation_interval=None
        )
        .api_stack(
            enable_env_runner_and_connector_v2=False,
            enable_rl_module_and_learner=False,
        )
    )
    dummy_env.close()

    return config