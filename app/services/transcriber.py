from pathlib import Path

import whisper

from app.models import TranscriptSegment


class WhisperTranscriber:
    def __init__(self, model_name: str) -> None:
        self._model = whisper.load_model(model_name)

    def transcribe(self, audio_path: Path) -> tuple[str, str | None, list[TranscriptSegment]]:
        result = self._model.transcribe(str(audio_path))
        raw_segments = result.get("segments", [])

        segments: list[TranscriptSegment] = []
        for index, segment in enumerate(raw_segments, start=1):
            segments.append(
                TranscriptSegment(
                    index=index,
                    start=float(segment.get("start", 0.0)),
                    end=float(segment.get("end", 0.0)),
                    text=str(segment.get("text", "")).strip(),
                )
            )

        text = str(result.get("text", "")).strip()
        language = result.get("language")
        return text, language, segments
