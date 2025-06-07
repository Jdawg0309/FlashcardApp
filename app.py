# app.py - Main application factory
from flask import Flask
from config import Config
from extensions import db, migrate, login_manager
from models import User
from blueprints.auth import auth_bp
from blueprints.decks import decks_bp
from blueprints.cards import cards_bp
from blueprints.reviews import reviews_bp
from blueprints.exports import exports_bp
from blueprints.generate import generate_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(exports_bp)
    app.register_blueprint(generate_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)