from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

from models import User

# Authentication Blueprint
auth_bp = Blueprint("auth", __name__)


# ===========================
# Login
# ===========================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):

            if not login_user(user, remember=bool(remember)):

                flash("Your account is inactive. Contact an administrator.", "danger")

                return render_template("login.html")

            flash("Login successful!", "success")

            return redirect(url_for("dashboard.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


# ===========================
# Logout
# ===========================
@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "info")

    return redirect(url_for("auth.login"))