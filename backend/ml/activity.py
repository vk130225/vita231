import numpy as np

def get_activity_score():
    # simulate active working time (in minutes)
    active_time = np.random.choice([10, 30, 60, 90])

    # validation logic
    if active_time >= 45:
        return 1  # valid worker
    return 0  # not valid