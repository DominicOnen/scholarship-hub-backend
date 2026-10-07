# Global Scholarship Hub – backend

FastAPI service for the Global Scholarship Hub phone app.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | `{"status":"ok"}` – the app checks the server with this |
| GET | `/scholarships` | the 6 offers, with live "slots left" |
| GET | `/scholarships/{id}` | one offer |
| POST | `/applications` | submit `{scholarship_id, full_name, email}` → status `pending` (same email twice returns the same application) |
| GET | `/applications/{id}` | status: `pending` → `accepted` after `REVIEW_SECONDS` (default 20) |
| PATCH | `/applications/{id}` | board decision, header `X-Admin-Key` |

## Run on your laptop (phone on the same Wi-Fi)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: py -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest                                       # 8 passed
uvicorn scholarhub.api:app --host 0.0.0.0 --app-dir src
```
Open `http://<laptop-IP>:8000/docs`. Put `http://<laptop-IP>:8000` in the app's `config.js`.

## Put it online (free, so the APK works from anywhere)
1. Push this folder to its own GitHub repo.
2. On render.com: **New → Blueprint** → pick the repo (it reads `render.yaml`).
3. Copy the URL Render gives you (like `https://scholarship-hub-api.onrender.com`) into the app's `config.js`, push the app, and let the APK build run again.

Free Render sleeps when idle: the first request after a rest takes ~30–60 s, and applications saved in SQLite reset when it restarts. Fine for a demo; use a hosted database for real use.
