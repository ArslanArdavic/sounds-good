#!/usr/bin/env python3
"""Print one-time ENCRYPTION_KEY (Fernet) and SECRET_KEY (JWT signing) for backend .env / App Platform."""

from __future__ import annotations

import secrets

from cryptography.fernet import Fernet


def main() -> None:
    enc = Fernet.generate_key().decode()
    jwt_secret = secrets.token_urlsafe(32)
    print("Add these to your backend environment (do not commit):")
    print()
    print(f"ENCRYPTION_KEY={enc}")
    print(f"SECRET_KEY={jwt_secret}")


if __name__ == "__main__":
    main()
