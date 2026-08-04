# Deploy the window (public URL, ~1 minute, no token handed to anyone)

The window is pure Python stdlib — no dependencies. It binds `0.0.0.0:$PORT` automatically
when a platform sets `$PORT` (Railway/Render/Fly/Heroku), and `127.0.0.1` otherwise.

## Railway (deploy from this GitHub repo — recommended)
1. railway.com → **New Project** → **Deploy from GitHub repo** → pick this repo,
   branch `claude/new-session-57sgrp`.
2. Railway auto-detects Python (Nixpacks), runs `Procfile` (`python -m ui.server`).
3. In the service → **Settings → Networking → Generate Domain**. That is your public URL.
4. Do **NOT** set `ANTHROPIC_API_KEY` — the window boots in LM-omitted mode and says so;
   the deterministic engine runs live. (Set it later only if you want the LM source.)

Ephemeral vs keeper: a Railway service is persistent (stays up until you delete it), unlike
a sandbox tunnel. It is unauthenticated — anyone with the URL can paste text and watch the
engine settle. It reads only what is pasted; it never touches P3/D5 or any real corpus.

## Local (no browser-exposure, one command)
    python -m ui.server        # http://127.0.0.1:8848, LM-omitted unless a key is set

## Any other platform
Set the start command to `python -m ui.server`; the app honors `$PORT`. Or force a public
bind locally with `COMMON_GROUND_BIND_ALL=1 python -m ui.server`.
