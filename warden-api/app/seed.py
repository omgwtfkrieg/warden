import bcrypt
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Role, User

DEFAULT_ROLES = [
    {
        "name": "admin",
        "permissions": [
            "users:read", "users:write",
            "cameras:read", "cameras:write",
            "devices:read", "devices:write",
            "config:read", "config:write",
            "streams:read",
        ],
    },
    {
        "name": "operator",
        "permissions": [
            "cameras:read", "cameras:write",
            "config:read", "config:write",
            "streams:read",
        ],
    },
    {
        "name": "viewer",
        "permissions": ["cameras:read", "streams:read"],
    },
]

DEFAULT_ADMIN_EMAIL = "admin@warden.local"
DEFAULT_ADMIN_PASSWORD = "warden-admin"


def seed(db: Session) -> None:
    roles: dict[str, Role] = {}

    for role_data in DEFAULT_ROLES:
        role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not role:
            role = Role(**role_data)
            db.add(role)
            print(f"  Created role: {role_data['name']}")
        roles[role_data["name"]] = role

    db.flush()

    admin = db.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=bcrypt.hashpw(DEFAULT_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
            role_id=roles["admin"].id,
            is_active=True,
        )
        db.add(admin)
        print(f"  Created admin user: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}")

    db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
