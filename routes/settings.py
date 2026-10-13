from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from extensions import db
from models import (
    RolePermission,
    PERMISSIONS,
    CONFIGURABLE_ROLES,
    role_permissions
)
from permissions import admin_required

settings_bp = Blueprint(
    "settings",
    __name__,
    url_prefix="/settings"
)


# ==========================================
# Role Permissions
# ==========================================

@settings_bp.route(
    "/permissions",
    methods=["GET", "POST"]
)
@admin_required
def permissions():

    if request.method == "POST":

        for role in CONFIGURABLE_ROLES:

            for key in PERMISSIONS:

                # Unchecked switches aren't submitted, so absence means "off"
                allowed = f"{role}:{key}" in request.form

                db.session.merge(
                    RolePermission(
                        role=role,
                        permission=key,
                        allowed=allowed
                    )
                )

        db.session.commit()

        flash(
            "Role permissions saved.",
            "success"
        )

        return redirect(
            url_for("settings.permissions")
        )

    return render_template(
        "settings/permissions.html",
        permissions=PERMISSIONS,
        roles=CONFIGURABLE_ROLES,
        current=role_permissions()
    )
