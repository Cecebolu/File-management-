from datetime import datetime

from flask import g, has_request_context
from flask_login import UserMixin

from extensions import db, login_manager, bcrypt


# Super Admins manage the whole organisation
ADMIN_ROLES = ("superadmin",)

ROLES = ("superadmin", "manager", "employee")

# Roles whose permissions an admin can switch on and off (admins always have everything)
CONFIGURABLE_ROLES = ("manager", "employee")

# permission key -> (label, description, default per role)
PERMISSIONS = {
    "view_all_departments": (
        "See all departments",
        "Browse folders and files from every department, not just their own.",
        {"manager": False, "employee": False},
    ),
    "create_folders": (
        "Create folders",
        "Create new folders in their own department.",
        {"manager": True, "employee": False},
    ),
    "manage_folders": (
        "Edit and delete folders",
        "Rename, move or delete folders in their own department.",
        {"manager": True, "employee": False},
    ),
    "upload_files": (
        "Upload files",
        "Upload files into folders they can see.",
        {"manager": True, "employee": True},
    ),
    "download_files": (
        "Download files",
        "Download files from folders they can see.",
        {"manager": True, "employee": True},
    ),
    "modify_own_files": (
        "Edit and delete their own files",
        "Move or delete files they uploaded themselves.",
        {"manager": True, "employee": True},
    ),
    "modify_department_files": (
        "Edit and delete anyone's files in their department",
        "Move or delete files uploaded by colleagues in their own department.",
        {"manager": True, "employee": False},
    ),
}


# =====================================================
# Folder sharing (many-to-many)
# =====================================================

