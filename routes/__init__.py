from .auth import auth_bp
from .dashboard import dashboard_bp
from .users import users_bp
from .departments import departments_bp
from .folders import folders_bp
from .files import files_bp
from .reports import reports_bp
from .api import api_bp
from .settings import settings_bp

blueprints = [

    auth_bp,

    dashboard_bp,

    users_bp,

    departments_bp,

    folders_bp,

    files_bp,

    reports_bp,

    api_bp,

    settings_bp

]