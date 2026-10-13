"""Create the Super Admin account, or repair it.

Usage (with the venv active, after `flask db upgrade`):

    python seed.py            # create the admin if it doesn't exist yet
    python seed.py --reset    # also set a new password and re-activate an existing admin

The password is asked for when the script runs. To run it without a prompt
(e.g. in a deploy script), set the ADMIN_PASSWORD environment variable.
"""

import argparse
import os
import sys
from getpass import getpass

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app import app
from extensions import db
from models import User

USERNAME = "admin"
EMAIL = "admin@company.com"
MIN_PASSWORD_LENGTH = 8


def ask_password():

    password = os.environ.get("ADMIN_PASSWORD")

    if password:
        if len(password) < MIN_PASSWORD_LENGTH:
            sys.exit(f"ADMIN_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters.")
        return password

    while True:

        password = getpass("New admin password: ")

        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"Use at least {MIN_PASSWORD_LENGTH} characters.")
            continue

        if getpass("Repeat password: ") != password:
            print("Passwords don't match, try again.")
            continue

        return password


def main():

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reset",
        action="store_true",
        help="set a new password for an existing admin and make sure it is an active superadmin",
    )
    args = parser.parse_args()

    with app.app_context():

        if not inspect(db.engine).has_table(User.__tablename__):
            sys.exit("The database tables don't exist yet. Run `flask db upgrade` first.")

        admin = User.query.filter_by(username=USERNAME).first()

        if admin and not args.reset:
            print(f"Admin '{USERNAME}' already exists. Nothing changed.")
            print("Run `python seed.py --reset` to set a new password.")
            return

        if not admin and User.query.filter_by(email=EMAIL).first():
            sys.exit(f"Another user already uses {EMAIL}. Change EMAIL in seed.py and try again.")

        password = ask_password()

        try:

            if admin:
                # Undo anything that would keep the admin locked out
                admin.role = "superadmin"
                admin.active = True
                admin.set_password(password)
                message = "Admin password reset and account re-activated."

            else:
                admin = User(
                    first_name="System",
                    last_name="Administrator",
                    username=USERNAME,
                    email=EMAIL,
                    role="superadmin",
                    active=True,
                )
                admin.set_password(password)
                db.session.add(admin)
                message = "Super Admin created."

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()
            sys.exit(f"Could not save the admin account, nothing was changed:\n{error}")

        print(message)
        print(f"Log in with username '{USERNAME}'.")


if __name__ == "__main__":
    main()
