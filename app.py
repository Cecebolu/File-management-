from datetime import datetime

from flask import Flask, redirect, url_for, render_template

from config import Config
from extensions import (
    db,
    login_manager,
    bcrypt,
    migrate,
)

# Import models
from models import User

# Import Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.users import users_bp
from routes.departments import departments_bp
from routes.folders import folders_bp
from routes.files import files_bp
from routes.reports import reports_bp
from routes.api import api_bp
from routes.settings import settings_bp


def create_app():

    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    # Home Route
    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    @app.template_filter("filesize")
    def filesize(size):
        if not size:
            return "—"
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024

    @app.context_processor
    def inject_now():
        return {"now": datetime.now()}

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)