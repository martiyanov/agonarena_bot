from __future__ import annotations

import subprocess
from pathlib import Path

import httpx

from app.config import settings


class TranscriptionService:
    """Распознавание голосовых сообщений через OpenAI Audio Transcriptions API."""

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

    async def transcribe(self, source_path: str | Path, *, language: str = "ru") -> str:
        if not self.is_configured():
            raise RuntimeError("Transcription API is not configured")

        prepared_path = self._prepare_audio(Path(source_path))
        try:
            return await self._transcribe_via_api(prepared_path, language=language)
        finally:
            if prepared_path != Path(source_path) and prepared_path.exists():
                prepared_path.unlink(missing_ok=True)

    def _prepare_audio(self, source_path: Path) -> Path:
        if source_path.suffix.lower() not in {".ogg", ".oga"}:
            return source_path

        target_path = source_path.with_suffix(".wav")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                str(target_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return target_path

    async def _transcribe_via_api(self, file_path: Path, *, language: str) -> str:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        data = {
            "model": settings.stt_model,
            "language": language,
            "response_format": "json",
        }

        with file_path.open("rb") as audio_file:
            files = {"file": (file_path.name, audio_file, "audio/wav")}
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.openai_base_url}/audio/transcriptions",
                    headers=headers,
                    data=data,
                    files=files,
                )
                response.raise_for_status()
                payload = response.json()

        text = (payload.get("text") or "").strip()
        if not text:
            raise RuntimeError("Empty transcription result")
        return text
