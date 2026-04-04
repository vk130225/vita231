import numpy as np

def get_subzone(lat, lon):
    grid_x = int(lat * 1000) % 10
    grid_y = int(lon * 1000) % 10

    return f"Z{grid_x}-{grid_y}"