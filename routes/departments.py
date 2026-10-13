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
from models import Department, User
from permissions import admin_required

departments_bp = Blueprint(
    "departments",
    __name__,
    url_prefix="/departments"
)


# =====================================================
# List Departments
# =====================================================

@departments_bp.route("/")
@admin_required
def list_departments():

    departments = Department.query.order_by(
        Department.name
    ).all()

    return render_template(
        "departments/list.html",
        departments=departments,
        user=current_user
    )


# =====================================================
# Add Department
# =====================================================

@departments_bp.route(
    "/add",
    methods=["GET", "POST"]
)
@admin_required
def add_department():

    if request.method == "POST":

        name = request.form.get("name")
        description = request.form.get("description")

        existing = Department.query.filter_by(
            name=name
        ).first()

        if existing:

            flash(
                "Department already exists.",
                "warning"
            )

            return redirect(
                url_for("departments.add_department")
            )

        department = Department(
            name=name,
            description=description,
            active=True
        )

        db.session.add(department)
        db.session.commit()

        flash(
            "Department created successfully.",
            "success"
        )

        return redirect(
            url_for("departments.list_departments")
        )

    return render_template(
        "departments/add.html",
        user=current_user
    )


# =====================================================
# View Department
# =====================================================

@departments_bp.route(
    "/view/<int:department_id>"
)
@admin_required
def view_department(department_id):

    department = Department.query.get_or_404(
        department_id
    )

    return render_template(
        "departments/view.html",
        department=department,
        user=current_user
    )


# =====================================================
# Edit Department
# =====================================================

@departments_bp.route(
    "/edit/<int:department_id>",
    methods=["GET", "POST"]
)
@admin_required
def edit_department(department_id):

    department = Department.query.get_or_404(
        department_id
    )

    if request.method == "POST":

        department.name = request.form.get("name")
        department.description = request.form.get("description")
        department.active = True if request.form.get("active") else False

        db.session.commit()

        flash(
            "Department updated successfully.",
            "success"
        )

        return redirect(
            url_for("departments.list_departments")
        )

    return render_template(
        "departments/edit.html",
        department=department,
        user=current_user
    )


# =====================================================
# Delete Department
# =====================================================

@departments_bp.route(
    "/delete/<int:department_id>",
    methods=["POST"]
)
@admin_required
def delete_department(department_id):

    department = Department.query.get_or_404(
        department_id
    )

    db.session.delete(department)
    db.session.commit()

    flash(
        "Department deleted successfully.",
        "success"
    )

    return redirect(
        url_for("departments.list_departments")
    )


# =====================================================
# Department Employees
# =====================================================

@departments_bp.route(
    "/<int:department_id>/employees"
)
@admin_required
def department_users(department_id):

    department = Department.query.get_or_404(
        department_id
    )

    users = User.query.filter_by(
        department_id=department.id
    ).all()

    return render_template(
        "departments/users.html",
        department=department,
        users=users,
        user=current_user
    )