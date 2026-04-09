from app.models import TranscriptSegment


def format_timestamp(seconds: float, for_srt: bool = False) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours = total_ms // 3_600_000
    remainder = total_ms % 3_600_000
    minutes = remainder // 60_000
    remainder = remainder % 60_000
    secs = remainder // 1_000
    millis = remainder % 1_000

    if for_srt:
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


def to_timestamped_text(segments: list[TranscriptSegment]) -> str:
    lines: list[str] = []
    for segment in segments:
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        lines.append(f"[{start} -> {end}] {segment.text}")
    return "\n".join(lines)


def to_srt(segments: list[TranscriptSegment]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = format_timestamp(segment.start, for_srt=True)
        end = format_timestamp(segment.end, for_srt=True)
        text = segment.text.strip()
        blocks.append(f"{index}\n{start} --> {end}\n{text}\n")
    return "\n".join(blocks).strip() + "\n"
