# Whisper Upload Web Transcriber

This repo is now Vercel-friendly.

The deployment path is:

1. Vercel hosts the frontend and Python API.
2. Transcription runs through the OpenAI API instead of local Whisper.
3. The browser generates `.txt` and `.srt` downloads locally from the response.

Upload an audio file (`.m4a`, `.mp3`, `.wav`, `.mp4`, `.ogg`, `.flac`) from a browser and get:

- Plain transcript text
- Timestamped transcript view
- Downloadable `.txt` and `.srt` files

## 1) Setup

```powershell
# from project root
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You do not need `ffmpeg` or local Whisper for Vercel deployment anymore.

## 2) Configure

```powershell
Copy-Item .env.example .env
```

Optional `.env` settings:

- `APP_NAME`
- `MAX_UPLOAD_MB`
- `OPENAI_API_KEY`
- `TRANSCRIPTION_MODEL` (default: `whisper-1`)

## 3) Run

```powershell
uvicorn app.main:app --reload
```

Open your browser at `http://127.0.0.1:8000`.

## Vercel Deployment

1. Set your OpenAI API key in Vercel environment variables.
2. Deploy the repo as a Python project.
3. Vercel will pick up the ASGI app from [app/main.py](app/main.py).
4. The `vercel.json` file excludes local dev files and the old Whisper artifacts from the bundle.

## API Endpoint

- `POST /api/transcribe`

The browser handles timestamp display and `.txt`/`.srt` downloads from the returned transcript payload.

## Notes

- The app no longer depends on local Whisper or in-memory transcript storage.
- Downloads are created in the browser, so there is no server-side file persistence requirement.
- For public deployment later, keep your API key restricted to Vercel environment variables.
