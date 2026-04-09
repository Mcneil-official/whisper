from datetime import datetime, UTC
from threading import Lock
from uuid import uuid4

from app.models import JobState, StoredJob, StoredTranscript


class TranscriptStore:
    def __init__(self) -> None:
        self._transcripts: dict[str, StoredTranscript] = {}
        self._jobs: dict[str, StoredJob] = {}
        self._lock = Lock()

    def create(self, transcript: StoredTranscript) -> str:
        transcript_id = uuid4().hex
        with self._lock:
            self._transcripts[transcript_id] = transcript
        return transcript_id

    def get(self, transcript_id: str) -> StoredTranscript | None:
        with self._lock:
            return self._transcripts.get(transcript_id)

    def create_job(self, filename: str, temp_path: str) -> str:
        job_id = uuid4().hex
        job = StoredJob(filename=filename, temp_path=temp_path)
        with self._lock:
            self._jobs[job_id] = job
        return job_id

    def get_job(self, job_id: str) -> StoredJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        *,
        state: JobState | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        transcript_id: str | None = None,
    ) -> StoredJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            if state is not None:
                job.state = state
            if progress is not None:
                job.progress = max(0, min(100, int(progress)))
            if message is not None:
                job.message = message
            if error is not None:
                job.error = error
            if transcript_id is not None:
                job.transcript_id = transcript_id
            job.updated_at = datetime.now(UTC)
            return job

    def clear_job_temp_path(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.temp_path = ""
            job.updated_at = datetime.now(UTC)


store = TranscriptStore()
