import asyncio
import os
import stat
from pathlib import Path
from uuid import UUID

from src.planning.application.ports.knowledge_file_store_port import KnowledgeFileStorePort


class LocalKnowledgeFileStore(KnowledgeFileStorePort):
    """Stores temporary uploaded knowledge files in a private (0700) directory using UUID names."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _path(self, source_id: UUID, suffix: str) -> Path:
        safe_suffix = suffix.lower().lstrip(".")
        if safe_suffix not in {"pdf", "docx", "txt"}:
            raise ValueError("Unsupported knowledge file extension")
        return self._root / f"{source_id}.{safe_suffix}"

    def _ensure_private_root(self) -> None:
        os.makedirs(self._root, mode=0o700, exist_ok=True)
        if os.name != "nt":
            st = os.lstat(self._root)
            if stat.S_ISLNK(st.st_mode):
                raise ValueError("Knowledge storage root must not be a symlink")
            if hasattr(os, "getuid") and st.st_uid == os.getuid():
                os.chmod(self._root, 0o700)

    def _write_private_file(self, path: Path, content: bytes) -> None:
        self._ensure_private_root()
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
        except Exception:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        if os.name != "nt":
            os.chmod(path, 0o600)

    async def save(self, source_id: UUID, suffix: str, content: bytes) -> str:
        path = self._path(source_id, suffix)
        await asyncio.to_thread(self._write_private_file, path, content)
        return str(path)

    async def read(self, uri: str) -> bytes:
        if not uri:
            raise ValueError("Knowledge file path is empty")
        path = Path(uri).resolve()
        if self._root not in path.parents:
            raise ValueError("Knowledge file path escapes configured storage root")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, uri: str) -> None:
        if not uri:
            return
        path = Path(uri).resolve()
        if self._root not in path.parents:
            return
        await asyncio.to_thread(path.unlink, missing_ok=True)
