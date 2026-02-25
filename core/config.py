import json
import os
from typing import Any, Dict

class ConfigManager:
    """Handles loading, saving, and accessing the application's configuration."""

    def __init__(self, config_path: str):
        self.path = config_path
        self.settings: Dict[str, Any] = {}

        self.defaults = {
            "scan_rate": 1.0,
            "send_timeout": 30,
            "file_delay": 0.8,
            "formats": ".jpg,.jpeg,.png,.gif,.bmp,.webp",
            "sound_enabled": True,
            "theme_name": "Dark Blue (default)"
        }

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        else:
            self.settings = self.defaults.copy()
    
    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default if default is not None else self.defaults.get(key))
    
    def set(self, key: str, value: Any):
        self.settings[key] = value