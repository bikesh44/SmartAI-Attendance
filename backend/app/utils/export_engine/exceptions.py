"""Export Engine Custom Exceptions.

Defines domain-specific exceptions for the SAMS-FR multi-format document
export engine (PDF, Excel, CSV).
"""


class ExportEngineError(Exception):
    """Base exception for all export engine errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ExportValidationError(ExportEngineError):
    """Raised when input parameters, headers, or data rows fail validation."""
    pass


class ExportRenderingError(ExportEngineError):
    """Raised when rendering a document format (PDF, Excel, CSV) fails."""
    pass
