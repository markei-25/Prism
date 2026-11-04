# config.py
"""Load local Prism configuration from environment variables or .env."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    config_directory = Path(sys.executable).resolve().parent
else:
    config_directory = Path(__file__).resolve().parent

load_dotenv(config_directory / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()
JAMENDO_CLIENT_ID = os.getenv("JAMENDO_CLIENT_ID", "e6c53c81").strip()

missing_settings = [
    name
    for name, value in (
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_KEY", SUPABASE_KEY),
    )
    if not value
]

if missing_settings:
    missing = ", ".join(missing_settings)
    raise RuntimeError(
        f"Missing {missing}. Copy .env.example to .env beside Prism and fill in "
        "your Supabase project values."
    )