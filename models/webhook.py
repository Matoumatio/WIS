from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SharedProfileModel:
    """
    Identity override for webhooks (username and avatar).
    """

    name: str
    username: str
    avatar_url: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> 'SharedProfileModel':
        return cls(**data)

@dataclass
class WebhookModel:
    """
    Configuration for a Discord style webhook endpoint.
    """
    name: str
    url: str
    is_enabled: bool = True
    shared_profile_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'WebhookModel':
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            is_enabled=data.get("enabled", True),
            shared_profile_name=data.get("shared_profile")
        )
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "enabled": self.is_enabled,
            "shared_profile": self.shared_profile_name
        }