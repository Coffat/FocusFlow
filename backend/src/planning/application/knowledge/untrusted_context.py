import html
from uuid import UUID


def wrap_untrusted_knowledge_context(*, source_id: UUID | str, content: str) -> str:
    sanitized = content.replace(
        "</untrusted_knowledge_context>", "&lt;/untrusted_knowledge_context&gt;"
    )
    sanitized = sanitized.replace("<untrusted_knowledge_context", "&lt;untrusted_knowledge_context")
    safe_source = html.escape(str(source_id), quote=True)
    return (
        f'<untrusted_knowledge_context source_id="{safe_source}">\n'
        f"{sanitized}\n"
        "</untrusted_knowledge_context>"
    )
