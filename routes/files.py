import json
import os
import re
import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
    send_from_directory
)

from flask_login import (
    login_required,
    current_user
)

from werkzeug.utils import secure_filename

from extensions import db
from models import File, Folder
from permissions import allowed_departments, deny, visible_files, visible_folders


files_bp = Blueprint(
    "files",
    __name__,
    url_prefix="/files"
)


def stored_path(file):
    """Absolute path of a file on disk. Only the basename of filepath is used,
    so rows created before uploads moved out of static/ still resolve."""

    return os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        os.path.basename(file.filepath)
    )


# ==========================================
# List Files
# ==========================================

@files_bp.route("/")
@login_required
def list_files():

    files = visible_files(current_user).order_by(
        File.uploaded_at.desc()
    ).all()

    return render_template(
        "files/list.html",
        files=files
    )


# ==========================================
# Upload Files
# ==========================================

# Files operating systems drop into folders on their own; never worth uploading
SYSTEM_FILES = {"thumbs.db", "desktop.ini", ".ds_store"}


def save_upload(uploaded_file, folder, name, saved_paths):
    """Save one uploaded file to disk and add its File row (not committed).
    The disk path is appended to saved_paths so a failed upload can clean up."""

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    # secure_filename drops non-ASCII names entirely, so keep the extension at least
    filename = secure_filename(name) or "file" + os.path.splitext(name)[1].lower()

    # Unique stored name so same-named uploads don't overwrite each other
    stored_name = f"{uuid.uuid4().hex}_{filename}"

    filepath = os.path.join(
        upload_folder,
        stored_name
    )

    uploaded_file.save(filepath)

    saved_paths.append(filepath)

    db.session.add(File(

        filename=filename,

        filepath=stored_name,

        file_size=os.path.getsize(filepath),

        file_type=uploaded_file.content_type,

        folder=folder,

        uploaded_by=current_user.id

    ))


def remove_saved(saved_paths):
    """Delete files written to disk by an upload that then failed."""

    for filepath in saved_paths:
        if os.path.exists(filepath):
            os.remove(filepath)


def path_parts(path):
    """Folder and file names from a browser-supplied relative path,
    without empty, '.' or '..' parts."""

    parts = (part.strip() for part in re.split(r"[\\/]", path))

    return [part for part in parts if part and part not in (".", "..")]


def folder_destinations(folders):
    """Where the current user may put an uploaded folder, as (value, label) pairs."""

    destinations = []

    if current_user.can_create_folder():

        destinations += [
            (f"department:{d.id}", f"{d.name} (top level)")
            for d in allowed_departments()
        ]

    destinations += [
        (f"folder:{f.id}", f.path)
        for f in folders
        if current_user.can_create_subfolder(f) and current_user.can_upload(f)
    ]

    return destinations


def upload_folder_tree(uploaded_files, destination, destinations):
    """Recreate an uploaded folder (and its subfolders) under the destination.
    Returns (top uploaded folder, file count). Folders that already exist with
    the same name are reused, so uploading the same folder again adds to it."""

    deny(destination in [value for value, _ in destinations])

    kind, _, target_id = destination.partition(":")

    if kind == "folder":
        parent = db.session.get(Folder, int(target_id))
        department_id = parent.department_id
    else:
        parent = None
        department_id = int(target_id)

    try:
        paths = json.loads(request.form.get("paths") or "[]")
    except ValueError:
        abort(400)

    if not isinstance(paths, list) or len(paths) != len(uploaded_files):
        abort(400)

    known = {}

    def child_folder(parent, name):

        name = name[:150]
        key = (parent, name.lower())

        if key not in known:

            existing = Folder.query.filter(
                Folder.department_id == department_id,
                Folder.parent_id == (parent.id if parent else None),
                db.func.lower(Folder.name) == name.lower()
            ).first() if parent is None or parent.id else None

            known[key] = existing or Folder(
                name=name,
                parent=parent,
                department_id=department_id
            )

            db.session.add(known[key])

        return known[key]

    top = None
    saved_paths = []

    try:

        with db.session.no_autoflush:

            for uploaded_file, path in zip(uploaded_files, paths):

                parts = path_parts(str(path))

                # Folder uploads always give at least "Folder/file"
                if len(parts) < 2 or parts[-1].lower() in SYSTEM_FILES:
                    continue

                folder = parent

                for name in parts[:-1]:
                    folder = child_folder(folder, name)

                top = top or child_folder(parent, parts[0])

                save_upload(uploaded_file, folder, parts[-1], saved_paths)

        db.session.commit()

    except Exception:

        db.session.rollback()
        remove_saved(saved_paths)
        raise

    return top, len(saved_paths)


