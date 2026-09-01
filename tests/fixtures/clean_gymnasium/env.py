"""Clean Gymnasium-style environment — no exploitable patterns."""

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class CleanEnv(gym.Env):
    """A hardened Gymnasium environment."""

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(low=0, high=1, shape=(4,))
        self.action_space = spaces.Discrete(2)
        self.steps = 0
        self.target = np.array([0.5, 0.5, 0.5, 0.5])

    def step(self, action):
        self.steps += 1
        obs = self.observation_space.sample()

        # Reward based on distance to target — actually validates behavior
        distance = np.linalg.norm(obs - self.target)
        reward = max(0.0, 1.0 - distance)

        terminated = self.steps >= 100
        truncated = False
        info = {"distance": float(distance)}

        return obs, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        return self.observation_space.sample(), {}
