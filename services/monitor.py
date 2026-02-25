import time
import os
from threading import Thread, Event
from typing import List, Set
from core.events import EventBus, AppEvents
from models.folder import FolderModel
from models.webhook import WebhookModel, SharedProfileModel
from services.scanner import ImageScanner
from services.sender import ISender

class MonitoringService:
    """
    Main service that monitors folders and dispatches images to webhooks.
    """

    def __init__(self, sender: ISender, scanner: ImageScanner):
        self.sender = sender
        self.scanner = scanner
        self._stop_event = Event()
        self._seen_files: Set[str] = set()
    
    def start(self, folders: List[FolderModel], webhooks: List[WebhookModel],
              profiles: List[SharedProfileModel], settings: dict):
        self._stop_event.clear()
        self._seen_files.clear()

        for folder in folders:
            if folder.is_enabled:
                for img_path in self.scanner.walk_images(folder.path, folder.is_recursive):
                    self._seen_files.add(img_path)
        
        Thread(target=self._main_loop, args=(folders, webhooks, profiles, settings), daemon=True).start()
        EventBus.emit(AppEvents.MONITORING_STARTED)
    
    def stop(self):
        self._stop_event.set()
        EventBus.emit(AppEvents.MONITORING_STOPPED)
    
    def _main_loop(self, folders: List[FolderModel], webhooks: List[WebhookModel],
                   profiles: List[SharedProfileModel], settings: dict):
        scan_rate = settings.get("scan_rate", 1.0)

        while not self._stop_event.is_set():
            for folder in [f for f in folders if f.is_enabled]:
                for img_path in self.scanner.walk_images(folder.path, folder.is_recursive):
                    if img_path not in self._seen_files:
                        self._process_new_image(img_path, webhooks, profiles, settings)
                        self._seen_files.add(img_path)

            time.sleep(scan_rate)
    
    def _process_new_image(self, img_path: str, webhooks: List[WebhookModel],
                           profiles: List[SharedProfileModel], settings: dict):
        filename = os.path.basename(img_path)

        # Settle delay to ensure file is completely written to disk
        time.sleep(settings.get("file_delay", 0.8))

        if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
            return
        
        success_count = 0
        enabled_webhooks = [w for w in webhooks if w.is_enabled]

        for webhook in enabled_webhooks:
            profile = next((p for p in profiles if p.name == webhook.shared_profile_name), None)

            ok = self.sender.send_image(
                img_path, webhook.url, settings.get("send_timeout", 30), profile
            )

            if ok: success_count += 1

            EventBus.emit(AppEvents.LOG_EMITTED, {
                "message": f"Sent {filename} to {webhook.name}",
                "level": "ok" if ok else "err"
            })
        
        EventBus.emit(AppEvents.STATS_UPDATED, {
            "is_success": success_count == len(enabled_webhooks)
        })