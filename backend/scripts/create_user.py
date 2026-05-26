"""
Create initial user for the voice chat application.
Usage: python -m scripts.create_user --username admin --password secret123
"""

import asyncio
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tortoise import Tortoise
from app.config import DATABASE_URL
from app.models.user import User
from app.core.auth import hash_password


async def main(username: str, password: str, role: str = "admin"):
    await Tortoise.init(db_url=DATABASE_URL, modules={"models": ["app.models.user"]})
    await Tortoise.generate_schemas()

    existing = await User.filter(username=username).first()
    if existing:
        print(f"User '{username}' already exists. Updating password and role.")
        existing.password_hash = hash_password(password)
        existing.role = role
        await existing.save()
    else:
        await User.create(username=username, password_hash=hash_password(password), role=role)
        print(f"User '{username}' created with role '{role}'.")

    await Tortoise.close_connections()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update a user")
    parser.add_argument("--username", required=True, help="Login username")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--role", default="admin", choices=("admin", "user"), help="User role (default: admin)")
    args = parser.parse_args()

    asyncio.run(main(args.username, args.password, args.role))
