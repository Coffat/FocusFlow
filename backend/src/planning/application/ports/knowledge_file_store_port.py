from typing import Protocol
from uuid import UUID


class KnowledgeFileStorePort(Protocol):
    async def save(self, source_id: UUID, suffix: str, content: bytes) -> str: ...

    async def read(self, uri: str) -> bytes: ...

    async def delete(self, uri: str) -> None: ...
