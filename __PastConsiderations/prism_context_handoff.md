# 💎 PRISM Media Hub - AI Handoff & Project Context

> **Project Goal:** Cross-platform desktop Media & Entertainment Hub built for university project (Option 3A).
> **Former Name:** `spotibai` → **New Identity:** `Prism`

---

## 1. Project Overview & Scope (Option 3A)

The project satisfies requirement **Option 3A: Media and Entertainment**, covering three unified media components inside a single desktop application without external application redirects:

1. 🎵 **3A.2 Music & Audio:** Audio streaming engine powered by `pygame-ce` connected to a Supabase database. *(Status: Core complete)*
2. 🎬 **3A.1 Movies & TV Shows:** TMDB-backed title catalogue plus local embedded video playback powered by PyQt6 (`QMediaPlayer` & `QVideoWidget`). *(Status: Catalogue UI and local playback implemented; test with the configured API key and a local video file.)*
3. 🎮 **3A.3 Games & Arcade:** Interactive mini-game integrated natively inside a PyQt layout frame. *(Status: Planned)*

---

## 2. Technical Stack

* **Language/Runtime:** Python 3.15
* **GUI Framework:** PyQt6 (`PyQt6.QtWidgets`, `PyQt6.QtCore`, `PyQt6.QtMultimedia`)
* **Audio Engine:** `pygame-ce` (`pygame.mixer`)
* **Backend Services:** Supabase and SQLite
  * **Identity and sessions:** Supabase Auth remains the identity provider so music, playlists, and likes keep using the matching Supabase user ID and session.
  * **Local account data:** SQLite stores the email and password hash, salt, and KDF iteration count in the user's local application data folder. Existing Supabase accounts are added to SQLite after their first successful sign-in.
  * **Password security:** Use a salted password KDF available in Python's built-in `hashlib` (such as `pbkdf2_hmac`) to hash and verify passwords. Never store plaintext passwords or unsalted fast hashes.
  * **Supabase Database (PostgreSQL):** `songs`, `playlists`, and `liked_songs` tables.
  * **Supabase Storage:** Direct HTTPS raw audio streaming.
* **Movie catalogue:** TMDB movie and TV search API. Store `TMDB_API_KEY` in local `.env`, never in source control. Show the approved TMDB logo and the required non-endorsement notice in Credits.

---

## 3. Brand Identity & Visual Theme (Prism Cyan)

* **Primary Accent:** Electric Cyan (`#00D2FF`)
* **Background:** Deep Obsidian (`#0F0F12`)
* **Widget/Card Surface:** Dark Slate (`#1A1A24`)
* **Borders & Dividers:** Subtle Slate (`#2E2E3E`)
* **Text Colors:** White (`#FFFFFF`) for titles, Muted Slate (`#7A7A95`) as the palette reference. Use a contrast-adjusted slate (`#B7B7C7`) for small labels on dark surfaces.
* **Interface direction:** Keep the deep background as the media canvas; use a narrow cyan edge to mark the active destination and the currently available music route. The music destination gets more visual weight because it is usable now; future media destinations stay restrained until implemented. Use Segoe UI for native desktop legibility, with Qt's system fallback on other platforms. A short fade on page changes softens navigation without competing with media content. The first login/dashboard pass uses ENERGY 2 / RHYTHM 2 / MOTION 1.

---

## 4. Current Workspace Architecture

```text
Finals Project (SpotifyClone)/
│
├── config.py             # Holds SUPABASE_URL and SUPABASE_KEY
├── supabase_client.py    # Initializes global Supabase client instance
├── auth.py               # Handles user authentication (login_user, register_user)
├── db.py                 # Handles table queries (fetch_all_songs, fetch_user_playlists, etc.)
├── player.py             # Audio playback logic using pygame.mixer.music
├── main.py               # Main application entry point & window router
│
└── ui/
    ├── login_window.py   # Login UI styled with Prism Electric Cyan theme
    ├── sidebar.py        # Navigation menu widget
    ├── player_bar.py     # Bottom persistent media control bar widget
    └── main_window.py    # Main dashboard container loading song tables & controls
```

---

## 5. Verified File Implementations

### `auth.py`
Contains `register_user(email, password)` and `login_user(email, password)`. Supabase Auth provides the session and user ID; SQLite stores only the local email and salted PBKDF2 password hash metadata. Existing Supabase users are migrated to local hash storage after successful authentication. Plaintext passwords and unsalted fast hashes must never be stored.

### `db.py`
Functions available:
- `fetch_all_songs()`: Returns list of available tracks.
- `fetch_user_playlists(user_id)`: Returns user playlists.
- `create_playlist(user_id, name)`: Creates a new playlist record.
- `toggle_like_song(user_id, song_id)`: Toggles song in `liked_songs`.
- `fetch_liked_songs(user_id)`: Returns full song data for liked tracks.

### `player.py`
Contains `AudioPlayer` class:
- `play_url(audio_url, song_data)`: Streams raw audio bytes over HTTPS using `urllib.request` and `pygame.mixer.music`.
- `pause()`, `resume()`, `stop()`, `set_volume(value)`.

---

## 6. Development Roadmap for AI Agent

When continuing development in VS Code, follow this implementation order:

1. **Refactor `ui/main_window.py` for Multi-Tab Media (QStackedWidget):**
   - Replace the static central widget with a `QStackedWidget`.
   - Page 0: Music & Audio View (existing song table).
   - Page 1: Movies & TV View.
   - Page 2: Arcade & Games View.

2. **Update `ui/sidebar.py` Navigation:**
   - Add tab selector buttons: `🎵 Music`, `🎬 Movies & TV`, `🎮 Arcade`.
   - Apply Prism Electric Cyan (`#00D2FF`) styling.

3. **Build Video Player (`ui/video_view.py`):**
   - Implement `QMediaPlayer` and `QVideoWidget` from `PyQt6.QtMultimedia` & `PyQt6.QtMultimediaWidgets`.
   - Add playback controls (play/pause, timeline slider, volume).
   - Current first pass: `ui/view_view.py` hosts a TMDB movie/TV catalogue and a local video player. Internet playback remains a separate future feature.

4. **Build In-App Game Module (`ui/game_view.py`):**
   - Implement an in-app interactive mini-game tab (e.g., Music Trivia or Rhythm mini-game).

---
*Created for VS Code AI Extension context loading (Continue / Cline / Copilot).*