#!/usr/bin/env python3
"""Create a user in the application's Postgres database.

This script uses the same PBKDF2-HMAC-SHA256 parameters as `api/auth.py` (100_000 iterations)
so passwords created here will be valid for login.

Usage:
  # interactively
  python scripts/create_user.py

  # or non-interactively via env vars
  CREATE_USER_USERNAME=admin CREATE_USER_PASSWORD=secret python scripts/create_user.py
"""
import asyncio
import getpass
import hashlib
import os
import secrets

from database.models import db_manager


async def main():
    username = os.environ.get("CREATE_USER_USERNAME")
    password = os.environ.get("CREATE_USER_PASSWORD")

    if not username:
        username = input("Username: ").strip()
    if not password:
        password = getpass.getpass("Password: ")

    if not username or not password:
        print("Username and password are required")
        return

    # generate salt and hash using same method as api/auth.py
    salt = secrets.token_hex(8)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(
        "utf-8"), salt.encode("utf-8"), 100_000).hex()

    # ensure database/tables exist
    await db_manager.init_database()

    try:
        user_id = await db_manager.create_user(username, salt, pwd_hash)
        print(f"Created user '{username}' with id={user_id}")
    except Exception as e:
        print("Failed to create user:", e)


if __name__ == "__main__":
    asyncio.run(main())
