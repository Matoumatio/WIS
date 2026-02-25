import json
import requests
import mimetypes
import os
from abc import ABC, abstractmethod
from typing import Optional
from models.webhook import SharedProfileModel

class ISender(ABC):
    """Interface for image delivery services."""
    @abstractmethod
    def send_image(self, file_path: str, url: str, timeout: int, profile: Optional[SharedProfileModel] = None) -> bool:
        pass

class HttpSender(ISender):
    """Implementation for sending images to webhooks via HTTP POST."""

    def send_image(self, file_path, url, timeout, profile = None):
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, mime_type)}

                if profile:
                    payload = {
                        "username": profile.username,
                        "avatar_url": profile.avatar_url
                    }
                    files["payload_json"] = (None, json.dumps(payload), "application/json")
                
                response = requests.post(url, files=files, timeout=timeout)
                return response.status_code in (200, 201, 204)
        except:
            return False