# models.py

from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager

# ───────────────────────────────────────────────────────────────────────
# Flask-Login user_loader
# ───────────────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # PLAIN‐TEXT password (no hashing)
    password = db.Column(db.String(128), nullable=False)

    # Relationship: One User → Many Decks
    decks = db.relationship(
        "Deck",
        backref="owner",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


# ───────────────────────────────────────────────────────────────────────
# Association table for Card ↔ Tag (many‐to‐many)
# ───────────────────────────────────────────────────────────────────────
card_tags = db.Table(
    "card_tags",
    db.Column("card_id", db.Integer, db.ForeignKey("cards.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


# ───────────────────────────────────────────────────────────────────────
# Deck model (belongs to a User)
# ───────────────────────────────────────────────────────────────────────
class Deck(db.Model):
    __tablename__ = "decks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One Deck → Many Cards
    cards = db.relationship(
        "Card",
        backref="deck",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Deck {self.id} '{self.name}' owned by User {self.user_id}>"


# ───────────────────────────────────────────────────────────────────────
# Tag model (cards ↔ tags = many‐to‐many)
# ───────────────────────────────────────────────────────────────────────
class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)

    cards = db.relationship(
        "Card",
        secondary=card_tags,
        back_populates="tags"
    )

    def __repr__(self):
        return f"<Tag {self.name}>"


# ───────────────────────────────────────────────────────────────────────
# Card model
# ───────────────────────────────────────────────────────────────────────
class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    deck_id = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)

    front = db.Column(db.Text, nullable=False)
    back = db.Column(db.Text, nullable=False)

    # — Image/Audio support —
    image_filename = db.Column(db.String(256), nullable=True)
    image_url = db.Column(db.String(512), nullable=True)
    audio_filename = db.Column(db.String(256), nullable=True)
    audio_url = db.Column(db.String(512), nullable=True)

    # — SM-2 spaced-repetition fields —
    interval_days = db.Column(db.Integer, default=0, nullable=False)
    repetition = db.Column(db.Integer, default=0, nullable=False)
    efactor = db.Column(db.Float, default=2.5, nullable=False)
    next_review = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # — Tagging relationship —
    tags = db.relationship(
        "Tag",
        secondary=card_tags,
        back_populates="cards"
    )

    # — Review logs —
    reviews = db.relationship(
        "ReviewLog",
        backref="card",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Card {self.id} in Deck {self.deck_id}>"


# ───────────────────────────────────────────────────────────────────────
# ReviewLog model
# ───────────────────────────────────────────────────────────────────────
class ReviewLog(db.Model):
    __tablename__ = "review_logs"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)
    quality = db.Column(db.Integer, nullable=False)
    interval_days = db.Column(db.Integer, nullable=False)
    efactor = db.Column(db.Float, nullable=False)
    response_time = db.Column(db.Float, nullable=True)  # in seconds

    def __repr__(self):
        return (
            f"<ReviewLog Card {self.card_id} on {self.review_date:%Y-%m-%d} "
            f"(q={self.quality}, intv={self.interval_days}, ef={self.efactor:.2f})>"
        )
