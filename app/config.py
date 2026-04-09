from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Whisper Web Transcriber"
    max_upload_mb: int = 100
    whisper_model: str = "base"
    allowed_extensions: tuple[str, ...] = (".m4a", ".mp3", ".wav", ".mp4", ".ogg", ".flac")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent


settings = Settings()
