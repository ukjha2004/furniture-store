"""Application factory: builds and configures the Flask app.

Settings come from environment variables (set them on Render, never in code):
  DATABASE_URL         postgresql://... for Neon, or a SQLite file path (default: store.db)
  SECRET_KEY           signs login tokens; must be a long random string in production
  ALLOWED_ORIGINS      comma-separated frontend URLs allowed to call the API
  RAZORPAY_KEY_ID      from the Razorpay dashboard (Test Mode keys start with rzp_test_)
  RAZORPAY_KEY_SECRET  from the Razorpay dashboard; keep private
"""

import os
import secrets

from flask import Flask, request

from .auth import auth
from .db import Database, close_db, init_db
from .errors import register_error_handlers
from .orders import orders
from .payments import RazorpayGateway
from .recommender import TfidfRecommender
from .repository import ProductRepository
from .routes import api


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        # DATABASE_PATH is the old name for this setting; still accepted.
        DATABASE=os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH", "store.db"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        ALLOWED_ORIGINS=os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173"),
    )
    if config:
        app.config.update(config)

    if not app.config["SECRET_KEY"]:
        # Safe fallback for local development: a random key per run. Logins then
        # reset whenever the server restarts, so always set SECRET_KEY in production.
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning("SECRET_KEY is not set; using a temporary random key")

    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)
    register_error_handlers(app)
    app.register_blueprint(api)
    app.register_blueprint(auth)
    app.register_blueprint(orders)

    # Payments: tests pass a fake gateway in config; otherwise use Razorpay if keys are set.
    gateway = app.config.get("PAYMENT_GATEWAY")
    # .strip() removes spaces or newlines accidentally pasted around the keys.
    key_id = os.environ.get("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if gateway is None and key_id and key_secret:
        gateway = RazorpayGateway(key_id, key_secret)
        # Startup self-check. Logs the public key id and the secret's LENGTH only (never the secret),
        # so a wrong, swapped or truncated key is easy to spot in the Render logs.
        app.logger.warning(
            "Razorpay key id %s (%s mode), secret length %d -> %s",
            key_id, "test" if key_id.startswith("rzp_test_") else "LIVE?", len(key_secret),
            gateway.check_credentials(),
        )
    app.extensions["payment_gateway"] = gateway  # None means checkout returns "not configured"

    # Train the recommender once at startup on the whole catalogue.
    db = Database(app.config["DATABASE"])
    try:
        products = ProductRepository(db).all()
    finally:
        db.close()
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
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    return app
