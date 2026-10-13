from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import current_user

from extensions import db
from models import User, Department, ROLES
from permissions import admin_required

users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/users"
)


def assignable_roles():

    return ROLES


def form_department_id():

    return request.form.get("department_id", type=int) or None


@users_bp.route("/")
@admin_required
def list_users():

    query = User.query

    search = request.args.get("search", "").strip()

    if search:

        like = f"%{search}%"

        query = query.filter(
            User.first_name.ilike(like) |
            User.last_name.ilike(like) |
            User.username.ilike(like) |
            User.email.ilike(like)
        )

    users = query.order_by(User.first_name).all()

    return render_template(
        "users/list.html",
        users=users,
        user=current_user
    )


@users_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_user():

    departments = Department.query.order_by(Department.name).all()

    if request.method == "POST":

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        if role not in assignable_roles():

            flash("You can't assign that role.", "danger")

            return redirect(
                url_for("users.add_user")
            )

        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:

            flash(
                "Username or Email already exists.",
                "danger"
            )

            return redirect(
                url_for("users.add_user")
            )

        user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            role=role,
            department_id=form_department_id(),
            active=True
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(
            "User created successfully.",
            "success"
        )

        return redirect(
            url_for("users.list_users")
        )

    return render_template(
        "users/add.html",
        departments=departments,
        roles=assignable_roles()
    )


@users_bp.route("/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):

    user = User.query.get_or_404(user_id)

    departments = Department.query.order_by(Department.name).all()

    if request.method == "POST":

        role = request.form.get("role")

        if role not in assignable_roles():

            flash("You can't assign that role.", "danger")

            return redirect(
                url_for("users.edit_user", user_id=user.id)
            )

        user.first_name = request.form.get("first_name")
        user.last_name = request.form.get("last_name")
        user.username = request.form.get("username")
        user.email = request.form.get("email")
        user.department_id = form_department_id()

        # Don't let admins lock themselves out by demoting or disabling their own account
        if user.id != current_user.id:

            user.role = role
            user.active = True if request.form.get("active") else False

        new_password = request.form.get("password")

        if new_password:
            user.set_password(new_password)

        db.session.commit()

        flash(
            "User updated successfully.",
            "success"
        )

        return redirect(
            url_for("users.list_users")
        )

    return render_template(
        "users/edit.html",
        edit_user=user,
        departments=departments,
        roles=assignable_roles()
    )


# ==========================
# View User
# ==========================

@users_bp.route("/view/<int:user_id>")
@admin_required
def view_user(user_id):

    user = User.query.get_or_404(user_id)

    return render_template(
        "users/view.html",
        view_user=user
    )


# ==========================
# Delete User
# ==========================

@users_bp.route("/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:

        flash(
            "You cannot delete your own account.",
            "warning"
        )

        return redirect(
            url_for("users.list_users")
        )

    if user.uploaded_files or user.activity_logs:

        flash(
            "This user has uploaded files, so they can't be deleted. Deactivate the account instead.",
            "warning"
        )

        return redirect(
            url_for("users.list_users")
        )

    db.session.delete(user)
    db.session.commit()

    flash(
        "User deleted successfully.",
        "success"
    )

    return redirect(
        url_for("users.list_users")
    )
