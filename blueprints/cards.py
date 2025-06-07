# blueprints/cards.py - Card management routes
from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, flash, current_app
)
from flask_login import current_user, login_required
from models import Deck, Card, Tag, card_tags
from extensions import db
from utils import allowed_file, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_AUDIO_EXTENSIONS, save_uploaded_file
from datetime import datetime

cards_bp = Blueprint('cards', __name__)

@cards_bp.route("/decks/<int:deck_id>/cards/new", methods=["GET", "POST"])
@login_required
def new_card(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    tags = Tag.query.order_by(Tag.name).all()

    if request.method == "POST":
        front = request.form.get("front", "").strip()
        back = request.form.get("back", "").strip()
        if not front or not back:
            flash("Both front and back must be provided.", "warning")
            return redirect(url_for("cards.new_card", deck_id=deck.id))

        # Handle image upload
        image_file = request.files.get("image_file")
        image_url = request.form.get("image_url", "").strip()
        image_filename = save_uploaded_file(image_file, ALLOWED_IMAGE_EXTENSIONS)
        
        if image_file and image_file.filename and not image_filename:
            flash("Invalid image type. Must be PNG, JPG, JPEG, or GIF.", "danger")
            return redirect(url_for("cards.new_card", deck_id=deck.id))

        # Handle audio upload
        audio_file = request.files.get("audio_file")
        audio_url = request.form.get("audio_url", "").strip()
        audio_filename = save_uploaded_file(audio_file, ALLOWED_AUDIO_EXTENSIONS)
        
        if audio_file and audio_file.filename and not audio_filename:
            flash("Invalid audio type. Must be MP3, WAV, OGG, or M4A.", "danger")
            return redirect(url_for("cards.new_card", deck_id=deck.id))

        # Create Card instance
        card = Card(
            deck_id=deck.id,
            front=front,
            back=back,
            image_filename=image_filename,
            image_url=image_url if (not image_filename and image_url) else None,
            audio_filename=audio_filename,
            audio_url=audio_url if (not audio_filename and audio_url) else None,
            interval_days=0,
            repetition=0,
            efactor=2.5,
            next_review=datetime.utcnow()
        )

        # Attach existing tags by ID
        selected_tag_ids = request.form.getlist("tags")
        for tid in selected_tag_ids:
            tag = Tag.query.get(int(tid))
            if tag:
                card.tags.append(tag)

        # Create new tags from comma-separated "new_tags" field
        new_tags_raw = request.form.get("new_tags", "").strip()
        if new_tags_raw:
            for name in [n.strip() for n in new_tags_raw.split(",") if n.strip()]:
                existing = Tag.query.filter_by(name=name).first()
                if existing:
                    if existing not in card.tags:
                        card.tags.append(existing)
                else:
                    new_tag = Tag(name=name)
                    db.session.add(new_tag)
                    db.session.flush()
                    card.tags.append(new_tag)

        db.session.add(card)
        db.session.commit()
        return redirect(url_for("decks.deck_detail", deck_id=deck.id))

    return render_template("card_form.html", deck=deck, tags=tags)

@cards_bp.route("/decks/<int:deck_id>/import", methods=["GET", "POST"])
@login_required
def import_cards(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        uploaded_file = request.files.get("file")
        if not uploaded_file or uploaded_file.filename == "":
            flash("No file selected.", "warning")
            return redirect(url_for("cards.import_cards", deck_id=deck.id))

        filename_lower = uploaded_file.filename.lower()
        try:
            if filename_lower.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
            elif filename_lower.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                flash("Unsupported file type. Please upload .xlsx or .csv.", "danger")
                return redirect(url_for("cards.import_cards", deck_id=deck.id))
        except Exception as e:
            flash(f"Failed to read file: {e}", "danger")
            return redirect(url_for("cards.import_cards", deck_id=deck.id))

        df_cols = {col.strip().lower() for col in df.columns}
        required = {"front", "back"}
        if not required.issubset(df_cols):
            flash("File must contain columns labeled exactly 'front' and 'back'.", "danger")
            return redirect(url_for("cards.import_cards", deck_id=deck.id))

        imported = 0
        skipped = 0

        for idx, row in df.iterrows():
            front = str(row.get("front", "")).strip()
            back = str(row.get("back", "")).strip()
            if not front or not back:
                skipped += 1
                continue

            exists = Card.query.filter_by(deck_id=deck.id, front=front, back=back).first()
            if exists:
                skipped += 1
                continue

            card = Card(
                deck_id=deck.id,
                front=front,
                back=back,
                interval_days=0,
                repetition=0,
                efactor=2.5,
                next_review=datetime.utcnow()
            )
            db.session.add(card)
            imported += 1

        db.session.commit()
        flash(f"Imported {imported} cards; skipped {skipped} rows.", "success")
        return redirect(url_for("decks.deck_detail", deck_id=deck.id))

    return render_template("import.html", deck=deck)