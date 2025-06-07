# app/generate/routes.py
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from openai import OpenAI
from extensions import db
from models import Deck, Card
import os

generate_bp = Blueprint("generate", __name__)

# Optional: Load OpenAI once
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
print(os.getenv("OPENAI_API_KEY"))

@generate_bp.route("/generate", methods=["GET", "POST"])
@login_required
def generate_flashcards():
    if request.method == "POST":
        topic = request.form.get("topic")
        report = request.form.get("report")

        if not report:
            flash("Please provide a research report.", "danger")
            return redirect(url_for("generate.generate_flashcards"))

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert flashcard creator."},
                    {"role": "user", "content": f"Create 10 flashcards from this report. Format strictly as:\nQ: question\nA: answer\n\nReport:\n{report}"}
                ],
                temperature=0.4
            )

            content = response.choices[0].message.content.strip()
            print("=== GPT RESPONSE ===")
            print(content)

            import re
            qa_pairs = re.findall(r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\nQ:|\Z)", content, re.DOTALL)

            if not qa_pairs:
                flash("No flashcards were detected in the response. Try again or rephrase.", "danger")
                return redirect(url_for("generate.generate_flashcards"))

            deck = Deck(name=f"Generated: {topic}", user_id=current_user.id)
            db.session.add(deck)
            db.session.flush()

            for q, a in qa_pairs:
                card = Card(front=q.strip(), back=a.strip(), deck_id=deck.id)
                db.session.add(card)

            db.session.commit()
            flash(f"Flashcards generated in deck: {deck.name}", "success")
            return redirect(url_for("decks.deck_detail", deck_id=deck.id))

        except Exception as e:
            flash(f"Error generating flashcards: {str(e)}", "danger")

    return render_template("generate.html")

    if request.method == "POST":
        topic = request.form.get("topic")
        report = request.form.get("report")

        if not report:
            flash("Please provide a research report.", "danger")
            return redirect(url_for("generate.generate_flashcards"))

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert flashcard creator."},
                    {"role": "user", "content": f"Create 10 Q&A flashcards from the following research report:\n\n{report}"}
                ],
                temperature=0.4
            )
            content = response.choices[0].message.content.strip()
            lines = content.split("\n")

            # Auto-create deck
            deck = Deck(name=f"Generated: {topic}", user_id=current_user.id)
            db.session.add(deck)
            db.session.flush()

            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    q = lines[i].replace("Q:", "").strip()
                    a = lines[i+1].replace("A:", "").strip()
                    card = Card(front=q, back=a, deck_id=deck.id)
                    db.session.add(card)

            db.session.commit()
            flash(f"Flashcards generated in deck: {deck.name}", "success")
            return redirect(url_for("decks.deck_detail", deck_id=deck.id))

        except Exception as e:
            flash(f"Error generating flashcards: {str(e)}", "danger")

    return render_template("generate.html")
