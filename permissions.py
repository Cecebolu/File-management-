from functools import wraps

from flask import flash, redirect, url_for, abort
from flask_login import current_user, login_required

from sqlalchemy import or_

from extensions import db
from models import Folder, File, User, Department


def admin_required(view):

    """Only superadmins and admins may open this page."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):

        if not current_user.is_admin:

            flash("You don't have permission to access that page.", "danger")

            return redirect(url_for("dashboard.dashboard"))

        return view(*args, **kwargs)

    return wrapped


def deny(condition):

    """Abort with 403 Forbidden unless condition holds."""

    if not condition:
        abort(403)


def allowed_departments():

    """Departments the current user may put folders in."""

    if current_user.is_admin:

        return Department.query.order_by(
            Department.name
        ).all()

    return [current_user.department] if current_user.department else []


def folder_visibility_filter(user):

    """SQL condition for folders the user may see, or None when they see everything.

    A folder is visible when it is in the user's department, or when its
    top-level folder is shared with the user or the user's department.
    """

    if user.is_admin or user.has_permission("view_all_departments"):
        return None

    shared = [Folder.shared_users.any(User.id == user.id)]

    if user.department_id is not None:
        shared.append(Folder.shared_departments.any(Department.id == user.department_id))

    shared_root_ids = {
        folder_id for (folder_id,) in
        db.session.query(Folder.id).filter(or_(*shared))
    }

    parents = dict(db.session.query(Folder.id, Folder.parent_id))

    def root_id(folder_id):

        while parents.get(folder_id) is not None:
            folder_id = parents[folder_id]

        return folder_id

    visible_ids = [
        folder_id for folder_id in parents
        if root_id(folder_id) in shared_root_ids
    ]

    if user.department_id is None:
        return Folder.id.in_(visible_ids)

    return or_(
        Folder.department_id == user.department_id,
        Folder.id.in_(visible_ids)
    )


def visible_folders(user):

    """Folders the user may see: own department, plus anything shared with them."""

    query = Folder.query

    condition = folder_visibility_filter(user)

    if condition is not None:
        query = query.filter(condition)

    return query


def visible_files(user):

    """Files in the folders the user may see."""

    query = File.query

    condition = folder_visibility_filter(user)

    if condition is not None:
        query = query.join(File.folder).filter(condition)

    return query
