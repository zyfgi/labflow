"""Local file storage service.

All business code must go through this service (PRD §14): sanitized file
names, extension whitelist, size limit and path-traversal protection.
Swappable with MinIO/S3 later behind the same interface.
"""

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._\-一-龥]")


class StorageService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.upload_path).resolve()

    def _resolve(self, rel_path: str) -> Path:
        # path traversal guard: the resolved path must stay inside root
        candidate = (self.root / rel_path).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise HTTPException(status_code=400, detail="非法的文件路径")
        return candidate

    @staticmethod
    def sanitize_name(name: str) -> str:
        name = Path(name).name  # drop any directory components
        name = _UNSAFE_CHARS.sub("_", name).strip("._")
        return name[:120] or "file"

    def save_upload(self, subdir: str, upload: UploadFile) -> tuple[str, int, str]:
        """Persist an UploadFile. Returns (rel_path, size, content_type)."""
        original = upload.filename or "file"
        ext = Path(original).suffix.lower().lstrip(".")
        if ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型 .{ext}，允许：{', '.join(settings.allowed_extensions)}",
            )

        safe = self.sanitize_name(original)
        rel_path = f"{subdir}/{uuid.uuid4().hex[:12]}_{safe}"
        dest = self._resolve(rel_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        size = 0
        limit = settings.upload_max_bytes
        with dest.open("wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过大小限制 {settings.UPLOAD_MAX_MB} MB",
                    )
                out.write(chunk)
        if size == 0:
            dest.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="空文件")
        return rel_path, size, upload.content_type or "application/octet-stream"

    def delete(self, rel_path: str) -> None:
        path = self._resolve(rel_path)
        path.unlink(missing_ok=True)

    def open_path(self, rel_path: str) -> Path:
        path = self._resolve(rel_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        return path


storage_service = StorageService()
