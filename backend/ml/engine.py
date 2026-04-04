import random

def location_check():
    return random.choice([0, 1])  # 1 = valid

def movement_score():
    return random.randint(60, 100)

def activity_score():
    return random.randint(60, 100)

def final_score(zone, location, movement, activity):
    zone_score = {"RED": 1, "ORANGE": 0.8, "YELLOW": 0.6, "GREEN": 0.3}

    score = (
        0.3 * zone_score[zone] +
        0.2 * location +
        0.25 * (movement / 100) +
        0.25 * (activity / 100)
    )

    return score

def decision(score):
    if score > 0.7:
        return "APPROVED"
    elif score > 0.5:
        return "REVIEW"
    return "REJECTED"