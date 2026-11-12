import asyncio
from pathlib import Path
from uuid import UUID

from src.planning.application.ports.knowledge_file_store_port import KnowledgeFileStorePort


class LocalKnowledgeFileStore(KnowledgeFileStorePort):
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _path(self, source_id: UUID, suffix: str) -> Path:
        safe_suffix = suffix.lower().lstrip(".")
        if safe_suffix not in {"pdf", "docx", "txt"}:
            raise ValueError("Unsupported knowledge file extension")
        return self._root / f"{source_id}.{safe_suffix}"

    async def save(self, source_id: UUID, suffix: str, content: bytes) -> str:
        path = self._path(source_id, suffix)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, content)
        return str(path)

    async def read(self, uri: str) -> bytes:
        path = Path(uri).resolve()
        if self._root not in path.parents:
            raise ValueError("Knowledge file path escapes configured storage root")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, uri: str) -> None:
        path = Path(uri).resolve()
        if self._root not in path.parents:
            return
        await asyncio.to_thread(path.unlink, missing_ok=True)
