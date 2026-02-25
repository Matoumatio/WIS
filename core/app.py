import tkinter as tk
from core.config import ConfigManager
from core.events import EventBus, AppEvents

class WISApplication:
    """Main class that coordinates the application's lifecycle."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = ConfigManager("wis_settings.json")
        self.stats_config = ConfigManager("wis_stats.json")

        self.monitor_service = None
        self.ui = None
    

    def initialize(self):
        self.config.load()

        self._setup_styles()

        EventBus.subscribe(AppEvents.LOG_EMITTED, self._handle_log)
    
    def _setup_styles(self):
        pass
    
    def _handle_log(self, data):
        print(f"[{data.get('level')}] {data.get('message')}")
    
    def run(self):
        self.root.mainloop()