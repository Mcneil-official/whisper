import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ErrorResponse, JobStatusResponse, StoredTranscript, TranscriptionResult
from app.services.exporters import to_srt, to_timestamped_text
from app.services.store import store
from app.services.transcriber import WhisperTranscriber

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

transcriber = WhisperTranscriber(settings.whisper_model)
job_executor = ThreadPoolExecutor(max_workers=1)


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


def process_transcription_job(job_id: str) -> None:
    job = store.get_job(job_id)
    if not job:
        return

    temp_path = job.temp_path
    try:
        store.update_job(job_id, state="preparing", progress=10, message="Preparing audio file")
        store.update_job(job_id, state="transcribing", progress=45, message="Running Whisper transcription")

        text, language, segments = transcriber.transcribe(Path(temp_path))

        store.update_job(job_id, state="formatting", progress=85, message="Formatting transcript output")
        transcript = StoredTranscript(
            filename=job.filename,
            language=language,
            text=text,
            segments=segments,
        )
        transcript_id = store.create(transcript)

        store.update_job(
            job_id,
            state="completed",
            progress=100,
            message="Transcription completed",
            error="",
            transcript_id=transcript_id,
        )
    except Exception as exc:
        store.update_job(
            job_id,
            state="failed",
            progress=100,
            message="Transcription failed",
            error=str(exc),
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        store.clear_job_temp_path(job_id)


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
        transcript_id = store.create(transcript)
        return transcript.as_response(transcript_id)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post(
    "/api/transcribe/jobs",
    response_model=JobStatusResponse,
    status_code=202,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def create_transcription_job(file: UploadFile = File(...)) -> JobStatusResponse:
    payload = await file.read()
    extension = validate_upload(file, payload)

    try:
        with NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            temp_file.write(payload)
            temp_path = temp_file.name

        job_id = store.create_job(file.filename or "audio", temp_path)
        store.update_job(job_id, message="Queued for processing", progress=0, state="queued")
        job_executor.submit(process_transcription_job, job_id)

        job = store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=500, detail="Failed to create transcription job.")
        return job.as_status_response(job_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to enqueue transcription: {exc}") from exc


@app.get(
    "/api/transcribe/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_transcription_job_status(job_id: str) -> JobStatusResponse:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")
    return job.as_status_response(job_id)


@app.get(
    "/api/transcribe/jobs/{job_id}/result",
    response_model=TranscriptionResult,
    responses={202: {"model": JobStatusResponse}, 404: {"model": ErrorResponse}},
)
def get_transcription_job_result(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    if job.state == "failed":
        detail = job.error or "Transcription failed"
        raise HTTPException(status_code=500, detail=detail)

    if job.state != "completed" or not job.transcript_id:
        return JSONResponse(status_code=202, content=job.as_status_response(job_id).model_dump(mode="json"))

    transcript = store.get(job.transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")

    return transcript.as_response(job.transcript_id)


@app.get("/api/transcripts/{transcript_id}", response_model=TranscriptionResult)
def get_transcript(transcript_id: str) -> TranscriptionResult:
    transcript = store.get(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    return transcript.as_response(transcript_id)


@app.get("/api/transcripts/{transcript_id}/timestamped")
def get_timestamped_text(transcript_id: str) -> dict[str, str]:
    transcript = store.get(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    return {"timestamped": to_timestamped_text(transcript.segments)}


@app.get("/api/transcripts/{transcript_id}/download/txt")
def download_txt(transcript_id: str) -> FileResponse:
    transcript = store.get(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")

    file_path = settings.base_dir / "app" / "static" / "downloads" / f"{transcript_id}.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(transcript.text, encoding="utf-8")

    return FileResponse(
        path=file_path,
        media_type="text/plain",
        filename=f"{Path(transcript.filename).stem}.txt",
    )


@app.get("/api/transcripts/{transcript_id}/download/srt")
def download_srt(transcript_id: str) -> FileResponse:
    transcript = store.get(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")

    srt_content = to_srt(transcript.segments)
    file_path = settings.base_dir / "app" / "static" / "downloads" / f"{transcript_id}.srt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(srt_content, encoding="utf-8")

    return FileResponse(
        path=file_path,
        media_type="application/x-subrip",
        filename=f"{Path(transcript.filename).stem}.srt",
    )


app.mount("/", StaticFiles(directory=settings.base_dir / "app" / "static", html=True), name="static")
