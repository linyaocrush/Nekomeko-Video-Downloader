from typing import Optional
from pydantic import BaseModel, field_validator


class HistoryRecord(BaseModel):
    id: int
    title: str = "Unknown Title"
    uploader: str = "Unknown Uploader"
    uploader_url: Optional[str] = ""
    webpage_url: Optional[str] = ""
    file_size: int = 0
    download_date: str
    duration: int = 0
    elapsed_seconds: float = 0.0

    @field_validator('title', 'uploader', mode='before')
    @classmethod
    def handle_none_strings(cls, v):
        return v if v is not None else "Unknown"

    @field_validator('file_size', 'duration', mode='before')
    @classmethod
    def handle_none_ints(cls, v):
        return v if v is not None else 0

    @field_validator('elapsed_seconds', mode='before')
    @classmethod
    def handle_none_floats(cls, v):
        return v if v is not None else 0.0

    @property
    def size_mb(self) -> float:
        return self.file_size / (1024 * 1024)

    @property
    def speed_mb_s(self) -> float:
        return (self.size_mb / self.elapsed_seconds) if self.elapsed_seconds > 0 else 0.0
