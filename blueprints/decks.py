# blueprints/decks.py - Deck management routes
from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, flash, current_app
)
from flask_login import current_user, login_required
from models import Deck, Card, Tag, card_tags
from extensions import db

decks_bp = Blueprint('decks', __name__)

@decks_bp.route("/decks")
@login_required
def deck_list():
    decks = Deck.query.filter_by(user_id=current_user.id).order_by(Deck.created_at.desc()).all()
    return render_template("deck_list.html", decks=decks)

@decks_bp.route("/decks/new", methods=["GET", "POST"])
@login_required
def new_deck():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Deck name cannot be empty.", "warning")
            return redirect(url_for("decks.new_deck"))

        deck = Deck(name=name, user_id=current_user.id)
        db.session.add(deck)
        db.session.commit()
        return redirect(url_for("decks.deck_list"))

    return render_template("deck_form.html")

@decks_bp.route('/decks/<int:deck_id>/delete', methods=['POST'])
@login_required
def delete_deck(deck_id):
    print(f"Request method: {request.method}")
    print(f"Route accessed with id: {id}")
    print(f"Request data: {request.data}")
    print(f"Form data: {request.form}")
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    db.session.delete(deck)
    db.session.commit()
    flash("Deck deleted successfully.", "success")
    return redirect(url_for('decks.deck_list'))  # ← FIXED
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    db.session.delete(deck)
    db.session.commit()
    flash("Deck deleted successfully.", "success")
    return redirect(url_for('deck_list.html'))

@decks_bp.route("/decks/<int:deck_id>")
@login_required
def deck_detail(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    all_tags = (
        Tag.query
        .join(card_tags)
        .join(Card)
        .filter(Card.deck_id == deck.id)
        .distinct()
        .order_by(Tag.name)
        .all()
    )

    q = request.args.get("q", "").strip()
    tag_id = request.args.get("tag", type=int)

    query = Card.query.filter(Card.deck_id == deck.id)

    if q:
        search_expr = f"MATCH(front, back) AGAINST(:q IN NATURAL LANGUAGE MODE)"
        query = query.filter(db.text(search_expr)).params(q=q)

    if tag_id:
        query = query.join(card_tags).filter(card_tags.c.tag_id == tag_id)

    query = query.order_by(
        db.text("(next_review IS NULL) DESC"),
        db.text("next_review ASC")
    )

    cards = query.all()

    return render_template(
        "deck_detail.html",
        deck=deck,
        cards=cards,
        all_tags=all_tags,
        selected_tag=tag_id,
        q=q
    )