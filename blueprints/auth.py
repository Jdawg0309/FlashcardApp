# blueprints/auth.py - Authentication routes
from flask import (
    Blueprint, render_template, request, redirect, 
    url_for, flash, current_app
)
from flask_login import login_user, logout_user, current_user, login_required
from models import User
from extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("decks.deck_list"))
    else:
        return redirect(url_for("auth.login"))

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("decks.deck_list"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        password2 = request.form.get("password2", "").strip()

        if not username or not email or not password or not password2:
            flash("All fields are required.", "warning")
            return redirect(url_for("auth.register"))

        if password != password2:
            flash("Passwords do not match.", "warning")
            return redirect(url_for("auth.register"))

        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            flash("Username or email already taken.", "warning")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("decks.deck_list"))

    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "").strip()

        if "@" in username_or_email:
            user = User.query.filter_by(email=username_or_email).first()
        else:
            user = User.query.filter_by(username=username_or_email).first()

        if user is None or user.password != password:
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=(request.form.get("remember") == "on"))
        flash("Logged in successfully.", "success")
        return redirect(url_for("decks.deck_list"))

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))