"""Authentication using Supabase identities and locally stored password hashes."""

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

from supabase_client import supabase

PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16
LOGGER = logging.getLogger(__name__)
_LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
DATABASE_PATH = _LOCAL_APP_DATA / "Prism" / "users.sqlite3"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                hash_iterations INTEGER NOT NULL
            )
            """
        )
        connection.commit()
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def _hash_password(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def _get_local_user(email: str) -> sqlite3.Row | None:
    with closing(_connect()) as connection:
        return connection.execute(
            "SELECT id, email, password_salt, password_hash, hash_iterations "
            "FROM users WHERE email = ?",
            (email,),
        ).fetchone()


def _store_local_user(user_id: str, email: str, password: str) -> None:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    password_hash = _hash_password(password, salt, PASSWORD_HASH_ITERATIONS)
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO users (id, email, password_salt, password_hash, hash_iterations)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, email, salt, password_hash, PASSWORD_HASH_ITERATIONS),
            )


def _sign_in_with_supabase(email: str, password: str) -> tuple[bool, str, str | None]:
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as err:
        return False, str(err), None

    if response.user and response.session:
        return True, "Login successful.", response.user.id
    return False, "Invalid email or password.", None


def register_user(email: str, password: str) -> tuple[bool, str]:
    """Creates a Supabase identity and stores its salted password hash in SQLite."""
    normalized_email = email.strip().casefold()
    if not normalized_email or not password.strip():
        return False, "Email and password cannot be empty."

    try:
        if _get_local_user(normalized_email):
            return False, "An account with that email already exists. Sign in instead."
    except sqlite3.Error:
        return False, "Prism could not access its local account database."

    try:
        response = supabase.auth.sign_up(
            {"email": normalized_email, "password": password}
        )
    except Exception as err:
        return False, str(err)

    if not response.user:
        return False, "Registration failed. Please try again."

    try:
        _store_local_user(response.user.id, normalized_email, password)
    except sqlite3.Error:
        return (
            False,
            "Your online account was created, but Prism could not save its local account record. "
            "Check local storage permissions before trying again.",
        )

    return True, "Account created successfully. You can now sign in."


def login_user(email: str, password: str) -> tuple[bool, str, str | None]:
    """Verifies the local hash, signs in remotely, and migrates older accounts on success."""
    normalized_email = email.strip().casefold()
    if not normalized_email or not password:
        return False, "Email and password are required.", None

    try:
        local_user = _get_local_user(normalized_email)
    except sqlite3.Error:
        return False, "Prism could not access its local account database.", None

    if local_user:
        candidate_hash = _hash_password(
            password,
            local_user["password_salt"],
            local_user["hash_iterations"],
        )
        if not hmac.compare_digest(candidate_hash, local_user["password_hash"]):
            return False, "Invalid email or password.", None

    success, message, user_id = _sign_in_with_supabase(normalized_email, password)
    if not success or not user_id:
        return False, message, None

    if not local_user:
        try:
            _store_local_user(user_id, normalized_email, password)
        except sqlite3.Error:
            try:
                supabase.auth.sign_out()
            except Exception:
                LOGGER.exception("Could not clear the Supabase session after local account storage failed")
            return (
                False,
                "Prism signed you in online but could not save your local account record. "
                "Check local storage permissions and try again.",
                None,
            )

    return True, "Login successful.", user_id


def logout_user() -> tuple[bool, str]:
    """Ends the active Supabase session."""
    try:
        supabase.auth.sign_out()
        return True, "Logged out successfully."
    except Exception as err:
        return False, str(err)
