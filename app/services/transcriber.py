from pathlib import Path

from openai import OpenAI

from app.models import TranscriptSegment


class WhisperTranscriber:
    def __init__(self, api_key: str | None, model_name: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name

    def transcribe(self, audio_path: Path) -> tuple[str, str | None, list[TranscriptSegment]]:
        with audio_path.open("rb") as audio_file:
            result = self._client.audio.transcriptions.create(
                model=self._model_name,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        raw_segments = getattr(result, "segments", None) or []

        segments: list[TranscriptSegment] = []
        for index, segment in enumerate(raw_segments, start=1):
            segments.append(
                TranscriptSegment(
                    index=index,
                    start=float(getattr(segment, "start", 0.0)),
                    end=float(getattr(segment, "end", 0.0)),
                    text=str(getattr(segment, "text", "")).strip(),
                )
            )

        text = str(getattr(result, "text", "")).strip()
        language = getattr(result, "language", None)

        if not segments and text:
            segments = [
                TranscriptSegment(
                    index=1,
                    start=0.0,
                    end=0.0,
                    text=text,
                )
            ]

        return text, language, segments
