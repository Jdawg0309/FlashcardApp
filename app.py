# app.py

import os
import uuid
import io
import tempfile
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    current_app
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

import pandas as pd       # For CSV/Excel import/export
import genanki            # For Anki .apkg export
from werkzeug.utils import secure_filename

# ───────────────────────────────────────────────────────────────────────
# 1) Initialize extensions at module scope
# ───────────────────────────────────────────────────────────────────────
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # ─────────────────────────────────────────────────────────────────
    # 2) Initialize SQLAlchemy, Migrate, and LoginManager
    # ─────────────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # ─────────────────────────────────────────────────────────────────
    # 3) Import models now that extensions are bound to the app
    # ─────────────────────────────────────────────────────────────────
    from models import User, Deck, Card, ReviewLog, Tag, card_tags

    # ─────────────────────────────────────────────────────────────────
    # 4) Allowed file extensions for images/audio
    # ─────────────────────────────────────────────────────────────────
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a"}

    def allowed_file(filename, allowed_set):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

    # ─────────────────────────────────────────────────────────────────
    # 5) ROUTES
    # ─────────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("deck_list"))
        else:
            return redirect(url_for("login"))

    # —––– User Registration (plaintext) —–––
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("deck_list"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            password2 = request.form.get("password2", "").strip()

            if not username or not email or not password or not password2:
                flash("All fields are required.", "warning")
                return redirect(url_for("register"))

            if password != password2:
                flash("Passwords do not match.", "warning")
                return redirect(url_for("register"))

            existing = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            if existing:
                flash("Username or email already taken.", "warning")
                return redirect(url_for("register"))

            # Save plaintext password directly
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    # —––– User Login (plaintext comparison) —–––
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("deck_list"))

        if request.method == "POST":
            username_or_email = request.form.get("username_or_email", "").strip()
            password = request.form.get("password", "").strip()

            if "@" in username_or_email:
                user = User.query.filter_by(email=username_or_email).first()
            else:
                user = User.query.filter_by(username=username_or_email).first()

            # Compare raw password to stored plaintext
            if user is None or user.password != password:
                flash("Invalid credentials.", "danger")
                return redirect(url_for("login"))

            login_user(user, remember=(request.form.get("remember") == "on"))
            flash("Logged in successfully.", "success")
            return redirect(url_for("deck_list"))

        return render_template("login.html")

    # —––– User Logout —–––
    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # —––– 1. List all decks for current user —–––
    @app.route("/decks")
    @login_required
    def deck_list():
        decks = Deck.query.filter_by(user_id=current_user.id).order_by(Deck.created_at.desc()).all()
        return render_template("deck_list.html", decks=decks)

    # —––– 2. Create a new deck —–––
    @app.route("/decks/new", methods=["GET", "POST"])
    @login_required
    def new_deck():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Deck name cannot be empty.", "warning")
                return redirect(url_for("new_deck"))

            deck = Deck(name=name, user_id=current_user.id)
            db.session.add(deck)
            db.session.commit()
            return redirect(url_for("deck_list"))

        return render_template("deck_form.html")

    # —––– 3. Deck detail: show cards, search & tag filter —–––
    @app.route("/decks/<int:deck_id>")
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

    # —––– 4. Add a new card (with image/audio + tags) —–––
    @app.route("/decks/<int:deck_id>/cards/new", methods=["GET", "POST"])
    @login_required
    def new_card(deck_id):
        deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
        tags = Tag.query.order_by(Tag.name).all()

        if request.method == "POST":
            front = request.form.get("front", "").strip()
            back = request.form.get("back", "").strip()
            if not front or not back:
                flash("Both front and back must be provided.", "warning")
                return redirect(url_for("new_card", deck_id=deck.id))

            # — Image handling —
            image_file = request.files.get("image_file")
            image_url = request.form.get("image_url", "").strip()
            image_filename = None
            if image_file and image_file.filename:
                if allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                    ext = image_file.filename.rsplit(".", 1)[1].lower()
                    unique_name = f"{uuid.uuid4().hex}.{ext}"
                    save_path = os.path.join(
                        current_app.root_path, "static", "uploads", unique_name
                    )
                    image_file.save(save_path)
                    image_filename = unique_name
                else:
                    flash("Invalid image type. Must be PNG, JPG, JPEG, or GIF.", "danger")
                    return redirect(url_for("new_card", deck_id=deck.id))

            # — Audio handling —
            audio_file = request.files.get("audio_file")
            audio_url = request.form.get("audio_url", "").strip()
            audio_filename = None
            if audio_file and audio_file.filename:
                if allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
                    ext = audio_file.filename.rsplit(".", 1)[1].lower()
                    unique_name = f"{uuid.uuid4().hex}.{ext}"
                    save_path = os.path.join(
                        current_app.root_path, "static", "uploads", unique_name
                    )
                    audio_file.save(save_path)
                    audio_filename = unique_name
                else:
                    flash("Invalid audio type. Must be MP3, WAV, OGG, or M4A.", "danger")
                    return redirect(url_for("new_card", deck_id=deck.id))

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

            # Create new tags from comma-separated “new_tags” field
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
            return redirect(url_for("deck_detail", deck_id=deck.id))

        return render_template("card_form.html", deck=deck, tags=tags)

    # —––– 5. Bulk Import (Excel / CSV) —–––
    @app.route("/decks/<int:deck_id>/import", methods=["GET", "POST"])
    @login_required
    def import_cards(deck_id):
        deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

        if request.method == "POST":
            uploaded_file = request.files.get("file")
            if not uploaded_file or uploaded_file.filename == "":
                flash("No file selected.", "warning")
                return redirect(url_for("import_cards", deck_id=deck.id))

            filename_lower = uploaded_file.filename.lower()
            try:
                if filename_lower.endswith(".xlsx"):
                    df = pd.read_excel(uploaded_file)
                elif filename_lower.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    flash("Unsupported file type. Please upload .xlsx or .csv.", "danger")
                    return redirect(url_for("import_cards", deck_id=deck.id))
            except Exception as e:
                flash(f"Failed to read file: {e}", "danger")
                return redirect(url_for("import_cards", deck_id=deck.id))

            df_cols = {col.strip().lower() for col in df.columns}
            required = {"front", "back"}
            if not required.issubset(df_cols):
                flash("File must contain columns labeled exactly 'front' and 'back'.", "danger")
                return redirect(url_for("import_cards", deck_id=deck.id))

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
            return redirect(url_for("deck_detail", deck_id=deck.id))

        return render_template("import.html", deck=deck)

    # —––– 6. Review cards —–––
    @app.route("/decks/<int:deck_id>/review", methods=["GET", "POST"])
    @login_required
    def review(deck_id):
        deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

        if request.method == "POST":
            card_id = int(request.form.get("card_id"))
            quality = int(request.form.get("quality"))
            card = Card.query.get_or_404(card_id)

            from scheduler import sm2
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

            return redirect(url_for("review", deck_id=deck.id))

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

    # —––– 7. Deck statistics + Chart.js data —–––
    @app.route("/stats/<int:deck_id>")
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

    # —––– 8. Export to CSV —–––
    @app.route("/decks/<int:deck_id>/export_csv")
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

    # —––– 9. Export to Excel —–––
    @app.route("/decks/<int:deck_id>/export_xlsx")
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

    # —––– 10. Export to Anki (.apkg) —–––
    @app.route("/decks/<int:deck_id>/export_anki")
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

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
