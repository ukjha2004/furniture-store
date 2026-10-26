"""Sign up, log in, and protecting routes with JSON Web Tokens (JWT).

How login works:
1. Sign up: the password is hashed (one-way, salted) and only the hash is stored.
2. Log in: the typed password is checked against the hash. If it matches, the
   server returns a signed token: {"sub": user id, "exp": expiry time}.
3. The frontend sends that token on every request:  Authorization: Bearer <token>
4. `login_required` checks the signature and expiry. Nobody can forge or edit a
   token without SECRET_KEY, so the server can trust the user id inside it.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .errors import ApiError, BadRequest
from .models import User
from .repository import EmailTaken, UserRepository

auth = Blueprint("auth", __name__, url_prefix="/api/auth")

TOKEN_LIFETIME = timedelta(days=7)
ALGORITHM = "HS256"


def create_token(user_id):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + TOKEN_LIFETIME}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=ALGORITHM)


def user_from_token(token):
    """Return the User a valid token belongs to, or None if the token is bad or expired."""
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
    return UserRepository(get_db()).get(user_id)


def login_required(view):
    """Decorator: the route only runs for a logged-in user, available as g.user."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        user = user_from_token(token) if scheme == "Bearer" and token else None
        if user is None:
            raise ApiError("please log in", 401)
        g.user = user
        return view(*args, **kwargs)

    return wrapper


_DUMMY_HASH = None


def _dummy_hash():
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = generate_password_hash("not-a-real-password")
    return _DUMMY_HASH


def _json_body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


@auth.post("/signup")
def signup():
    body = _json_body()
    try:
        name, email = User.validate_signup(body.get("name"), body.get("email"), body.get("password"))
    except ValueError as err:
        raise BadRequest(str(err))
    try:
        user = UserRepository(get_db()).create(name, email, generate_password_hash(body["password"]))
    except EmailTaken:
        raise ApiError("an account with this email already exists", 409)
    return jsonify(token=create_token(user.id), user=user.to_dict()), 201


@auth.post("/login")
def login():
    body = _json_body()
    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or not email or not password:
        raise BadRequest("email and password are required")

    user, password_hash = UserRepository(get_db()).get_with_password_hash(email.strip().lower())
    # Same message whether the email or the password is wrong, so attackers
    # can't use this endpoint to discover which emails have accounts. For the same
    # reason we still run a (slow) hash check when the email doesn't exist, so the
    # response takes the same time either way.
    password_ok = check_password_hash(password_hash or _dummy_hash(), password)
    if user is None or not password_ok:
        raise ApiError("incorrect email or password", 401)
    return jsonify(token=create_token(user.id), user=user.to_dict())


@auth.get("/me")
@login_required
def me():
    return jsonify(g.user.to_dict())
