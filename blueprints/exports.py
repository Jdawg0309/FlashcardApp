# blueprints/exports.py - Export routes
from flask import (
    Blueprint, send_file, current_app
)
from flask_login import current_user, login_required
from models import Deck, Card
from extensions import db
import pandas as pd
import io
import tempfile
import genanki
from datetime import datetime

exports_bp = Blueprint('exports', __name__)

@exports_bp.route("/decks/<int:deck_id>/export_csv")
@login_required
def export_csv(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    cards = deck.cards.all()

    data = []
    for c in cards:
        data.append({
            "front": c.front,
            "back": c.back,
            "image_filename": c.image_filename or "",
            "image_url": c.image_url or "",
            "audio_filename": c.audio_filename or "",
            "audio_url": c.audio_url or "",
            "tags": ",".join(tag.name for tag in c.tags),
            "interval_days": c.interval_days,
            "repetition": c.repetition,
            "efactor": c.efactor,
            "next_review": c.next_review.strftime("%Y-%m-%d %H:%M") if c.next_review else ""
        })
    df = pd.DataFrame(data)

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{deck.name}_export.csv"
    )

@exports_bp.route("/decks/<int:deck_id>/export_xlsx")
@login_required
def export_xlsx(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    cards = deck.cards.all()

    data = []
    for c in cards:
        data.append({
            "front": c.front,
            "back": c.back,
            "image_filename": c.image_filename or "",
            "image_url": c.image_url or "",
            "audio_filename": c.audio_filename or "",
            "audio_url": c.audio_url or "",
            "tags": ",".join(tag.name for tag in c.tags),
            "interval_days": c.interval_days,
            "repetition": c.repetition,
            "efactor": c.efactor,
            "next_review": c.next_review.strftime("%Y-%m-%d %H:%M") if c.next_review else ""
        })
    df = pd.DataFrame(data)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cards")
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"{deck.name}_export.xlsx"
    )

@exports_bp.route("/decks/<int:deck_id>/export_anki")
@login_required
def export_anki(deck_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    cards = deck.cards.all()

    anki_deck = genanki.Deck(
        deck_id=deck.id + 1000000,
        name=deck.name
    )
    model = genanki.Model(
        1607392319,
        "Simple Model",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": "{{FrontSide}}<hr id=\"answer\">{{Back}}"
            }
        ]
    )
    for c in cards:
        front_html = c.front
        back_html = c.back
        note = genanki.Note(model=model, fields=[front_html, back_html])
        anki_deck.add_note(note)

    tmp = tempfile.NamedTemporaryFile(suffix=".apkg", delete=False)
    genanki.Package(anki_deck).write_to_file(tmp.name)
    tmp.close()
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name=f"{deck.name}.apkg"
    )