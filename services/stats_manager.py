import json
import os
import time
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Any

class StatsManager:
    def __init__(self, path: str, config: dict):
        self.path = path
        self.config = config
        self.sends = []
        self.errors = []
        self.load()
    
    def load(self):
        if os.path.exists(self.path):
            try: 
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    self.sends = data.get("sends", [])
                    self.errors = data.get("errors", [])
            except:
                self.sends, self.errors = [], []
    
    def save(self):
        max_sends = self.config.get("max_send_records", 100000)
        max_errors = self.config.get("max_error_records", 2000)

        data = {
            "sends": self.sends[-max_sends:],
            "errors": self.errors[-max_errors:]
        }
        with open(self.path, 'w') as f:
            json.dump(data, f)
    
    def record_event(self, ok: bool, filename: str, webhook: str, folder: str, ext: str, error_type: str = "General", detail: str = ""):
        ts = time.strftime("%H:%M:%S")
        month = time.strftime("%Y-%m")
        
        self.sends.append({
            "time": ts, "month": month, "file": filename,
            "webhook": webhook, "folder": folder, "ext": ext, "ok": ok
        })
        
        if not ok:
            self.errors.append({
                "time": ts, "type": error_type, "file": filename,
                "webhook": webhook, "detail": detail
            })
        
        if len(self.sends) % self.config.get("autosave_interval", 10) == 0:
            self.save()
    

    def get_monthly_data(self, n_months: int) -> List[Tuple[str, int]]:
        now = datetime.now()
        slots = []

        for offset in range (n_months - 1, -1, -1):
            m = now.month - offset
            y = now.year

            while m <= 0:
                m += 12
                y -= 1
            
            key = f"{y}-{m:02d}"
            label = datetime(y, m, 1).strftime("%b %y")
            slots.append((key, label))
        
        month_counts = Counter(record.get("month") for record in self.sends if record.get("ok") is True)

        result = []

        for key, label in slots:
            count = month_counts.get(key, 0)
            result.append((label, count))
        return result
    
    def get_distribution(self, field: str) -> List[Tuple[str, int]]:
        counts = Counter(s.get(field, "Unknown") for s in self.sends if s.get("ok"))
        return sorted(counts.items(), key=lambda x: -x[1])