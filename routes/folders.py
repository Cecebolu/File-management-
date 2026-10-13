import os

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from extensions import db

from models import (
    Folder,
    Department,
    User
)

from permissions import admin_required, allowed_departments, deny, visible_folders
from routes.files import stored_path

folders_bp = Blueprint(
    "folders",
    __name__,
    url_prefix="/folders"
)


def form_department_id():

    """Department chosen in the form, limited to ones the user may use."""

    department_id = request.form.get("department_id", type=int)

    deny(department_id in [d.id for d in allowed_departments()])

    return department_id


# ==========================================
# List Folders
# ==========================================

@folders_bp.route("/")
@login_required
def list_folders():

    folders = visible_folders(current_user).filter(
        Folder.parent_id.is_(None)
    ).order_by(
        Folder.name
    ).all()

    return render_template(
        "folders/list.html",
        folders=folders
    )


# ==========================================
# Add Folder
# ==========================================

@folders_bp.route(
    "/add",
    methods=["GET", "POST"]
)
@login_required
def add_folder():

    parent_id = request.values.get("parent_id", type=int)

    parent = Folder.query.get_or_404(parent_id) if parent_id else None

    if parent:
        deny(current_user.can_create_subfolder(parent))
    else:
        deny(current_user.can_create_folder())

    departments = allowed_departments()

    if request.method == "POST":

        name = request.form.get("name")

        description = request.form.get(
            "description"
        )

        folder = Folder(
            name=name,
            description=description,
            parent=parent,
            # Subfolders always belong to the same department as the folder they're in
            department_id=parent.department_id if parent else form_department_id()
        )

        db.session.add(folder)

        db.session.commit()

        flash(
            "Subfolder created successfully." if parent else "Folder created successfully.",
            "success"
        )

        return redirect(
            url_for(
                "folders.view_folder",
                folder_id=folder.id
            )
        )

    return render_template(
        "folders/add.html",
        departments=departments,
        parent=parent
    )


# ==========================================
# View Folder
# ==========================================

@folders_bp.route(
    "/view/<int:folder_id>"
)
@login_required
def view_folder(folder_id):

    folder = Folder.query.get_or_404(
        folder_id
    )

    deny(current_user.can_view_folder(folder))

    files = sorted(
        folder.files,
        key=lambda f: f.uploaded_at,
        reverse=True
    )

    return render_template(
        "folders/view.html",
        folder=folder,
        files=files,
        subfolders=folder.children
    )


# ==========================================
# Edit Folder
# ==========================================

@folders_bp.route(
    "/edit/<int:folder_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_folder(folder_id):

    folder = Folder.query.get_or_404(
        folder_id
    )

    deny(current_user.can_manage_folder(folder))

    departments = allowed_departments()

    if request.method == "POST":

        folder.name = request.form.get(
            "name"
        )

        folder.description = request.form.get(
            "description"
        )

        if folder.parent_id is None:
            folder.set_department(form_department_id())

        db.session.commit()

        flash(
            "Folder updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "folders.view_folder",
                folder_id=folder.id
            )
        )

    return render_template(
        "folders/edit.html",
        folder=folder,
        departments=departments
    )


# ==========================================
# Delete Folder
# ==========================================

@folders_bp.route(
    "/delete/<int:folder_id>",
    methods=["POST"]
)
@login_required
def delete_folder(folder_id):

    folder = Folder.query.get_or_404(
        folder_id
    )

    deny(current_user.can_manage_folder(folder))

    # Subfolders and file rows cascade away, so remove their contents from disk too
    paths = [
        stored_path(file)
        for f in [folder] + folder.descendants()
        for file in f.files
    ]

    parent_id = folder.parent_id

    db.session.delete(folder)

    db.session.commit()

    for path in paths:

        if os.path.exists(path):
            os.remove(path)

    flash(
        "Folder deleted successfully.",
        "success"
    )

    if parent_id:

        return redirect(
            url_for(
                "folders.view_folder",
                folder_id=parent_id
            )
        )

    return redirect(
        url_for(
            "folders.list_folders"
        )
    )


# ==========================================
# Share Folder (admins only)
# ==========================================

@folders_bp.route(
    "/share/<int:folder_id>",
    methods=["GET", "POST"]
)
@admin_required
def share_folder(folder_id):

    folder = Folder.query.get_or_404(
        folder_id
    )

    if folder.parent_id:

        flash(
            f"Subfolders use the sharing of \"{folder.root.name}\". Changes here apply to everything inside it.",
            "info"
        )

        return redirect(
            url_for(
                "folders.share_folder",
                folder_id=folder.root.id
            )
        )

    # The folder's own department already has access, so it isn't offered
    departments = Department.query.filter(
        Department.id != folder.department_id
    ).order_by(Department.name).all()

    users = User.query.filter(
        User.active.is_(True)
    ).order_by(User.first_name, User.last_name).all()

    # Admins see every folder anyway, so only list people sharing changes anything for
    users = [
        u for u in users
        if not u.is_admin and u.department_id != folder.department_id
    ]

    if request.method == "POST":

        department_ids = set(request.form.getlist("department_ids", type=int))
        user_ids = set(request.form.getlist("user_ids", type=int))

        folder.shared_departments = [
            d for d in departments if d.id in department_ids
        ]

        folder.shared_users = [
            u for u in users if u.id in user_ids
        ]

        db.session.commit()

        flash(
            f"Sharing for \"{folder.name}\" updated.",
            "success"
        )

        return redirect(
            url_for(
                "folders.view_folder",
                folder_id=folder.id
            )
        )

    return render_template(
        "folders/share.html",
        folder=folder,
        departments=departments,
        users=users
    )
