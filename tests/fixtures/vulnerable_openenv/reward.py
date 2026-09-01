"""Deliberately vulnerable reward function."""


def reward_function(observation, action, done):
    """Bad: hardcoded maximum reward."""
    reward = 1.0
    return reward
