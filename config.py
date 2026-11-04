# config.py
"""Load local Prism configuration from environment variables or .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

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
        f"Missing {missing}. Copy .env.example to .env and fill in your Supabase project values."
    )