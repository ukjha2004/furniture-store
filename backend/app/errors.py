"""Shared error type and JSON error responses for every blueprint."""

from flask import jsonify


class ApiError(Exception):
    """Raise this anywhere in a route to return {"error": message} with a status code."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


class BadRequest(ApiError):
    def __init__(self, message):
        super().__init__(message, 400)


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(error=err.message), err.status

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify(error="method not allowed"), 405
