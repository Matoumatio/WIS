import os
from threading import Thread
from typing import Optional

try:
    import pygame
    _PYGAME_AVAILABLE = True

except ImportError:
    _PYGAME_AVAILABLE = False


class AudioService:
    """Handles playing notification sounds asynchronously."""

    def __init__(self):
        self.enabled = _PYGAME_AVAILABLE
        if self.enabled:
            try:
                pygame.mixer.init()
            except Exception:
                self.enabled = False
    
    def play_sound(self, file_path: str, volume: float = 0.8):
        if not self.enabled or not os.path.exists(file_path):
            return
        
        def _play():
            try:
                sound = pygame.mixer.sound(file_path)
                sound.set_volume(max(0.0, min(1.0, volume)))
                sound.play()
            except Exception:
                pass
        
        Thread(target=_play, daemon=True).start()