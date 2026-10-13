from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import (
    User,
    Department,
    Folder,
    File,
    ActivityLog
)

from permissions import visible_files, visible_folders

dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.is_admin:
        return admin_dashboard()

    return employee_dashboard()


def admin_dashboard():

    # =====================================
    # Organisation-wide statistics
    # =====================================

    total_users = User.query.count()

    total_departments = Department.query.count()

    total_folders = Folder.query.count()

    total_files = File.query.count()

    active_users = User.query.filter_by(
        active=True
    ).count()

    inactive_users = User.query.filter_by(
        active=False
    ).count()

    recent_activity = ActivityLog.query.order_by(
        ActivityLog.created_at.desc()
    ).limit(10).all()

    latest_users = User.query.order_by(
        User.created_at.desc()
    ).limit(5).all()

    latest_departments = Department.query.order_by(
        Department.created_at.desc()
    ).limit(5).all()

    latest_folders = Folder.query.order_by(
        Folder.created_at.desc()
    ).limit(5).all()

    latest_files = File.query.order_by(
        File.uploaded_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",

        user=current_user,

        total_users=total_users,
        total_departments=total_departments,
        total_folders=total_folders,
        total_files=total_files,

        active_users=active_users,
        inactive_users=inactive_users,

        latest_users=latest_users,
        latest_departments=latest_departments,
        latest_folders=latest_folders,
        latest_files=latest_files,

        recent_activity=recent_activity
    )


def employee_dashboard():

    # =====================================
    # Department-scoped view for managers and employees
    # =====================================

    department = current_user.department

    folders = visible_folders(current_user).filter(
        Folder.parent_id.is_(None)
    ).order_by(
        Folder.name
    ).all()

    department_files = visible_files(current_user)

    my_files = File.query.filter_by(
        uploaded_by=current_user.id
    )

    colleagues = User.query.filter(
        User.department_id == current_user.department_id,
        User.id != current_user.id,
        User.active.is_(True)
    ).order_by(User.first_name).all() if department else []

    return render_template(
        "dashboard_employee.html",

        user=current_user,
        department=department,

        folders=folders,
        total_department_files=department_files.count(),
        total_my_files=my_files.count(),

        recent_files=department_files.order_by(
            File.uploaded_at.desc()
        ).limit(6).all(),

        my_recent_files=my_files.order_by(
            File.uploaded_at.desc()
        ).limit(5).all(),

        colleagues=colleagues
    )
