"""Add the standard departments.

Usage (with the venv active, after `flask db upgrade`):

    python seed_departments.py

Departments that already exist (same name, any capitalisation) are left as they are,
so it is safe to run more than once.
"""

import sys

from sqlalchemy import func, inspect
from sqlalchemy.exc import SQLAlchemyError

from app import app
from extensions import db
from models import Department

DEPARTMENTS = [
    ("Management", "Board papers, strategy and company-wide policies."),
    ("Finance", "Invoices, payments, budgets, KRA and tax records, and audits."),
    ("Human Resources", "Staff records, contracts, leave, payroll and recruitment."),
    ("Sales & Marketing", "Proposals, client contracts, price lists, campaigns and brand assets."),
    ("Customer Support", "Client onboarding, support procedures and escalation guides."),
    ("Technical / Engineering", "Server documentation, network diagrams, procedures and change logs."),
    ("Development", "Specifications, API documentation and release notes."),
    ("Administration & Operations", "Office, assets, suppliers, licences and insurance."),
]


def main():

    with app.app_context():

        if not inspect(db.engine).has_table(Department.__tablename__):
            sys.exit("The database tables don't exist yet. Run `flask db upgrade` first.")

        added = []

        try:

            for name, description in DEPARTMENTS:

                exists = Department.query.filter(
                    func.lower(Department.name) == name.lower()
                ).first()

                if exists:
                    print(f"  skipped  {name} (already exists)")
                    continue

                db.session.add(Department(name=name, description=description, active=True))
                added.append(name)
                print(f"  added    {name}")

            db.session.commit()

        except SQLAlchemyError as error:
            db.session.rollback()
            sys.exit(f"Could not add the departments, nothing was changed:\n{error}")

        print(f"\n{len(added)} department(s) added.")


if __name__ == "__main__":
    main()
