import tkinter as tk
from core.config import ConfigManager
from core.events import EventBus, AppEvents
from models.folder import FolderModel
from models.theme import ThemeModel
from models.webhook import WebhookModel
from ui.main_window import MainWindow
from ui.dialogs.folder_manager import FolderManager
from ui.dialogs.webhook_manager import WebhookManager, SharedProfileModel
from ui.dialogs.settings_manager import SettingsManager

from services.scanner import ImageScanner
from services.sender import HttpSender
from services.audio import AudioService
from services.monitor import MonitoringService

class WISApplication:
    """Main class that coordinates the application's lifecycle."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = ConfigManager("wis_settings.json")
        self.stats_config = ConfigManager("wis_stats.json")

        # Business Logic State
        self.folders = []
        self.webhooks = []
        self.profiles = []
        self.theme = None

        # Services
        self.audio = AudioService()
        self.sender = HttpSender()
        self.scanner = None
        self.monitor = None

        self.ui = None

        self.session_sent = 0
        self.session_failed = 0

    def initialize(self):
        """Initializes settings, themes, and the main UI window."""
        # 1. Load configuration from disk
        self.config.load()

        # 2. Transform raw data into typed Models
        self._load_data_models()

        # Init Scanner and monitor
        formats = self.config.get("formats", ".jpg,.jpeg,.png,.gif,.bmp,.webp").split(",")
        self.scanner = ImageScanner(set(formats))
        self.monitor = MonitoringService(self.sender, self.scanner)

        # 3. Setup Commands for the UI (dependency injection)
        commands = {
            "manage_folders": self._open_folder_manager,
            "manage_webhooks": self._open_webhook_manager,
            "settings": self._open_settings_manager,
            "statistics": lambda: self.ui.append_log("Statistics not implemented", "warn"),
            "start": self._toggle_monitoring
        }

        # 4. Initialize Main Window
        self.ui = MainWindow(self.root, self.theme, commands)

        # 5. Subscribe to Events
        EventBus.subscribe(AppEvents.LOG_EMITTED, self._handle_log)
        EventBus.subscribe(AppEvents.STATS_UPDATED, self._on_stats_updated)
        EventBus.subscribe(AppEvents.MONITORING_STARTED, self._on_monitor_started)
        EventBus.subscribe(AppEvents.MONITORING_STOPPED, self._on_monitor_stopped)
        
        # Initial status log
        self.ui.append_log("WIS - Ready", "ok")
        self._update_summaries()
    
    def _load_data_models(self):
        """Converts raw dictionary data from config into specific Models."""

        raw_folders = self.config.get("folders", [])
        self.folders = [FolderModel.from_dictionary(f) for f in raw_folders]

        # Load theme
        all_themes = self.config.get("themes", {})
        active_name = self.config.get("theme_active", "Dark Blue")
    
        theme_colors = all_themes.get(active_name, all_themes.get("Dark Blue"))
        self.theme = ThemeModel.from_dict(theme_colors)

        # Load Profiles
        raw_profiles = self.config.get("shared_profiles", [])
        self.profiles = [SharedProfileModel.from_dict(p) for p in raw_profiles]

        # Load Webhooks
        raw_webhooks = self.config.get("webhooks", [])
        self.webhooks = [WebhookModel.from_dict(w) for w in raw_webhooks]
    
    def _update_summaries(self):
        """Updates the information labels displayed on the sidebar."""
        active_folders = [f for f in self.folders if f.is_enabled]
        count = len(active_folders)
        
        summary = f"• {count} folders enabled"
        if count > 0:
            summary += f"\n• Active: {active_folders[0].path[:25]}..."
            
        # Update the UI directly
        self.ui.folder_summary_lbl.config(text=summary)
        # Update quick stats (Pills)
        self.ui.stat_dirs.config(text=str(count))

        # Update Webhook summary
        active_hooks = [w for w in self.webhooks if w.is_enabled]
        hook_summary = f"• {len(active_hooks)} webhooks active"
        self.ui.webhook_summary_lbl.config(text=hook_summary)
        self.ui.stat_hooks.config(text=str(len(active_hooks)))
    
    def _handle_log(self, data):
        print(f"[{data.get('level', 'info')}] {data.get('message', '')}")

        if self.ui:
            self.ui.append_log(data.get("message", ""), data.get("level", "info"))

    def _open_folder_manager(self):
        """Callback to open and handle the Folder Manager dialog."""
        def on_save(updated_folders):
            self.folders = updated_folders
            # Update config and persist
            self.config.set("folders", [f.to_dict() for f in self.folders])
            self.config.save()
            # Refresh UI
            self._update_summaries()
            self.ui.append_log("Folder configuration saved", "ok")

        FolderManager(self.root, self.folders, self.theme, on_save)
    
    def _open_webhook_manager(self):
        """Callback to handle Webhook and Profile management."""
        def on_webhooks_save(updated_webhooks):
            self.webhooks = updated_webhooks
            self.config.set("webhooks", [w.to_dict() for w in self.webhooks])
            self.config.save()
            self._update_summaries()

        def on_profiles_save(updated_profiles):
            self.profiles = updated_profiles
            self.config.set("shared_profiles", [p.__dict__ for p in self.profiles])
            self.config.save()

        WebhookManager(self.root, self.webhooks, self.profiles, self.theme, 
                       on_webhooks_save, on_profiles_save)
    
    def _open_settings_manager(self):
        """Opens settings and refreshes the theme/config if changed."""
        def on_settings_save():
            self._load_data_models()

            self._update_summaries()
            self.ui.append_log("Settings updated successfully", "ok")

            if self.monitor.is_running:
                self.ui.append_log("Restart monitoring to apply behaviour changes", "warn")
        
        SettingsManager(self.root, self.config, self.theme, on_settings_save)
    
    #region Monitoring Logic

    def _toggle_monitoring(self):
        """Starts or stops the monitoring process based on current state."""
        if self.monitor.is_running:
            self.monitor.stop()
            return
        
            
        active_folders = [f for f in self.folders if f.is_enabled]
        active_hooks = [w for w in self.webhooks if w.is_enabled]

        if not active_folders or not active_hooks:
            self.ui.append_log("Need at least one enabled folder and webhook", "err")
            return

        self.session_sent = 0
        self.session_failed = 0
        self._update_session_pills()
        
        # Start service
        settings = {
            "scan_rate": self.config.get("scan_rate"),
            "file_delay": self.config.get("file_delay"),
            "send_timeout": self.config.get("send_timeout")
        }
        self.monitor.start(self.folders, self.webhooks, self.profiles, settings)

    def _on_monitor_started(self, _):
        self.ui.start_btn.config(text="Stop Monitoring", bg=self.theme.danger, fg="white")
        self.ui.status_pill.config(text=" MONITORING ", bg="#1a3320", fg=self.theme.accent2)
        self.ui.append_log("Monitoring service started", "ok")
    
    def _on_monitor_stopped(self, _):
        self.ui.start_btn.config(text="Start Monitoring", bg=self.theme.accent2, fg=self.theme.bg)
        self.ui.status_pill.config(text=" STOPPED ", bg="#2a1a1a", fg=self.theme.danger)
        self.ui.append_log("Monitoring service stopped", "warn")
    
    def _on_stats_updated(self, data):
        """Triggered when an image is sent (success or fail)."""
        is_success = data.get("is_success", False)
        if is_success:
            self.session_sent += 1
            if self.config.get("sound_enabled"):
                self.audio.play_sound("validation.mp3", self.config.get("sound_volume"))
        else:
            self.session_failed += 1
            if self.config.get("sound_enabled"):
                self.audio.play_sound("exclamation.mp3", self.config.get("sound_volume"))
        
        self._update_session_pills()

    def _update_session_pills(self):
        """Updates the sent/failed counters in the UI."""
        self.ui.stat_sent.config(text=str(self.session_sent))
        self.ui.stat_fail.config(text=str(self.session_failed))
    
    def run(self):
        self.root.mainloop()