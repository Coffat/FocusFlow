class DomainError(Exception):
    """Base exception for domain invariant violations across all Bounded Contexts."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
