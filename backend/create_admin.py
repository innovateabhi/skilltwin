from datetime import datetime

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


ADMIN_EMAIL = "admin.skilltwin@gmail.com"
ADMIN_PASSWORD = "0"


def create_admin():
    db = SessionLocal()

    try:
        existing = (
            db.query(User)
            .filter(User.email == ADMIN_EMAIL)
            .first()
        )

        if existing:
            print("Admin account already exists.")
            print(f"Email: {existing.email}")
            print(f"Role: {existing.role}")
            print(f"Active: {existing.is_active}")
            return

        admin = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("===================================")
        print("SkillTwin Admin Created Successfully")
        print("===================================")
        print(f"User ID : {admin.id}")
        print(f"Email   : {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")
        print("Role    : admin")
        print("Active  : True")
        print("Verified: True")
        print("===================================")

    except Exception as error:
        db.rollback()
        print("Failed to create admin:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()