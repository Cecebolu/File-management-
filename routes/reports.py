from flask import Blueprint, render_template

from permissions import admin_required

reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/reports"
)

@reports_bp.route("/")
@admin_required
def index():
    return render_template("reports/index.html")