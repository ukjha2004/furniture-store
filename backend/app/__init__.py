"""Application factory: builds and configures the Flask app."""

import os

from flask import Flask, jsonify, request

from .db import close_db, connect, init_db
from .recommender import TfidfRecommender
from .repository import ProductRepository
from .routes import api


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("DATABASE_PATH", "store.db"),
        # Comma-separated list of frontend URLs allowed to call the API.
        ALLOWED_ORIGINS=os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173"),
    )
    if config:
        app.config.update(config)

    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)
    app.register_blueprint(api)

    # Train the recommender once at startup on the whole catalogue.
    conn = connect(app.config["DATABASE"])
    try:
        products = ProductRepository(conn).all()
    finally:
        conn.close()
    app.extensions["recommender"] = TfidfRecommender().fit(products)

    allowed = {o.strip() for o in app.config["ALLOWED_ORIGINS"].split(",") if o.strip()}

    @app.after_request
    def add_cors_headers(response):
        """Let the React frontend (a different origin) call this API from the browser."""
        origin = request.headers.get("Origin", "")
        if origin in allowed or "*" in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify(error="method not allowed"), 405

    return app

