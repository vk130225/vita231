def create_feature_vector(real_data, movement, activity, location):
    return [
        float(real_data.get("rain", 0)),
        float(real_data.get("temp", 0)),
        float(real_data.get("aqi", 0)),
        float(movement),
        float(activity),
        int(location),
    ]
