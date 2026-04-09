from datetime import datetime

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
