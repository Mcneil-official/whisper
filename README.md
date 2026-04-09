# Whisper Upload Web Transcriber

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

Make sure `ffmpeg` is installed and available in your PATH.

## 2) Configure

```powershell
Copy-Item .env.example .env
```

Optional `.env` settings:

- `APP_NAME`
- `MAX_UPLOAD_MB`
- `WHISPER_MODEL` (e.g. `tiny`, `base`, `small`, `medium`, `large`)

## 3) Run

```powershell
uvicorn app.main:app --reload
```

Open your browser at `http://127.0.0.1:8000`.

## API Endpoints

- `POST /api/transcribe`
- `POST /api/transcribe/jobs`
- `GET /api/transcribe/jobs/{job_id}/status`
- `GET /api/transcribe/jobs/{job_id}/result`
- `GET /api/transcripts/{transcript_id}`
- `GET /api/transcripts/{transcript_id}/timestamped`
- `GET /api/transcripts/{transcript_id}/download/txt`
- `GET /api/transcripts/{transcript_id}/download/srt`

## Progress Flow

The web UI now uses a server-side job flow to show transcription progress:

1. Upload creates a job with `POST /api/transcribe/jobs`.
2. Frontend polls `GET /api/transcribe/jobs/{job_id}/status` every ~1.2s.
3. When status becomes `completed`, frontend loads the transcript from `GET /api/transcribe/jobs/{job_id}/result`.

Progress is stage-based (`queued`, `preparing`, `transcribing`, `formatting`, `completed`/`failed`) with percentage updates from the server.

## Notes

- This first version stores transcript results in memory. Restarting the server clears transcript history.
- Download files are created under `app/static/downloads/`.
- For public deployment later, use a persistent database/object storage and restrict CORS origins.
