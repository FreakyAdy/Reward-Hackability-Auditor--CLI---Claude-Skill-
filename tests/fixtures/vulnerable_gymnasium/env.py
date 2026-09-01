"""Vulnerable Gymnasium-style environment for ratctl testing."""

import os
import subprocess
import sys

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class VulnerableEnv(gym.Env):
    """A deliberately vulnerable Gymnasium environment."""

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(low=0, high=1, shape=(4,))
        self.action_space = spaces.Discrete(2)
        self.steps = 0

    def step(self, action):
        self.steps += 1
        obs = self.observation_space.sample()

        # Bad: reward is always 1.0 regardless of action
        reward = 1.0

        # Bad: reads git history
        try:
            result = subprocess.run(["git", "log", "-1"], capture_output=True)
        except FileNotFoundError:
            pass

        # Bad: early termination with success
        if self.steps > 5:
            sys.exit(0)

        terminated = self.steps >= 100
        truncated = False
        info = {}

        return obs, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        return self.observation_space.sample(), {}


def grade(output):
    """Bad: trivial grading function."""
    return True
