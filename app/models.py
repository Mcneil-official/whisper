from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    index: int
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    transcript_id: str
    filename: str
    language: str | None = None
    text: str
    segments: list[TranscriptSegment]
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str


JobState = Literal["queued", "preparing", "transcribing", "formatting", "completed", "failed"]


class JobStatusResponse(BaseModel):
    job_id: str
    filename: str
    state: JobState
    progress: int
    message: str
    error: str | None = None
    transcript_id: str | None = None
    created_at: datetime
    updated_at: datetime


class StoredTranscript(BaseModel):
    filename: str
    language: str | None = None
    text: str
    segments: list[TranscriptSegment]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def as_response(self, transcript_id: str) -> TranscriptionResult:
        return TranscriptionResult(
            transcript_id=transcript_id,
            filename=self.filename,
            language=self.language,
            text=self.text,
            segments=self.segments,
            created_at=self.created_at,
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "language": self.language,
            "text": self.text,
            "segments": [segment.model_dump() for segment in self.segments],
            "created_at": self.created_at.isoformat(),
        }


class StoredJob(BaseModel):
    filename: str
    temp_path: str
    state: JobState = "queued"
    progress: int = 0
    message: str = "Queued for processing"
    error: str | None = None
    transcript_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def as_status_response(self, job_id: str) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=job_id,
            filename=self.filename,
            state=self.state,
            progress=self.progress,
            message=self.message,
            error=self.error,
            transcript_id=self.transcript_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
