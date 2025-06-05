# scheduler.py

from datetime import datetime, timedelta

def sm2(card, quality):
    """
    Implements the SM-2 spaced repetition algorithm.

    Args:
      card: instance of Card (with .interval_days, .repetition, .efactor)
      quality: integer 0..5 (5 = perfect recall, 0 = complete blackout)

    Returns:
      (new_interval_days, new_efactor, new_repetition, new_next_review_datetime)
    """
    # Clamp quality between 0 and 5
    q = max(0, min(5, quality))

    ef = card.efactor
    rep = card.repetition
    interval = card.interval_days

    if q < 3:
        # Hard recall or forgotten: reset repetition
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

    # Update ease factor
    ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if ef < 1.3:
        ef = 1.3

    next_review = datetime.utcnow() + timedelta(days=interval)
    return interval, ef, rep, next_review