@files_bp.route(
    "/upload",
    methods=["GET", "POST"]
)
@login_required
def upload_file():

    deny(current_user.can_upload())

    folders = sorted(
        visible_folders(current_user).all(),
        key=lambda f: f.path.lower()
    )

    destinations = folder_destinations(folders)

    if request.method == "POST":

        mode = request.form.get("mode", "files")

        uploaded_files = [
            f for f in request.files.getlist("files")
            if f.filename
        ]

        if not uploaded_files:

            flash(
                "Please select a folder." if mode == "folder" else "Please select at least one file.",
                "danger"
            )

            return redirect(
                url_for("files.upload_file", mode=mode)
            )

        if mode == "folder":

            top, uploaded_count = upload_folder_tree(
                uploaded_files,
                request.form.get("destination", ""),
                destinations
            )

            if top is None:

                flash(
                    "That folder has no files to upload. Empty folders can't be uploaded.",
                    "warning"
                )

                return redirect(
                    url_for("files.upload_file", mode=mode)
                )

            flash(
                f"Folder \"{top.name}\" uploaded with {uploaded_count} file(s).",
                "success"
            )

            return redirect(
                url_for("folders.view_folder", folder_id=top.id)
            )

        folder_id = request.form.get("folder_id", type=int)

        deny(folder_id in [f.id for f in folders])

        folder = db.session.get(Folder, folder_id)

        saved_paths = []

        try:

            for uploaded_file in uploaded_files:
                save_upload(uploaded_file, folder, uploaded_file.filename, saved_paths)

            db.session.commit()

        except Exception:

            db.session.rollback()
            remove_saved(saved_paths)
            raise

        flash(
            f"{len(saved_paths)} file(s) uploaded successfully.",
            "success"
        )

        return redirect(
            url_for("folders.view_folder", folder_id=folder_id)
        )

    selected_folder_id = request.args.get("folder_id", type=int)

    return render_template(
        "files/upload.html",
        folders=folders,
        destinations=destinations,
        selected_folder_id=selected_folder_id,
        selected_destination=f"folder:{selected_folder_id}",
        mode=request.args.get("mode", "files")
    )


# ==========================================
# View File
# ==========================================

@files_bp.route("/view/<int:file_id>")
@login_required
def view_file(file_id):

    file = File.query.get_or_404(file_id)

    deny(current_user.can_view_folder(file.folder))

    return render_template(
        "files/view.html",
        file=file
    )


# ==========================================
# Edit File
# ==========================================

@files_bp.route(
    "/edit/<int:file_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_file(file_id):

    file = File.query.get_or_404(file_id)

    deny(current_user.can_modify_file(file))

    folders = sorted(
        visible_folders(current_user).all(),
        key=lambda f: f.path.lower()
    )

    if request.method == "POST":

        folder_id = request.form.get("folder_id", type=int)

        deny(folder_id in [f.id for f in folders])

        file.folder_id = folder_id

        db.session.commit()

        flash(
            "File updated successfully.",
            "success"
        )

        return redirect(
            url_for("files.list_files")
        )

    return render_template(
        "files/edit.html",
        file=file,
        folders=folders
    )


# ==========================================
# Delete File
# ==========================================

@files_bp.route(
    "/delete/<int:file_id>",
    methods=["POST"]
)
@login_required
def delete_file(file_id):

    file = File.query.get_or_404(file_id)

    deny(current_user.can_modify_file(file))

    path = stored_path(file)

    if os.path.exists(path):

        os.remove(path)

    db.session.delete(file)

    db.session.commit()

    flash(
        "File deleted successfully.",
        "success"
    )

    next_url = request.form.get("next", "")

    # Only follow local paths, never another site
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = url_for("files.list_files")

    return redirect(next_url)


# ==========================================
# Download File
# ==========================================

@files_bp.route("/download/<int:file_id>")
@login_required
def download_file(file_id):

    file = File.query.get_or_404(file_id)

    deny(current_user.can_download(file))

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        os.path.basename(file.filepath),
        as_attachment=True,
        download_name=file.filename
    )