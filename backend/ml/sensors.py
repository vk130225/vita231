import numpy as np

def get_sensor_score():

    motion_type = np.random.choice(
        ["delivery", "idle", "fake"],
        p=[0.7, 0.2, 0.1]
    )

    if motion_type == "delivery":
        return 0.8
    elif motion_type == "idle":
        return 0.3
    else:
        return 0.1