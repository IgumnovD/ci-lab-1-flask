from flask import Flask, jsonify
from app.visits import create_visits_blueprint, init_db
import os


def create_app():
    app = Flask(__name__)
    app.register_blueprint(create_visits_blueprint())

    @app.cli.command("init-db")
    def initialize_database():
        """Create the visits table before serving requests."""
        init_db(os.environ["DATABASE_URL"])

    @app.route("/health")
    def health():
        return jsonify(status="ok"), 200

    return app
