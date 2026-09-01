
import gymnasium as gym
class CustomEnv(gym.Env):
    def step(self, action):
        reward = 1.0 if action == self.target else -1.0
        return {}, reward, False, False, {}
