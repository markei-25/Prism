# Prism Media Hub

Prism is a Python desktop media hub for music and audio, movies and TV, and arcade games. It is a university project following Option 3A.

## Current status

- Music and audio: Jamendo search and streaming, recursive playback from a selected local folder, and the existing Supabase library available as a separate legacy source.
- Movies and TV: TMDB title catalogue and embedded local video playback.
- Arcade: Snake is playable inside Prism; more games can be added later.

The Snake game adapts PyBox gameplay under its MIT license. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for attribution and license terms.

## Requirements

- Windows (the current app has been developed and run on Windows)
- Python 3.15, matching the project handoff
- A Supabase project configured for authentication and the playlist migration below

## Set up on Windows

1. Clone the repository and open PowerShell in its folder.
2. Create and activate a virtual environment:

   ```powershell
   py -3.15 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Create your local configuration file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edit `.env` and set `SUPABASE_URL` and `SUPABASE_KEY` to the project's Supabase URL and publishable key. Never put a Supabase `service_role` key in this desktop client or commit `.env`.

   In the Supabase SQL Editor, run [`supabase/migrations/202606080001_music_playlists.sql`](./supabase/migrations/202606080001_music_playlists.sql) once. It creates account-owned playlists and Jamendo playlist entries protected by row-level security. If an existing `public.playlists` table uses non-UUID `id` or `user_id` columns, the migration stops with an explicit error; do not drop that table, since it may contain data.

   If you use the **Supabase library** or **Liked Songs** destination, also run [`supabase/migrations/202611060001_legacy_music_library.sql`](./supabase/migrations/202611060001_legacy_music_library.sql). It creates the legacy `songs` and account-owned `liked_songs` tables with row-level security. Add your song rows to `public.songs` in Supabase; the Jamendo and Local files sources do not require these legacy tables. Local playlist entries are stored only on this computer under `%LOCALAPPDATA%\Prism\playlist_items.sqlite3`; their paths are not uploaded.

   To enable the Movies & TV catalog, set `TMDB_API_KEY` in the same local `.env` file using your own TMDB API key. Keep it out of Git as well.

   Music & Audio uses the public Jamendo Client ID in `.env.example` by default. It can be overridden with `JAMENDO_CLIENT_ID`. Do not add a Jamendo client secret to this desktop app.

5. Launch Prism:

   ```powershell
   python main.py
   ```

## Build a portable Windows presentation copy

Build on a Windows computer using the same architecture as the presentation computer. This creates a folder-based app and a ZIP; the lab computer does not need Python, PyCharm, or a project checkout.

1. Install the project requirements in its virtual environment, then install the build tool:

   ```powershell
   python -m pip install -r requirements.txt
   python -m pip install -r requirements-build.txt
   ```

2. From the project folder, run:

   ```powershell
   .\build_windows.ps1
   ```

3. Copy `dist\Prism-Windows-x64.zip` to the presentation computer and extract it. In the extracted `Prism` folder, copy `.env.example` to `.env`, then set `SUPABASE_URL` and `SUPABASE_KEY`. `TMDB_API_KEY` is optional if you will not demonstrate Movies & TV. Jamendo uses its public Client ID by default.

The ZIP deliberately excludes `.env`. Configure the extracted copy on the presentation computer instead of sharing credentials in the archive. Use only a Supabase publishable/legacy anon key protected by the project's row-level security; never distribute a `service_role` key. The computer needs internet access for Supabase, Jamendo, and TMDB. Local files and Snake work without those catalog services.

## Data and credentials

- `.env` contains local Supabase settings and is excluded from Git.
- Supabase Auth provides account identity and sessions. SQLite stores a salted PBKDF2 password hash and its metadata locally; the database is created under `%LOCALAPPDATA%\Prism\users.sqlite3`.
- Do not commit `.env`, SQLite databases, real user data, or credentials.
- The Movies & TV catalog uses TMDB metadata. This app is not endorsed or certified by TMDB; see the in-app Credits for attribution.
- Snake uses arrow keys or W/A/S/D to steer, Space or Escape to pause, a Play overlay to start or replay, and icon controls above the board to pause or restart.
- Jamendo catalog search and genre browsing use its public API. Select a Jamendo result and double-click to play it; track pages and license links are shown in Prism. Downloads are not offered.
- Select **Local files** in Music & Audio and choose a folder to scan recursively. Supported extensions are MP3, OGG, OGA, WAV, and FLAC.
- The player queue follows the active results or playlist when a track is started. Use the queue panel to play, remove, or clear upcoming tracks; shuffle and repeat-off/all/one controls are available in the player bar. Timeline seeking depends on the active format supporting seeking.
- Create playlists from the sidebar, open one by double-clicking it, and rename or delete it from its context menu. Add Jamendo or local tracks from the music table context menu. Jamendo entries sync to the signed-in Supabase account; local entries remain device-only.

## Working with branches

After creating an empty repository on GitHub, publish this prepared local project from PowerShell:

```powershell
git remote add origin https://github.com/OWNER/REPOSITORY.git
git add -A
git commit -m "Prepare Prism project"
git push -u origin main
```

Replace the URL with the repository you created. Then create a feature branch before making changes:

```powershell
git switch -c feature/your-change
```

Keep commits focused and open a pull request against the shared project branch when your work is ready.

## License

No license is included yet. Choose one with your project partner before inviting reuse or redistributing the project.

## Project guidance

Before changing the app, read `#PastConsiderations/prism_context_handoff.md`. It records the scope, architecture, design direction, status, and roadmap.
