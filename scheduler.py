# scheduler.py

from datetime import datetime, timedelta
from flask_login import current_user
from app import db

def sm2(card, quality):
    q = max(0, min(5, quality))
    user_stat = getattr(current_user, "stat", None)

    ef = card.efactor
    rep = card.repetition
    interval = card.interval_days

    if q < 3:
        rep = 0
        interval = 1
    else:
        rep += 1
        if rep == 1:
            interval = 1
        elif rep == 2:
            interval = 6
        else:
            interval = int(interval * ef)

    # SM-2 efactor update
    new_ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if new_ef < 1.3:
        new_ef = 1.3

    # Adaptive smoothing
    if user_stat:
        α = user_stat.efactor_stability or 0.5  # stability coefficient (0.0 = reactive, 1.0 = slow to change)
        user_stat.average_efactor = α * user_stat.average_efactor + (1 - α) * new_ef
        db.session.add(user_stat)

    next_review = datetime.utcnow() + timedelta(days=interval)
    return interval, new_ef, rep, next_review