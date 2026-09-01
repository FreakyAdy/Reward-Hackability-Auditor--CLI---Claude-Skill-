
import gymnasium as gym
class CustomEnv(gym.Env):
    def step(self, action):
        # Additive reward skipping
        reward = 1.0 + (0.5 if action == 1 else 0)
        return {}, reward, False, False, {}
