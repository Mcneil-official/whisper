import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ErrorResponse, StoredTranscript, TranscriptionResult
from app.services.transcriber import WhisperTranscriber

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

transcriber = WhisperTranscriber(settings.openai_api_key, settings.transcription_model)


def validate_upload(file: UploadFile, payload: bytes) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    extension = Path(file.filename).suffix.lower()
    if extension not in settings.allowed_extensions:
        allowed = ", ".join(settings.allowed_extensions)
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")

    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large. Max size is {settings.max_upload_mb} MB.",
        )

    return extension


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post(
    "/api/transcribe",
    response_model=TranscriptionResult,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def transcribe(file: UploadFile = File(...)) -> TranscriptionResult:
    payload = await file.read()
    extension = validate_upload(file, payload)

    temp_path: str | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_file.write(payload)
            temp_path = temp_file.name

        text, language, segments = transcriber.transcribe(Path(temp_path))
        transcript = StoredTranscript(
            filename=file.filename,
            language=language,
            text=text,
            segments=segments,
        )
        return transcript.as_response("local")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


app.mount("/", StaticFiles(directory=settings.base_dir / "app" / "static", html=True), name="static")
