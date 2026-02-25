from dataclasses import dataclass
from datetime import datetime


@dataclass
class SendRecord:
    """
    Represents a single successful or failed image delivery.
    """
    time: str
    month: str
    filename: str
    webhook_name: str
    folder_path: str
    extension: str
    is_ok: bool

    @classmethod
    def create_now(cls, filename: str, webhook: str, folder: str, ext: str, ok: bool) -> 'SendRecord':
        """Factory method to create a record with current time."""
        now = datetime.now()
        return cls(
            time=now.strftime("%H:%M:%S"),
            month=now.strftime("%Y-%m"),
            filename=filename,
            webhook_name=webhook,
            folder_path=folder,
            extension=ext,
            is_ok=ok
        )

@dataclass
class ErrorRecord:
    """
    Detailed information about a delivery failure.
    """
    timestamp: str
    error_type: str
    filename: str
    webhook_name: str
    detail: str