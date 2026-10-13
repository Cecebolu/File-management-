from flask import Blueprint, jsonify

api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)


@api_bp.route("/")
def index():

    return jsonify({
        "status": "success",
        "message": "DocoraFile API is running."
    })