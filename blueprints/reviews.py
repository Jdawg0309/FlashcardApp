# blueprints/reviews.py - Review and stats routes
from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, flash, current_app
)
from flask_login import current_user, login_required
from models import Deck, Card, ReviewLog
from extensions import db
from datetime import datetime
from scheduler import sm2

reviews_bp = Blueprint('reviews', __name__)

from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@reviews_bp.route("/decks/<int:deck_id>/review", methods=["GET", "POST"])
@login_required
def review(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    now = datetime.utcnow()

    card = (
        Card.query
        .filter(
            Card.deck_id == deck.id,
            (Card.next_review <= now) | (Card.next_review.is_(None))
        )
        .order_by(
            db.text("(next_review IS NULL) DESC"),
            db.text("next_review ASC")
        )
        .first()
    )

    if not card:
        return render_template("review.html", deck=deck, card=None)

    feedback = None

    if request.method == "POST":
        mode = request.form.get("mode")
        card_id = int(request.form.get("card_id"))
        card = Card.query.get_or_404(card_id)

        if mode == "active_recall":
            user_answer = request.form.get("user_answer")

            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You're an AI tutor grading free-recall flashcard answers."},
                        {"role": "user", "content": f"""Evaluate this:
Question: {card.front}
Correct Answer: {card.back}
Student's Answer: {user_answer}

Grade the answer on a scale of 1–5 and give brief feedback.
Output format:
Score: X/5
Feedback: [Your feedback]
"""}],
                    temperature=0.5
                )
                feedback = response.choices[0].message.content.strip()
                return render_template("review.html", deck=deck, card=card, feedback=feedback, mode="active_recall")

            except Exception as e:
                flash(f"Error using AI: {e}", "danger")
                return redirect(url_for("reviews.review", deck_id=deck.id))

        else:  # Normal mode (SM2 grading)
            quality = int(request.form.get("quality"))
            new_interval, new_ef, new_rep, new_next = sm2(card, quality)
            card.interval_days = new_interval
            card.efactor = new_ef
            card.repetition = new_rep
            card.next_review = new_next

            log = ReviewLog(
                card_id=card.id,
                quality=quality,
                interval_days=new_interval,
                efactor=new_ef
            )
            db.session.add(log)
            db.session.commit()

            return redirect(url_for("reviews.review", deck_id=deck.id))

    return render_template("review.html", deck=deck, card=card, feedback=feedback)
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        card_id = int(request.form.get("card_id"))
        quality = int(request.form.get("quality"))
        card = Card.query.get_or_404(card_id)

        new_interval, new_ef, new_rep, new_next = sm2(card, quality)
        card.interval_days = new_interval
        card.efactor = new_ef
        card.repetition = new_rep
        card.next_review = new_next

        log = ReviewLog(
            card_id=card.id,
            quality=quality,
            interval_days=new_interval,
            efactor=new_ef
        )
        db.session.add(log)
        db.session.commit()

        return redirect(url_for("reviews.review", deck_id=deck.id))

    now = datetime.utcnow()
    card = (
        Card.query
        .filter(
            Card.deck_id == deck.id,
            (Card.next_review <= now) | (Card.next_review.is_(None))
        )
        .order_by(
            db.text("(next_review IS NULL) DESC"),
            db.text("next_review ASC")
        )
        .first()
    )
    return render_template("review.html", deck=deck, card=card)

@reviews_bp.route("/stats/<int:deck_id>")
@login_required
def stats(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    total_cards = deck.cards.count()

    now = datetime.utcnow()
    due_cards = deck.cards.filter(Card.next_review <= now).count()

    logs = (
        ReviewLog.query
        .join(Card)
        .filter(Card.deck_id == deck.id)
        .order_by(ReviewLog.review_date.desc())
        .limit(50)
        .all()
    )

    result = (
        db.session.query(
            db.func.date(ReviewLog.review_date).label("day"),
            db.func.count(ReviewLog.id).label("count")
        )
        .join(Card)
        .filter(Card.deck_id == deck.id)
        .group_by("day") 
        .order_by("day")
        .all()
    )
    chart_dates = [row.day.strftime("%Y-%m-%d") for row in result]
    chart_counts = [row.count for row in result]

    return render_template(
        "stats.html",
        deck=deck,
        total_cards=total_cards,
        due_cards=due_cards,
        logs=logs,
        chart_dates=chart_dates,
        chart_counts=chart_counts
    )