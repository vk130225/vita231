import numpy as np
import pandas as pd

def generate_dataset(n=500):
    data = []

    for _ in range(n):
        rain = np.random.uniform(0, 30)
        temp = np.random.uniform(20, 40)
        aqi = np.random.uniform(50, 300)

        movement = np.random.uniform(20, 100)
        activity = np.random.uniform(20, 100)
        location = np.random.choice([0, 1], p=[0.2, 0.8])

        # label logic (important)
        risk = (rain > 10) + (aqi > 150) + (movement < 40)

        label = 1 if risk >= 2 and location == 1 else 0

        data.append([rain, temp, aqi, movement, activity, location, label])

    df = pd.DataFrame(data, columns=[
        "rain", "temp", "aqi",
        "movement", "activity", "location", "label"
    ])

    return df