folder_department_shares = db.Table(
    "folder_department_shares",
    db.Column("folder_id", db.Integer, db.ForeignKey("folders.id", ondelete="CASCADE"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
)

folder_user_shares = db.Table(
    "folder_user_shares",
    db.Column("folder_id", db.Integer, db.ForeignKey("folders.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


# =====================================================
# Role Permission Model
# =====================================================

class RolePermission(db.Model):

    """An admin's override of a permission default for a role."""

    __tablename__ = "role_permissions"

    role = db.Column(
        db.String(50),
        primary_key=True
    )

    permission = db.Column(
        db.String(100),
        primary_key=True
    )

    allowed = db.Column(
        db.Boolean,
        nullable=False
    )


def role_permissions():

    """{role: {permission: allowed}} with defaults filled in, cached per request."""

    if has_request_context() and "role_permissions" in g:
        return g.role_permissions

    table = {
        role: {key: spec[2][role] for key, spec in PERMISSIONS.items()}
        for role in CONFIGURABLE_ROLES
    }

    for row in RolePermission.query.all():

        if row.role in table and row.permission in PERMISSIONS:
            table[row.role][row.permission] = row.allowed

    if has_request_context():
        g.role_permissions = table

    return table


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(User, int(user_id))


# =====================================================
# Department Model
# =====================================================

class Department(db.Model):

    __tablename__ = "departments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    users = db.relationship(
        "User",
        back_populates="department",
        lazy=True
    )

    folders = db.relationship(
        "Folder",
        back_populates="department",
        cascade="all, delete-orphan",
        lazy=True
    )

    def __repr__(self):

        return f"<Department {self.name}>"


# =====================================================
# User Model
# =====================================================

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    first_name = db.Column(
        db.String(100),
        nullable=False
    )

    last_name = db.Column(
        db.String(100),
        nullable=False
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        default="employee",
        nullable=False
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id")
    )

    active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    department = db.relationship(
        "Department",
        back_populates="users"
    )

    uploaded_files = db.relationship(
        "File",
        back_populates="uploader",
        lazy=True
    )

    activity_logs = db.relationship(
        "ActivityLog",
        back_populates="user",
        lazy=True
    )

    def set_password(self, password):

        self.password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

    def check_password(self, password):

        return bcrypt.check_password_hash(
            self.password,
            password
        )

    @property
    def is_active(self):

        return self.active

    # -------------------------------------------------
    # Permissions
    # -------------------------------------------------

    @property
    def is_superadmin(self):

        return self.role == "superadmin"

    @property
    def is_admin(self):

        return self.role in ADMIN_ROLES

    @property
    def is_manager(self):

        return self.role == "manager"

    def has_permission(self, permission):

        if self.is_admin:
            return True

        return role_permissions().get(self.role, {}).get(permission, False)

    def in_own_department(self, folder):

        return (
            self.department_id is not None
            and folder.department_id == self.department_id
        )

    def can_view_folder(self, folder):

        if self.is_admin or self.has_permission("view_all_departments"):
            return True

        root = folder.root

        return (
            self.in_own_department(folder)
            or self in root.shared_users
            or (self.department is not None and self.department in root.shared_departments)
        )

    def can_create_folder(self):

        return self.is_admin or (
            self.department_id is not None
            and self.has_permission("create_folders")
        )

    def can_create_subfolder(self, parent):

        return self.is_admin or (
            self.in_own_department(parent)
            and self.has_permission("create_folders")
        )

    def can_manage_folder(self, folder):

        """Edit or delete a folder."""

        return self.is_admin or (
            self.in_own_department(folder)
            and self.has_permission("manage_folders")
        )

    def can_upload(self, folder=None):

        if not self.has_permission("upload_files"):
            return False

        return folder is None or self.can_view_folder(folder)

    def can_download(self, file):

        return (
            self.has_permission("download_files")
            and self.can_view_folder(file.folder)
        )

    def can_modify_file(self, file):

        """Move or delete a file."""

        if self.is_admin:
            return True

        if not self.can_view_folder(file.folder):
            return False

        if file.uploaded_by == self.id and self.has_permission("modify_own_files"):
            return True

        return (
            self.in_own_department(file.folder)
            and self.has_permission("modify_department_files")
        )

    def __repr__(self):

        return f"<User {self.username}>"


# =====================================================
# Folder Model
# =====================================================

class Folder(db.Model):

    __tablename__ = "folders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=False
    )

    # Empty for top-level folders; subfolders point at the folder they live in
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("folders.id", ondelete="CASCADE"),
        index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    department = db.relationship(
        "Department",
        back_populates="folders"
    )

    parent = db.relationship(
        "Folder",
        remote_side=[id],
        back_populates="children"
    )

    children = db.relationship(
        "Folder",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Folder.name",
        lazy=True
    )

    files = db.relationship(
        "File",
        back_populates="folder",
        cascade="all, delete-orphan",
        lazy=True
    )

    shared_departments = db.relationship(
        "Department",
        secondary=folder_department_shares,
        backref=db.backref("shared_folders", lazy=True),
        lazy=True
    )

    shared_users = db.relationship(
        "User",
        secondary=folder_user_shares,
        backref=db.backref("shared_folders", lazy=True),
        lazy=True
    )

    @property
    def ancestors(self):

        """Folders above this one, top-level first."""

        chain = []
        folder = self.parent

        while folder is not None:
            chain.insert(0, folder)
            folder = folder.parent

        return chain

    @property
    def root(self):

        """The top-level folder. Sharing set there applies to everything inside it."""

        return self.ancestors[0] if self.parent_id else self

    @property
    def path(self):

        return " / ".join(f.name for f in self.ancestors + [self])

    def descendants(self):

        """Every subfolder at any depth below this one."""

        found = []

        for child in self.children:
            found.append(child)
            found.extend(child.descendants())

        return found

    def set_department(self, department_id):

        """Move this folder and everything inside it to a department."""

        self.department_id = department_id

        for child in self.descendants():
            child.department_id = department_id

    def __repr__(self):

        return f"<Folder {self.name}>"


# =====================================================
# File Model
# =====================================================

class File(db.Model):

    __tablename__ = "files"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    filepath = db.Column(
        db.String(500),
        nullable=False
    )

    file_size = db.Column(
        db.Integer
    )

    file_type = db.Column(
        db.String(100)
    )

    folder_id = db.Column(
        db.Integer,
        db.ForeignKey("folders.id"),
        nullable=False
    )

    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    folder = db.relationship(
        "Folder",
        back_populates="files"
    )

    uploader = db.relationship(
        "User",
        back_populates="uploaded_files"
    )

    def __repr__(self):

        return f"<File {self.filename}>"


# =====================================================
# Activity Log Model
# =====================================================

class ActivityLog(db.Model):

    __tablename__ = "activity_logs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    action = db.Column(
        db.String(255),
        nullable=False
    )

    details = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="activity_logs"
    )

    def __repr__(self):

        return f"<ActivityLog {self.action}>"