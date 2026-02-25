from dataclasses import dataclass, asdict

@dataclass
class FolderModel:
    """
    Represents a directory to be monitored for new images.
    """
    path: str
    is_enabled: bool = True
    is_recursive: bool = False

    @classmethod
    def from_dictionary(cls, data: dict) -> 'FolderModel':
        """Creates an instance from a dictionary (JSON source)."""
        return cls(
            path=data.get("path", ""),
            is_enabled=data.get("enabled", True),
            is_recursive=data.get("recursive", False)
        )
    
    def to_dict(self) -> dict:
        """Converts the model to a dictionary for JSON storage."""
        return {
            "path": self.path,
            "enabled": self.is_enabled,
            "recursive": self.is_recursive
        }