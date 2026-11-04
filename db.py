# db.py
"""Supabase media and playlist database operations for Prism."""

from supabase_client import supabase

def fetch_all_songs() -> list[dict]:
    """Retrieves all songs ordered by creation date."""
    response = supabase.table("songs").select("*").order("created_at", desc=True).execute()
    return response.data or []

def fetch_user_playlists(user_id: str) -> list[dict]:
    """Retrieves all playlists created by a specific user."""
    response = supabase.table("playlists").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data or []

def create_playlist(user_id: str, name: str) -> dict | None:
    """Creates a new playlist record linked to the active user."""
    try:
        response = supabase.table("playlists").insert({"user_id": user_id, "name": name}).execute()
        return response.data[0] if response.data else None
    except Exception as err:
        print(f"Error creating playlist: {err}")
        return None

def toggle_like_song(user_id: str, song_id: str) -> bool:
    """Toggles a song in the user's liked_songs table."""
    try:
        existing = supabase.table("liked_songs").select("*").eq("user_id", user_id).eq("song_id", song_id).execute()
        if existing.data:
            supabase.table("liked_songs").delete().eq("user_id", user_id).eq("song_id", song_id).execute()
            return False
        else:
            supabase.table("liked_songs").insert({"user_id": user_id, "song_id": song_id}).execute()
            return True
    except Exception as err:
        print(f"Error toggling song like state: {err}")
        return False

def fetch_liked_songs(user_id: str) -> list[dict]:
    """Retrieves full song records for all songs liked by the user."""
    response = supabase.table("liked_songs").select("song_id").eq("user_id", user_id).execute()
    liked_ids = [item["song_id"] for item in (response.data or [])]
    if not liked_ids:
        return []
    songs_response = supabase.table("songs").select("*").in_("id", liked_ids).execute()
    return songs_response.data or []