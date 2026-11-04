# Prism Media Hub

Prism is a Python desktop media hub for music and audio, movies and TV, and arcade games. It is a university project following Option 3A.

## Current status

- Music and audio: the current working module, with Supabase-backed songs, playlists, and liked songs.
- Movies and TV: TMDB title catalogue and embedded local video playback.
- Arcade: Snake is playable inside Prism; more games can be added later.

The Snake game adapts PyBox gameplay under its MIT license. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for attribution and license terms.

## Requirements

- Windows (the current app has been developed and run on Windows)
- Python 3.15, matching the project handoff
- A Supabase project configured for the tables and authentication used by the app

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

   To enable the Movies & TV catalog, set `TMDB_API_KEY` in the same local `.env` file using your own TMDB API key. Keep it out of Git as well.

5. Launch Prism:

   ```powershell
   python main.py
   ```

## Data and credentials

- `.env` contains local Supabase settings and is excluded from Git.
- Supabase Auth provides account identity and sessions. SQLite stores a salted PBKDF2 password hash and its metadata locally; the database is created under `%LOCALAPPDATA%\Prism\users.sqlite3`.
- Do not commit `.env`, SQLite databases, real user data, or credentials.
- The Movies & TV catalog uses TMDB metadata. This app is not endorsed or certified by TMDB; see the in-app Credits for attribution.
- Snake uses arrow keys or W/A/S/D to steer, Space or Escape to pause, a Play overlay to start or replay, and icon controls above the board to pause or restart.

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
