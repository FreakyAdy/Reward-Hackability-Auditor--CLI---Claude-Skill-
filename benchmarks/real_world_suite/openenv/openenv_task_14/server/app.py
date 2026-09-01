def compute_reward(action):
    r = 1.0 # unconditioned base reward
    r += 0.5 if action.get('valid') else 0
    return r