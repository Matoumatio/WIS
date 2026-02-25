import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import time
import requests
import json
from threading import Thread
from abc import ABC, abstractmethod
import mimetypes
from collections import defaultdict, Counter
from datetime import datetime
from typing import Callable, List, Dict, Any, Optional, Tuple

# ── Optional audio ───────────────────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.init()
    _PYGAME_OK = True
except Exception:
    _PYGAME_OK = False

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Module-level constant : avoids rebuilding the dict on every log() call ───
_LOG_ICONS: Dict[str, str] = {
    "ok": "✓", "err": "✗", "warn": "!", "info": "·", "debug": ">",
}

# ─────────────────────────────────────────────
#  DEFAULTS & THEMES
# ─────────────────────────────────────────────
DEFAULTS: Dict[str, Any] = {
    "bg": "#0f1117", "bg2": "#181c26", "bg3": "#1f2433",
    "accent": "#4f8ef7", "accent2": "#2ecc8f", "danger": "#e05252",
    "warning": "#f0a500", "fg": "#d6dce8", "fg2": "#7a8499", "border": "#2a3045",
    "scan_rate": 15.0, "send_timeout": 15, "file_delay": 0.8,
    "formats": ".jpg,.jpeg,.png,.gif,.bmp,.webp",
    "sound_enabled": True, "sound_volume": 0.8,
    "theme_folder": "",
}

COLOR_KEYS: List[str] = [
    "bg", "bg2", "bg3", "accent", "accent2", "danger", "warning", "fg", "fg2", "border",
]

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "Dark Blue (default)": {
        "bg": "#0f1117", "bg2": "#181c26", "bg3": "#1f2433",
        "accent": "#4f8ef7", "accent2": "#2ecc8f", "danger": "#e05252",
        "warning": "#f0a500", "fg": "#d6dce8", "fg2": "#7a8499", "border": "#2a3045",
    },
    "Nord": {
        "bg": "#2e3440", "bg2": "#3b4252", "bg3": "#434c5e",
        "accent": "#81a1c1", "accent2": "#a3be8c", "danger": "#bf616a",
        "warning": "#ebcb8b", "fg": "#eceff4", "fg2": "#9099a6", "border": "#4c566a",
    },
    "Dracula": {
        "bg": "#282a36", "bg2": "#313341", "bg3": "#383a4a",
        "accent": "#bd93f9", "accent2": "#50fa7b", "danger": "#ff5555",
        "warning": "#f1fa8c", "fg": "#f8f8f2", "fg2": "#9099a6", "border": "#44475a",
    },
    "Light": {
        "bg": "#f0f2f7", "bg2": "#ffffff", "bg3": "#e4e7ef",
        "accent": "#2563eb", "accent2": "#16a34a", "danger": "#dc2626",
        "warning": "#d97706", "fg": "#1e293b", "fg2": "#64748b", "border": "#cbd5e1",
    },
}

# Live color dict — mutated when settings change
C: Dict[str, Any] = dict(DEFAULTS)


def _lighten(hex_color: str, amt: int = 25) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(
        min(255, r + amt), min(255, g + amt), min(255, b + amt)
    )


def load_themes_from_folder(folder: str) -> Dict[str, Dict[str, str]]:
    """Scan a folder for .wistheme / .json files and return valid theme dicts keyed by name."""
    themes: Dict[str, Dict[str, str]] = {}
    if not folder or not os.path.isdir(folder):
        return themes
    for entry in sorted(os.scandir(folder), key=lambda e: e.name.lower()):
        if not entry.is_file():
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext not in (".wistheme", ".json"):
            continue
        try:
            with open(entry.path) as f:
                data = json.load(f)
            if not data.get("wis_theme"):
                continue
            colors = {
                k: v for k, v in data.get("colors", {}).items()
                if k in COLOR_KEYS and isinstance(v, str)
                and v.startswith("#") and len(v) == 7
            }
            if not colors:
                continue
            name = data.get("name") or os.path.splitext(entry.name)[0]
            themes[name] = colors
        except Exception:
            continue
    return themes


# ─────────────────────────────────────────────
#  ABSTRACTIONS
# ─────────────────────────────────────────────

class ISender(ABC):
    @abstractmethod
    def send(self, file_path: str, url: str, timeout: int,
             username: str = "", avatar_url: str = "") -> bool: ...


class IAudioPlayer(ABC):
    @abstractmethod
    def play(self, file_path: str, volume: float) -> None: ...


class IChartWidget(ABC):
    @abstractmethod
    def update_data(self, data: list) -> None: ...


# ─────────────────────────────────────────────
#  CONCRETE IMPLEMENTATIONS
# ─────────────────────────────────────────────

class HttpSender(ISender):
    def send(self, file_path: str, url: str, timeout: int,
             username: str = "", avatar_url: str = "") -> bool:
        fname = os.path.basename(file_path)
        mime, _ = mimetypes.guess_type(file_path)
        mime = mime or "application/octet-stream"
        with open(file_path, "rb") as fh:
            files = {"file": (fname, fh, mime)}
            if username or avatar_url:
                payload: Dict[str, str] = {}
                if username:   payload["username"]   = username
                if avatar_url: payload["avatar_url"] = avatar_url
                files["payload_json"] = (None, json.dumps(payload), "application/json")
            r = requests.post(url, files=files, timeout=timeout)
        return r.status_code in (200, 201, 204)


class NullSender(ISender):
    def send(self, file_path: str, url: str, timeout: int,
             username: str = "", avatar_url: str = "") -> bool:
        return True


class PygameAudioPlayer(IAudioPlayer):
    def play(self, file_path: str, volume: float) -> None:
        def _play():
            try:
                sound = pygame.mixer.Sound(file_path)
                sound.set_volume(max(0.0, min(1.0, volume)))
                sound.play()
            except Exception:
                pass
        Thread(target=_play, daemon=True).start()


class NullAudioPlayer(IAudioPlayer):
    def play(self, file_path: str, volume: float) -> None:
        pass


# ─────────────────────────────────────────────
#  SETTINGS STORE
# ─────────────────────────────────────────────

class SettingsStore:
    def __init__(self, path: str):
        self._path = path
        self.webhooks:     List[dict]   = []
        self.folders:      List[dict]   = []
        self.auto_start:   bool         = False
        self.debug_mode:   bool         = False
        self.custom_themes: Dict        = {}
        self.shared_profiles: List[dict] = []   # {name, username, avatar_url}
        self.values:       Dict[str, Any] = dict(DEFAULTS)
        self.stats_config: Dict = {
            "max_sends": 10000, "max_errors": 2000,
            "months": 12, "autosave_every": 10,
        }

    def load(self) -> None:
        try:
            if not os.path.exists(self._path):
                return
            with open(self._path) as f:
                s = json.load(f)
            self.webhooks      = s.get("webhooks",        [])
            self.folders       = s.get("folders",         [])
            self.auto_start    = s.get("auto_start",      False)
            self.debug_mode    = s.get("debug_mode",      False)
            self.custom_themes = s.get("custom_themes",   {})
            self.shared_profiles = s.get("shared_profiles", [])
            self.values.update({k: s[k] for k in DEFAULTS if k in s})
            sc = s.get("stats_config", {})
            self.stats_config.update({k: sc[k] for k in self.stats_config if k in sc})
            if not self.webhooks and s.get("webhook_url"):
                self.webhooks = [{"name": "Default", "url": s["webhook_url"], "enabled": True}]
            if not self.folders and s.get("folder_path"):
                self.folders = [{"path": s["folder_path"], "enabled": True, "recursive": False}]
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save(self) -> None:
        try:
            data = {
                "webhooks": self.webhooks, "folders": self.folders,
                "auto_start": self.auto_start, "debug_mode": self.debug_mode,
                "stats_config": self.stats_config, "custom_themes": self.custom_themes,
                "shared_profiles": self.shared_profiles,
            }
            data.update(self.values)
            with open(self._path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")


# ─────────────────────────────────────────────
#  STATISTICS STORE
# ─────────────────────────────────────────────

class StatisticsStore:
    def __init__(self, path: str, config: Dict):
        self._path   = path
        self._config = config
        self.sends:  List[dict] = []
        self.errors: List[dict] = []

    def load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path) as f:
                    data = json.load(f)
                self.sends  = data.get("sends",  [])
                self.errors = data.get("errors", [])
        except Exception as e:
            print(f"Error loading stats: {e}")

    def save(self) -> None:
        try:
            max_s = self._config.get("max_sends",  10000)
            max_e = self._config.get("max_errors",  2000)
            self.sends  = self.sends [-max(1, max_s):]
            self.errors = self.errors[-max(1, max_e):]
            with open(self._path, "w") as f:
                json.dump({"sends": self.sends, "errors": self.errors}, f)
        except Exception as e:
            print(f"Error saving stats: {e}")

    def record_send(self, *, ok: bool, file: str, webhook: str, folder: str,
                    ext: str, err_type: str = "", detail: str = "") -> None:
        ts    = time.strftime("%H:%M:%S")
        month = time.strftime("%Y-%m")
        self.sends.append({"time": ts, "month": month, "file": file,
                           "webhook": webhook, "folder": folder, "ext": ext, "ok": ok})
        if not ok:
            self.errors.append({"time": ts, "type": err_type, "file": file,
                                "webhook": webhook, "detail": detail})
        every = max(1, self._config.get("autosave_every", 10))
        if len(self.sends) % every == 0:
            Thread(target=self.save, daemon=True).start()

    def clear(self) -> None:
        self.sends  = []
        self.errors = []

    def months_data(self, n: int) -> List[Tuple[str, int]]:
        now = datetime.now()
        slots: List[Tuple[str, str]] = []
        for offset in range(n - 1, -1, -1):
            m = now.month - offset
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            slots.append((f"{y}-{m:02d}", datetime(y, m, 1).strftime("%b %y")))
        month_counts: Counter = Counter(s.get("month") for s in self.sends)
        return [(label, month_counts.get(key, 0)) for key, label in slots]

    def _count_by(self, field: str, source: Optional[List[dict]] = None,
                  ok_only: bool = True) -> List[Tuple[str, int]]:
        data = source if source is not None else self.sends
        counts: Dict[str, int] = defaultdict(int)
        for item in data:
            if ok_only and not item.get("ok"):
                continue
            counts[item.get(field, "Unknown")] += 1
        return sorted(counts.items(), key=lambda x: -x[1])

    def webhook_data(self)    -> List[Tuple[str, int]]: return self._count_by("webhook")
    def folder_data(self)     -> List[Tuple[str, int]]: return self._count_by("folder")
    def ext_data(self)        -> List[Tuple[str, int]]: return self._count_by("ext")
    def error_type_data(self) -> List[Tuple[str, int]]:
        return self._count_by("type", source=self.errors, ok_only=False)

    def webhook_table(self) -> List[Tuple]:
        wh: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        for s in self.sends:
            rec = wh[s.get("webhook", "Unknown")]
            if s.get("ok"):
                rec[0] += 1
            else:
                rec[1] += 1
        rows = []
        for name, (ok, fail) in sorted(wh.items(), key=lambda x: -x[1][0]):
            tot  = ok + fail
            rate = f"{100 * ok / tot:.1f}%" if tot else "—"
            rows.append((name, ok, fail, rate))
        return rows


# ─────────────────────────────────────────────
#  FOLDER SCANNER
# ─────────────────────────────────────────────

class FolderScanner:
    def __init__(self, formats: set):
        self._formats = formats

    def iter_images(self, root: str, recursive: bool):
        if recursive:
            for dirpath, _, files in os.walk(root):
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in self._formats:
                        yield os.path.join(dirpath, fn)
        else:
            try:
                with os.scandir(root) as it:
                    for entry in it:
                        if entry.is_file() and \
                                os.path.splitext(entry.name)[1].lower() in self._formats:
                            yield entry.path
            except Exception:
                pass


# ─────────────────────────────────────────────
#  MONITORING SERVICE
# ─────────────────────────────────────────────

_SEND_ERRORS: Tuple = (
    (requests.exceptions.Timeout,         "Timeout",          "Timeout"),
    (requests.exceptions.ConnectionError,  "Connection error", "Connection Error"),
)


class MonitoringService:
    def __init__(self,
                 sender:      ISender,
                 audio:       IAudioPlayer,
                 stats:       StatisticsStore,
                 on_log:      Callable[[str, str], None],
                 on_counters: Callable[[int, int], None]):
        self._sender      = sender
        self._audio       = audio
        self._stats       = stats
        self._on_log      = on_log
        self._on_counters = on_counters
        self._running     = False
        self._sent_files: set = set()
        self._sent_count  = 0
        self._fail_count  = 0

    @property
    def running(self) -> bool:
        return self._running

    def start(self, folders: list, webhooks: list, settings: dict, debug: bool) -> None:
        self._running    = True
        self._sent_count = 0
        self._fail_count = 0
        self._sent_files.clear()
        scanner = FolderScanner(self._formats(settings))
        self._snapshot(folders, scanner)
        Thread(target=self._loop,
               args=(folders, webhooks, settings, debug, scanner),
               daemon=True).start()

    def stop(self) -> None:
        self._running = False

    @staticmethod
    def _formats(settings: dict) -> set:
        raw = settings.get("formats", DEFAULTS["formats"])
        return {e.strip().lower() for e in raw.split(",") if e.strip()}

    def _snapshot(self, folders: list, scanner: FolderScanner) -> None:
        new_files = {
            os.path.abspath(fp)
            for fc in folders
            for fp in scanner.iter_images(fc["path"], fc.get("recursive", False))
        }
        self._sent_files.update(new_files)
        self._on_log(f"Snapshot: {len(new_files)} existing file(s) marked as seen", "debug")

    def _loop(self, folders, webhooks, settings, debug, scanner: FolderScanner) -> None:
        scan_rate  = float(settings.get("scan_rate",  1.0))
        file_delay = float(settings.get("file_delay", 0.8))
        timeout    = int(settings.get("send_timeout", 30))
        volume     = float(settings.get("sound_volume", 0.8))
        scan = 0
        while self._running:
            scan += 1
            if debug:
                self._on_log(f"Scan #{scan}", "debug")
            for fc in folders:
                try:
                    self._scan_folder(fc, webhooks, scanner, file_delay, timeout, volume)
                except Exception as e:
                    self._on_log(f"Error scanning {fc['path']}: {e}", "err")
            time.sleep(scan_rate)

    def _scan_folder(self, fc, webhooks, scanner, file_delay, timeout, volume) -> None:
        folder_path = fc["path"]
        recursive   = fc.get("recursive", False)
        base_name   = os.path.basename(folder_path)
        for fp in scanner.iter_images(folder_path, recursive):
            abs_fp = os.path.abspath(fp)
            if abs_fp in self._sent_files:
                continue
            rel = os.path.relpath(abs_fp, folder_path)
            self._on_log(f"New: {rel}  [{base_name}]", "info")
            time.sleep(file_delay)
            if not os.path.exists(abs_fp):
                continue
            try:
                if os.path.getsize(abs_fp) == 0:
                    self._on_log(f"Empty, skipping: {rel}", "warn")
                    continue
            except Exception:
                continue
            all_ok = all(
                self._send_to_webhook(abs_fp, wh, folder_path, timeout) for wh in webhooks
            )
            self._sent_files.add(abs_fp)
            snd = os.path.join(_SCRIPT_DIR, "validation.mp3" if all_ok else "exclamation.mp3")
            if os.path.isfile(snd):
                self._audio.play(snd, volume)
            self._sent_count += all_ok
            self._fail_count += not all_ok
            self._on_counters(self._sent_count, self._fail_count)

    def _send_to_webhook(self, abs_fp: str, wh: dict, folder_path: str, timeout: int) -> bool:
        fname = os.path.basename(abs_fp)
        url   = wh.get("url", "")
        name  = wh.get("name", "?")
        ext   = os.path.splitext(fname)[1].lower()

        # Shared profile identity override
        profile  = wh.get("_resolved_profile") or {}
        username   = profile.get("username", "")
        avatar_url = profile.get("avatar_url", "")

        def _record(ok: bool, log_msg: str, log_kind: str,
                    err_type: str = "", detail: str = "") -> bool:
            self._on_log(log_msg, log_kind)
            self._stats.record_send(ok=ok, file=fname, webhook=name,
                                    folder=folder_path, ext=ext,
                                    err_type=err_type, detail=detail)
            return ok

        try:
            ok = self._sender.send(abs_fp, url, timeout, username=username, avatar_url=avatar_url)
            if ok:
                return _record(True, f"{fname}  →  {name}", "ok")
            return _record(False, f"Non-2xx  {fname}  →  {name}", "err",
                           "HTTP Error", "Non-2xx response")
        except tuple(exc for exc, _, __ in _SEND_ERRORS) as e:
            for exc_type, log_label, err_label in _SEND_ERRORS:
                if isinstance(e, exc_type):
                    return _record(False, f"{log_label}  {fname}  →  {name}", "err",
                                   err_label, str(e)[:120])
        except Exception as e:
            return _record(False, f"Error  {fname}  →  {name}: {e}", "err",
                           type(e).__name__, str(e)[:120])
        return False


# ─────────────────────────────────────────────
#  WIDGET FACTORIES
# ─────────────────────────────────────────────

def apply_treeview_style() -> None:
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Treeview", background=C["bg2"], foreground=C["fg"],
                fieldbackground=C["bg2"], rowheight=26, font=("Segoe UI", 9))
    s.configure("Treeview.Heading", background=C["bg3"], foreground=C["accent"],
                font=("Segoe UI", 9, "bold"), relief="flat")
    s.map("Treeview",
          background=[("selected", C["bg3"])],
          foreground=[("selected", C["accent"])])
    s.configure("Vertical.TScrollbar", background=C["bg3"],
                troughcolor=C["bg2"], arrowcolor=C["fg2"])


def mk_btn(parent, text, command, color=None, fg=None, **kw):
    color   = color or C["bg3"]
    fg      = fg    or C["accent"]
    lighter = _lighten(color)
    b = tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                  activebackground=lighter, activeforeground=fg,
                  relief="flat", bd=0, padx=12, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2", **kw)
    b.bind("<Enter>", lambda e: b.config(bg=lighter))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


def mk_entry(parent, textvariable=None, width=40):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=C["bg3"], fg=C["fg"], insertbackground=C["accent"],
                    relief="flat", bd=0, font=("Segoe UI", 9),
                    highlightthickness=1, highlightbackground=C["border"],
                    highlightcolor=C["accent"])


def mk_label(parent, text, fg=None, font=None, bg=None, **kw):
    bg = bg if bg is not None else C["bg"]
    return tk.Label(parent, text=text, bg=bg, fg=fg or C["fg"],
                    font=font or ("Segoe UI", 9), **kw)


def mk_sep(parent):
    tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=6)


def mk_chk(parent, text, variable, command=None, bg=None):
    bg = bg if bg is not None else C["bg"]
    return tk.Checkbutton(parent, text=text, variable=variable,
                          bg=bg, fg=C["fg"], selectcolor=C["bg3"],
                          activebackground=bg, activeforeground=C["fg"],
                          font=("Segoe UI", 9), highlightthickness=0, command=command)


def mk_section(parent, text):
    tk.Label(parent, text=text, bg=C["bg"], fg=C["fg2"],
             font=("Segoe UI", 7, "bold")).pack(anchor="w")
    tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=3)


# ─────────────────────────────────────────────
#  TREEVIEW PANEL
# ─────────────────────────────────────────────

class TreePanel(tk.Frame):
    def __init__(self, parent, columns, headings, widths, height=9):
        super().__init__(parent, bg=C["bg"])
        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                  height=height, selectmode="browse")
        for col, hd, w in zip(columns, headings, widths):
            self.tree.heading(col, text=hd)
            self.tree.column(col, width=w,
                             anchor="center" if w <= 60 else "w",
                             stretch=(col == columns[-1]))
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def selected_idx(self) -> Optional[int]:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def clear(self):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

    def insert(self, iid, values):
        self.tree.insert("", "end", iid=str(iid), values=values)


# ─────────────────────────────────────────────
#  BASE POPUP
# ─────────────────────────────────────────────

class BasePopup(tk.Toplevel):
    def __init__(self, parent, title, subtitle="", size="560x500"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.geometry(size)

        hdr = tk.Frame(self, bg=C["bg2"])
        hdr.pack(fill="x", side="top")
        mk_label(hdr, title, fg=C["accent"], bg=C["bg2"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=14, pady=10)
        if subtitle:
            mk_label(hdr, subtitle, fg=C["fg2"], bg=C["bg2"],
                     font=("Segoe UI", 8)).pack(side="left")

        self._footer_frame = tk.Frame(self, bg=C["bg"])
        self._footer_frame.pack(fill="x", side="bottom", padx=12, pady=8)
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", side="bottom")

        self.body = tk.Frame(self, bg=C["bg"])
        self.body.pack(fill="both", expand=True, padx=14, pady=10, side="top")

    def add_footer_buttons(self, save_cmd, cancel_cmd=None):
        mk_btn(self._footer_frame, "Save & Close", save_cmd,
               color=C["accent"], fg=C["bg"]).pack(side="right", padx=(4, 0))
        mk_btn(self._footer_frame, "Cancel",
               cancel_cmd or self.destroy,
               color=C["bg3"], fg=C["fg2"]).pack(side="right")


# ─────────────────────────────────────────────
#  SHARED PROFILE MANAGER
# ─────────────────────────────────────────────

class SharedProfileManager(BasePopup):
    """Manage named identity profiles (username + avatar URL) for shared webhooks."""

    def __init__(self, parent, profiles: list, on_save: Callable):
        super().__init__(parent, "Shared Profiles",
                         "Identities that override a webhook's default appearance",
                         size="580x540")
        self.profiles  = [dict(p) for p in profiles]
        self.on_save   = on_save
        self._edit_idx = None
        self._build()
        self._refresh()

    def _build(self):
        b = self.body

        top = tk.Frame(b, bg=C["bg"])
        top.pack(fill="x", side="top")
        self.panel = TreePanel(top,
            columns=("name", "username", "avatar"),
            headings=("Profile Name", "Display Username", "Avatar URL"),
            widths=(130, 140, 260), height=6)
        self.panel.pack(fill="x")

        act = tk.Frame(top, bg=C["bg"])
        act.pack(fill="x", pady=(4, 0))
        mk_btn(act, "Edit",   self._edit,   color=C["bg3"], fg=C["accent"]).pack(side="left", padx=(0, 4))
        mk_btn(act, "Remove", self._remove, color=C["bg3"], fg=C["danger"]).pack(side="left", padx=4)

        tk.Frame(b, bg=C["border"], height=1).pack(fill="x", pady=8, side="top")

        bottom = tk.Frame(b, bg=C["bg"])
        bottom.pack(fill="x", side="top")
        mk_label(bottom, "Add / Edit Profile", fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        for label, attr in [("Profile name:", "_pname_var"),
                             ("Display username:", "_pusername_var"),
                             ("Avatar image URL:", "_pavatar_var")]:
            row = tk.Frame(bottom, bg=C["bg"])
            row.pack(fill="x", pady=2)
            mk_label(row, label, fg=C["fg2"], width=18, anchor="w").pack(side="left")
            var = tk.StringVar()
            setattr(self, attr, var)
            mk_entry(row, textvariable=var, width=42).pack(side="left", padx=(4, 0),
                                                            fill="x", expand=True)

        mk_label(bottom,
                 "Avatar URL must be a direct image link (https://…).  Leave blank to keep default.",
                 fg=C["fg2"], font=("Segoe UI", 7)).pack(anchor="w", pady=(4, 0))

        btn_row = tk.Frame(bottom, bg=C["bg"])
        btn_row.pack(fill="x", pady=(8, 0))
        self._add_btn = mk_btn(btn_row, "+ Add", self._commit, color=C["accent2"], fg=C["bg"])
        self._add_btn.pack(side="left")
        mk_btn(btn_row, "Clear", self._clear_form, color=C["bg3"], fg=C["fg2"]).pack(side="left", padx=8)

        self.add_footer_buttons(self._save)

    def _refresh(self):
        self.panel.clear()
        for i, p in enumerate(self.profiles):
            self.panel.insert(i, (p.get("name", ""),
                                  p.get("username", ""),
                                  p.get("avatar_url", "")))

    def _edit(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        p = self.profiles[idx]
        self._pname_var.set(p.get("name", ""))
        self._pusername_var.set(p.get("username", ""))
        self._pavatar_var.set(p.get("avatar_url", ""))
        self._edit_idx = idx
        self._add_btn.config(text="Update")

    def _remove(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        name = self.profiles[idx].get("name", "this profile")
        if messagebox.askyesno("Remove", f"Remove profile '{name}'?", parent=self):
            del self.profiles[idx]
            self._refresh()

    def _commit(self):
        name     = self._pname_var.get().strip()
        username = self._pusername_var.get().strip()
        avatar   = self._pavatar_var.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Enter a profile name.", parent=self); return
        if not username:
            messagebox.showwarning("Missing", "Enter a display username.", parent=self); return
        if avatar and not avatar.startswith("http"):
            messagebox.showwarning("Invalid URL", "Avatar URL must start with http.", parent=self); return
        if self._edit_idx is not None:
            self.profiles[self._edit_idx].update(name=name, username=username, avatar_url=avatar)
            self._edit_idx = None
        else:
            # Prevent duplicate names
            if name in {p["name"] for p in self.profiles}:
                messagebox.showwarning("Duplicate", f"A profile named '{name}' already exists.",
                                       parent=self); return
            self.profiles.append({"name": name, "username": username, "avatar_url": avatar})
        self._clear_form()
        self._refresh()

    def _clear_form(self):
        self._pname_var.set("")
        self._pusername_var.set("")
        self._pavatar_var.set("")
        self._edit_idx = None
        self._add_btn.config(text="+ Add")

    def _save(self):
        try:    self.on_save(self.profiles)
        finally: self.destroy()


# ─────────────────────────────────────────────
#  WEBHOOK MANAGER
# ─────────────────────────────────────────────

class WebhookManager(BasePopup):
    def __init__(self, parent, webhooks: list, profiles: list, on_save: Callable):
        super().__init__(parent, "Webhook Manager",
                         "One detection is sent to all enabled webhooks", size="620x600")
        self.webhooks  = [dict(w) for w in webhooks]
        self.profiles  = profiles   # live reference (read-only here)
        self.on_save   = on_save
        self._edit_idx = None
        self._build()
        self._refresh()

    def _profile_names(self) -> List[str]:
        return [p["name"] for p in self.profiles]

    def _build(self):
        b = self.body
        top = tk.Frame(b, bg=C["bg"])
        top.pack(fill="x", side="top")
        self.panel = TreePanel(top, columns=("on", "name", "profile", "url"),
                               headings=("On", "Name", "Shared Profile", "URL"),
                               widths=(44, 120, 120, 260), height=7)
        self.panel.pack(fill="x")
        act = tk.Frame(top, bg=C["bg"])
        act.pack(fill="x", pady=(4, 0))
        mk_btn(act, "Edit",   self._edit,   color=C["bg3"], fg=C["accent"]).pack(side="left", padx=(0, 4))
        mk_btn(act, "Toggle", self._toggle, color=C["bg3"], fg=C["warning"]).pack(side="left", padx=4)
        mk_btn(act, "Remove", self._remove, color=C["bg3"], fg=C["danger"]).pack(side="left", padx=4)
        tk.Frame(b, bg=C["border"], height=1).pack(fill="x", pady=8, side="top")
        bottom = tk.Frame(b, bg=C["bg"])
        bottom.pack(fill="x", side="top")
        mk_label(bottom, "Add / Edit Webhook", fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        name_row = tk.Frame(bottom, bg=C["bg"])
        name_row.pack(fill="x", pady=2)
        mk_label(name_row, "Name:", fg=C["fg2"], width=6, anchor="w").pack(side="left")
        self._name_var = tk.StringVar()
        mk_entry(name_row, textvariable=self._name_var, width=26).pack(side="left", padx=(4, 0))
        url_row = tk.Frame(bottom, bg=C["bg"])
        url_row.pack(fill="x", pady=2)
        mk_label(url_row, "URL:", fg=C["fg2"], width=6, anchor="w").pack(side="left")
        self._url_var = tk.StringVar()
        mk_entry(url_row, textvariable=self._url_var, width=56).pack(
            side="left", padx=(4, 0), fill="x", expand=True)

        # ── Shared profile section ──────────────────────────────────────────
        tk.Frame(bottom, bg=C["border"], height=1).pack(fill="x", pady=(8, 4))
        mk_label(bottom, "Shared Profile  (optional)", fg=C["accent2"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        sp_row = tk.Frame(bottom, bg=C["bg"])
        sp_row.pack(fill="x", pady=(4, 0))
        self._sp_enabled_var = tk.BooleanVar(value=False)
        self._sp_chk = mk_chk(sp_row, "Enable shared profile for this webhook",
                               self._sp_enabled_var, command=self._on_sp_toggle, bg=C["bg"])
        self._sp_chk.pack(side="left")

        sp_pick_row = tk.Frame(bottom, bg=C["bg"])
        sp_pick_row.pack(fill="x", pady=(4, 2))
        mk_label(sp_pick_row, "Profile:", fg=C["fg2"], width=8, anchor="w").pack(side="left")
        names = self._profile_names()
        self._sp_var = tk.StringVar(value=names[0] if names else "")
        self._sp_menu = tk.OptionMenu(sp_pick_row, self._sp_var, *(names or ["— no profiles —"]))
        self._sp_menu.config(bg=C["bg3"], fg=C["fg"], activebackground=C["bg2"],
                             activeforeground=C["accent"], highlightthickness=0,
                             relief="flat", font=("Segoe UI", 9), bd=0, width=20)
        self._sp_menu["menu"].config(bg=C["bg3"], fg=C["fg"], font=("Segoe UI", 9))
        self._sp_menu.pack(side="left", padx=(4, 0))
        mk_btn(sp_pick_row, "+ Manage Profiles", self._open_profile_manager,
               color=C["bg3"], fg=C["accent2"]).pack(side="left", padx=(8, 0))

        mk_label(bottom,
                 "The selected profile's username & avatar will override the webhook's default identity.",
                 fg=C["fg2"], font=("Segoe UI", 7)).pack(anchor="w", pady=(2, 0))

        self._on_sp_toggle()   # set initial enable/disable state

        btn_row = tk.Frame(bottom, bg=C["bg"])
        btn_row.pack(fill="x", pady=(10, 0))
        self._add_btn = mk_btn(btn_row, "+ Add", self._commit, color=C["accent2"], fg=C["bg"])
        self._add_btn.pack(side="left")
        mk_btn(btn_row, "Clear", self._clear_form, color=C["bg3"], fg=C["fg2"]).pack(side="left", padx=8)
        self.add_footer_buttons(self._save)

    def _on_sp_toggle(self):
        state = "normal" if self._sp_enabled_var.get() else "disabled"
        self._sp_menu.config(state=state)

    def _rebuild_sp_menu(self):
        names = self._profile_names()
        menu = self._sp_menu["menu"]
        menu.delete(0, "end")
        for n in names:
            menu.add_command(label=n, command=lambda v=n: self._sp_var.set(v))
        if names:
            if self._sp_var.get() not in names:
                self._sp_var.set(names[0])
        else:
            self._sp_var.set("")

    def _open_profile_manager(self):
        def on_save(profiles):
            self.profiles[:] = profiles
            self._rebuild_sp_menu()
        SharedProfileManager(self, self.profiles, on_save)

    def _refresh(self):
        self.panel.clear()
        for i, w in enumerate(self.webhooks):
            profile_label = ""
            if w.get("shared_profile_enabled") and w.get("shared_profile"):
                profile_label = f"✔ {w['shared_profile']}"
            self.panel.insert(i, ("✔" if w.get("enabled", True) else "—",
                                  w.get("name", ""), profile_label,
                                  w.get("url", "")))

    def _edit(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        w = self.webhooks[idx]
        self._name_var.set(w.get("name", ""))
        self._url_var.set(w.get("url", ""))
        self._sp_enabled_var.set(bool(w.get("shared_profile_enabled")))
        sp = w.get("shared_profile", "")
        names = self._profile_names()
        if sp and sp in names:
            self._sp_var.set(sp)
        elif names:
            self._sp_var.set(names[0])
        self._on_sp_toggle()
        self._edit_idx = idx
        self._add_btn.config(text="Update")

    def _toggle(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        self.webhooks[idx]["enabled"] = not self.webhooks[idx].get("enabled", True)
        self._refresh()

    def _remove(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        name = self.webhooks[idx].get("name", "this webhook")
        if messagebox.askyesno("Remove", f"Remove '{name}'?", parent=self):
            del self.webhooks[idx]
            self._refresh()

    def _commit(self):
        name = self._name_var.get().strip()
        url  = self._url_var.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Enter a name.", parent=self); return
        if not url.startswith("http"):
            messagebox.showwarning("Invalid URL", "URL must start with http.", parent=self); return
        sp_enabled = self._sp_enabled_var.get()
        sp_name    = self._sp_var.get() if sp_enabled else ""
        if sp_enabled and not self._profile_names():
            messagebox.showwarning("No Profiles",
                "No shared profiles exist yet.\nCreate one via Settings → Shared Profiles.",
                parent=self); return
        entry = {"name": name, "url": url, "enabled": True,
                 "shared_profile_enabled": sp_enabled,
                 "shared_profile": sp_name}
        if self._edit_idx is not None:
            entry["enabled"] = self.webhooks[self._edit_idx].get("enabled", True)
            self.webhooks[self._edit_idx] = entry
            self._edit_idx = None
        else:
            self.webhooks.append(entry)
        self._clear_form()
        self._refresh()

    def _clear_form(self):
        self._name_var.set("")
        self._url_var.set("")
        self._sp_enabled_var.set(False)
        self._on_sp_toggle()
        self._edit_idx = None
        self._add_btn.config(text="+ Add")

    def _save(self):
        try:    self.on_save(self.webhooks)
        finally: self.destroy()


# ─────────────────────────────────────────────
#  FOLDER MANAGER
# ─────────────────────────────────────────────

class FolderManager(BasePopup):
    def __init__(self, parent, folders: list, on_save: Callable):
        super().__init__(parent, "Folder Manager",
                         "All enabled folders are scanned simultaneously", size="640x540")
        self.folders = [dict(f) for f in folders]
        self.on_save = on_save
        self._build()
        self._refresh()

    def _build(self):
        b = self.body
        top = tk.Frame(b, bg=C["bg"])
        top.pack(fill="x", side="top")
        self.panel = TreePanel(top, columns=("on", "rec", "path"),
                               headings=("On", "Recursive", "Folder Path"),
                               widths=(44, 80, 440), height=7)
        self.panel.pack(fill="x")
        act = tk.Frame(top, bg=C["bg"])
        act.pack(fill="x", pady=(4, 0))
        mk_btn(act, "Toggle",           self._toggle,     color=C["bg3"], fg=C["warning"]).pack(side="left", padx=(0, 4))
        mk_btn(act, "Toggle Recursive", self._toggle_rec, color=C["bg3"], fg=C["accent"]).pack(side="left", padx=4)
        mk_btn(act, "Remove",           self._remove,     color=C["bg3"], fg=C["danger"]).pack(side="left", padx=4)
        tk.Frame(b, bg=C["border"], height=1).pack(fill="x", pady=8, side="top")
        bottom = tk.Frame(b, bg=C["bg"])
        bottom.pack(fill="x", side="top")
        mk_label(bottom, "Add Folder", fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))
        path_row = tk.Frame(bottom, bg=C["bg"])
        path_row.pack(fill="x", pady=(0, 6))
        self._path_var = tk.StringVar()
        mk_btn(path_row, "Browse", self._browse,
               color=C["bg3"], fg=C["fg"]).pack(side="right", padx=(6, 0))
        mk_entry(path_row, textvariable=self._path_var,
                 width=2).pack(side="left", fill="x", expand=True)
        self._recursive_var = tk.BooleanVar(value=True)
        mk_chk(bottom, "Recursive (include subfolders)", self._recursive_var,
               bg=C["bg"]).pack(anchor="w", pady=(0, 8))
        add_frame = tk.Frame(bottom, bg=C["bg"])
        add_frame.pack(fill="x")
        mk_btn(add_frame, "+ Add Folder", self._add,
               color=C["accent2"], fg=C["bg"]).pack(side="left")
        self.add_footer_buttons(self._save)

    def _refresh(self):
        self.panel.clear()
        for i, f in enumerate(self.folders):
            self.panel.insert(i, (
                "✔" if f.get("enabled",   True)  else "—",
                "✔" if f.get("recursive", False) else "—",
                f.get("path", ""),
            ))

    def _toggle(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        self.folders[idx]["enabled"] = not self.folders[idx].get("enabled", True)
        self._refresh()

    def _toggle_rec(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        self.folders[idx]["recursive"] = not self.folders[idx].get("recursive", False)
        self._refresh()

    def _remove(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        path = self.folders[idx].get("path", "?")
        if messagebox.askyesno("Remove", f"Remove '{os.path.basename(path)}'?", parent=self):
            del self.folders[idx]
            self._refresh()

    def _browse(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self._path_var.set(folder)

    def _add(self):
        path = self._path_var.get().strip()
        if not path:
            messagebox.showwarning("Missing", "Select or type a folder path.", parent=self); return
        if not os.path.isdir(path):
            messagebox.showwarning("Invalid", f"Not a valid directory:\n{path}", parent=self); return
        if path in {f["path"] for f in self.folders}:
            messagebox.showinfo("Duplicate", "This folder is already in the list.", parent=self); return
        self.folders.append({"path": path, "enabled": True, "recursive": self._recursive_var.get()})
        self._path_var.set("")
        self._refresh()

    def _save(self):
        try:    self.on_save(self.folders)
        finally: self.destroy()


# ─────────────────────────────────────────────
#  SETTINGS MANAGER
# ─────────────────────────────────────────────

_BEHAVIOUR_ROWS: List[Tuple[str, str, float]] = [
    ("Scan rate (seconds)",         "scan_rate",    1.0),
    ("Send timeout (seconds)",      "send_timeout", 30),
    ("File settle delay (seconds)", "file_delay",   0.8),
]

_STATS_ROWS: List[Tuple[str, str, int]] = [
    ("Max send records to keep",                "max_sends",       10000),
    ("Max error records to keep",               "max_errors",       2000),
    ("Months shown in bar chart",               "months",             12),
    ("Stats autosave every N sends  (0 = never)", "autosave_every",  10),
]

_COLOR_DEFS: List[Tuple[str, str]] = [
    ("bg",      "Background"),    ("bg2",     "Surface / header"),
    ("bg3",     "Input / card"),  ("accent",  "Accent (blue)"),
    ("accent2", "Success (green)"),("danger", "Danger (red)"),
    ("warning", "Warning (orange)"),("fg",    "Primary text"),
    ("fg2",     "Secondary text"),("border",  "Borders"),
]


class SettingsManager(BasePopup):
    def __init__(self, parent, store: SettingsStore, on_save: Callable):
        super().__init__(parent, "Settings", size="560x720")
        self._store         = store
        self._on_save       = on_save
        self._vars:         Dict[str, tk.Variable] = {}
        self._swatch_refs:  Dict[str, tk.Frame]    = {}
        self._custom_themes = dict(store.custom_themes)
        # Themes loaded from the theme folder (refreshed on demand)
        self._folder_themes: Dict[str, Dict[str, str]] = {}
        self._build()

    # ── Helpers shared across build phases ──────────────────────────────────

    def _all_preset_names(self) -> List[str]:
        """Built-ins  +  folder themes  +  custom (saved) themes — deduplicated, ordered."""
        seen  = set()
        names = []
        for n in list(THEME_PRESETS.keys()) \
               + list(self._folder_themes.keys()) \
               + list(self._custom_themes.keys()):
            if n not in seen:
                seen.add(n)
                names.append(n)
        return names

    def _lookup_preset(self, name: str) -> Optional[Dict[str, str]]:
        """Priority: built-in > folder > custom."""
        return (THEME_PRESETS.get(name)
                or self._folder_themes.get(name)
                or self._custom_themes.get(name))

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        b = self.body
        canvas = tk.Canvas(b, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(b, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner    = tk.Frame(canvas, bg=C["bg"])
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(inner_id, width=canvas.winfo_width())
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(inner_id, width=e.width))

        # ── Behaviour ──
        self._section(inner, "Behaviour")
        for label, key, default in _BEHAVIOUR_ROWS:
            self._num_row(inner, label, key, default, self._store.values)
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── File types ──
        self._section(inner, "Watched Extensions")
        mk_label(inner, "Comma-separated  (e.g.  .jpg,.png,.gif)",
                 fg=C["fg2"], font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        self._vars["formats"] = tk.StringVar(
            value=self._store.values.get("formats", DEFAULTS["formats"]))
        mk_entry(inner, textvariable=self._vars["formats"], width=50).pack(anchor="w", pady=(0, 4))
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── Sound ──
        self._section(inner, "Sound Notifications")
        sound_row = tk.Frame(inner, bg=C["bg"])
        sound_row.pack(fill="x", pady=2)
        self._vars["sound_enabled"] = tk.BooleanVar(
            value=bool(self._store.values.get("sound_enabled", True)))
        mk_chk(sound_row, "Enable sounds  (validation.mp3 / exclamation.mp3)",
               self._vars["sound_enabled"], bg=C["bg"]).pack(side="left")
        vol_row = tk.Frame(inner, bg=C["bg"])
        vol_row.pack(fill="x", pady=2)
        mk_label(vol_row, "Volume  (0.0 – 1.0)", fg=C["fg"], width=30, anchor="w").pack(side="left")
        self._vars["sound_volume"] = tk.StringVar(
            value=str(self._store.values.get("sound_volume", 0.8)))
        mk_entry(vol_row, textvariable=self._vars["sound_volume"], width=8).pack(side="left", padx=(6, 0))
        if not _PYGAME_OK:
            mk_label(inner,
                     "pygame not installed — sounds disabled.  Run: pip install pygame",
                     fg=C["warning"], font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── Startup & Debug ──
        self._section(inner, "Startup & Debug")
        for var_name, label_text, attr in [
            ("_auto_start_var", "Auto-start monitoring on launch", "auto_start"),
            ("_debug_var",      "Debug mode  (log every scan cycle)", "debug_mode"),
        ]:
            row = tk.Frame(inner, bg=C["bg"])
            row.pack(fill="x", pady=2)
            bv = tk.BooleanVar(value=getattr(self._store, attr))
            setattr(self, var_name, bv)
            mk_chk(row, label_text, bv, bg=C["bg"]).pack(side="left")
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── Statistics ──
        self._section(inner, "Statistics")
        for label, key, default in _STATS_ROWS:
            self._num_row(inner, label, key, default, self._store.stats_config)
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── Shared Profiles ──
        self._section(inner, "Shared Profiles")
        mk_label(inner,
                 "Create named identities (username + avatar) to assign to shared webhooks.",
                 fg=C["fg2"], font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        sp_count_row = tk.Frame(inner, bg=C["bg"])
        sp_count_row.pack(fill="x", pady=(0, 2))
        n_sp = len(self._store.shared_profiles)
        self._sp_count_lbl = mk_label(sp_count_row,
            f"{n_sp} profile{'s' if n_sp != 1 else ''} configured",
            fg=C["accent2"] if n_sp else C["fg2"], font=("Segoe UI", 8))
        self._sp_count_lbl.pack(side="left")
        mk_btn(inner, "Manage Shared Profiles", self._open_shared_profiles,
               color=C["accent"], fg=C["bg"]).pack(anchor="w", pady=(0, 2))
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ─── Theme Folder ──────
        self._section(inner, "Theme Folder")

        tf_desc = mk_label(
            inner,
            "Point to a folder of .wistheme / .json files to load them as presets.",
            fg=C["fg2"], font=("Segoe UI", 8),
        )
        tf_desc.pack(anchor="w", pady=(0, 4))

        tf_row = tk.Frame(inner, bg=C["bg"])
        tf_row.pack(fill="x", pady=(0, 2))

        self._vars["theme_folder"] = tk.StringVar(
            value=self._store.values.get("theme_folder", ""))
        tf_entry = mk_entry(tf_row, textvariable=self._vars["theme_folder"], width=2)
        tf_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        mk_btn(tf_row, "Browse…", self._browse_theme_folder,
               color=C["bg3"], fg=C["fg"]).pack(side="left", padx=(0, 4))
        mk_btn(tf_row, "Clear", self._clear_theme_folder,
               color=C["bg3"], fg=C["danger"]).pack(side="left")

        tf_action_row = tk.Frame(inner, bg=C["bg"])
        tf_action_row.pack(fill="x", pady=(4, 0))

        mk_btn(tf_action_row, "Reload Folder Themes", self._reload_folder_themes,
               color=C["accent"], fg=C["bg"]).pack(side="left")

        # Status label — updated after scanning
        self._tf_status = mk_label(tf_action_row, "", fg=C["fg2"],
                                   font=("Segoe UI", 8))
        self._tf_status.pack(side="left", padx=10)

        # Load folder themes from the saved path immediately (silently)
        saved_folder = self._store.values.get("theme_folder", "")
        if saved_folder and os.path.isdir(saved_folder):
            self._folder_themes = load_themes_from_folder(saved_folder)

        tk.Frame(inner, bg=C["bg"], height=6).pack()
        # ══ end Theme Folder ══════════════════════════════════════════════════

        # ── Theme Presets ──
        self._section(inner, "Theme Presets")
        all_presets = self._all_preset_names()
        self._preset_var = tk.StringVar(value=all_presets[0] if all_presets else "")
        preset_row = tk.Frame(inner, bg=C["bg"])
        preset_row.pack(fill="x", pady=(0, 4))
        self._preset_menu = tk.OptionMenu(preset_row, self._preset_var, *(all_presets or ["—"]))
        self._preset_menu.config(
            bg=C["bg3"], fg=C["fg"], activebackground=C["bg2"],
            activeforeground=C["accent"], highlightthickness=0,
            relief="flat", font=("Segoe UI", 9), bd=0, anchor="w")
        self._preset_menu["menu"].config(bg=C["bg3"], fg=C["fg"], font=("Segoe UI", 9))
        self._preset_menu.pack(side="left", fill="x", expand=True, padx=(0, 6))
        mk_btn(preset_row, "Apply",         self._apply_preset,
               color=C["accent"], fg=C["bg"]).pack(side="left", padx=(0, 4))
        mk_btn(preset_row, "Delete Custom", self._delete_preset,
               color=C["bg3"], fg=C["danger"]).pack(side="left")
        save_preset_row = tk.Frame(inner, bg=C["bg"])
        save_preset_row.pack(fill="x", pady=(0, 4))
        mk_label(save_preset_row, "Save as:", fg=C["fg2"], width=8, anchor="w").pack(side="left")
        self._new_preset_var = tk.StringVar()
        mk_entry(save_preset_row, textvariable=self._new_preset_var, width=22).pack(side="left", padx=(0, 6))
        mk_btn(save_preset_row, "Save Preset", self._save_preset,
               color=C["accent2"], fg=C["bg"]).pack(side="left")
        ie_row = tk.Frame(inner, bg=C["bg"])
        ie_row.pack(fill="x", pady=(0, 2))
        mk_btn(ie_row, "Export Theme", self._export_theme,
               color=C["bg3"], fg=C["fg"]).pack(side="left", padx=(0, 6))
        mk_btn(ie_row, "Import Theme", self._import_theme,
               color=C["bg3"], fg=C["fg"]).pack(side="left")
        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── Color Editor ──
        self._section(inner, "Color Editor  (hex codes)")
        grid = tk.Frame(inner, bg=C["bg"])
        grid.pack(fill="x", pady=4)
        for i, (key, lbl_text) in enumerate(_COLOR_DEFS):
            row_frame = tk.Frame(grid, bg=C["bg"])
            row_frame.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 16), pady=3)
            mk_label(row_frame, lbl_text, fg=C["fg2"],
                     font=("Segoe UI", 8), width=16, anchor="w").pack(side="left")
            self._vars[key] = tk.StringVar(
                value=self._store.values.get(key, DEFAULTS.get(key, "")))
            mk_entry(row_frame, textvariable=self._vars[key], width=9).pack(side="left")
            swatch = tk.Frame(row_frame, width=18, height=18,
                              bg=self._vars[key].get() or C["bg3"], relief="flat", bd=1)
            swatch.pack(side="left", padx=(4, 0))
            swatch.pack_propagate(False)
            self._swatch_refs[key] = swatch
            self._vars[key].trace_add("write", lambda *_, k=key: self._update_swatch(k))

        tk.Frame(inner, bg=C["bg"], height=4).pack()
        mk_btn(inner, "Reset to defaults", self._reset_colors,
               color=C["bg3"], fg=C["fg2"]).pack(anchor="w", pady=4)
        self.add_footer_buttons(self._save)

        # Populate status label after build
        self._update_tf_status()

    # ── Shared Profiles ──────────────────────────────────────────────────────

    def _open_shared_profiles(self):
        def on_save(profiles):
            self._store.shared_profiles = profiles
            n = len(profiles)
            self._sp_count_lbl.config(
                text=f"{n} profile{'s' if n != 1 else ''} configured",
                fg=C["accent2"] if n else C["fg2"])
        SharedProfileManager(self, self._store.shared_profiles, on_save)

    # ── Theme Folder actions ─────────────────────────────────────────────────

    def _browse_theme_folder(self):
        folder = filedialog.askdirectory(parent=self, title="Select Theme Folder")
        if folder:
            self._vars["theme_folder"].set(folder)
            self._reload_folder_themes()

    def _clear_theme_folder(self):
        self._vars["theme_folder"].set("")
        self._folder_themes.clear()
        self._rebuild_preset_menu()
        self._update_tf_status()

    def _reload_folder_themes(self):
        folder = self._vars["theme_folder"].get().strip()
        if not folder:
            messagebox.showwarning("No Folder", "No theme folder is set.", parent=self)
            return
        if not os.path.isdir(folder):
            messagebox.showwarning("Not Found",
                                   f"Folder not found:\n{folder}", parent=self)
            return
        self._folder_themes = load_themes_from_folder(folder)
        self._rebuild_preset_menu()
        self._update_tf_status()
        n = len(self._folder_themes)
        if n:
            messagebox.showinfo("Loaded",
                                f"Loaded {n} theme{'s' if n != 1 else ''} from folder.",
                                parent=self)
        else:
            messagebox.showwarning("None Found",
                                   "No valid .wistheme / .json themes found in that folder.",
                                   parent=self)

    def _update_tf_status(self):
        folder = self._vars["theme_folder"].get().strip() if "theme_folder" in self._vars else ""
        if not folder:
            self._tf_status.config(text="No folder selected", fg=C["fg2"])
        elif not os.path.isdir(folder):
            self._tf_status.config(text="⚠ Folder not found", fg=C["warning"])
        else:
            n = len(self._folder_themes)
            label = f"{n} theme{'s' if n != 1 else ''} loaded  ·  {os.path.basename(folder)}"
            self._tf_status.config(text=label, fg=C["accent2"])

    # ── Section / section helpers ────────────────────────────────────────────

    def _section(self, parent, text):
        mk_label(parent, text, fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=(2, 6))

    def _num_row(self, parent, label_text: str, key: str, default, source: dict):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=2)
        mk_label(row, label_text, fg=C["fg"], width=30, anchor="w").pack(side="left")
        self._vars[key] = tk.StringVar(value=str(source.get(key, default)))
        mk_entry(row, textvariable=self._vars[key], width=8).pack(side="left", padx=(6, 0))

    # ── Color helpers ────────────────────────────────────────────────────────

    def _reset_colors(self):
        for k in COLOR_KEYS:
            if k in self._vars:
                self._vars[k].set(DEFAULTS[k])

    def _update_swatch(self, key):
        val = self._vars[key].get().strip()
        sw  = self._swatch_refs.get(key)
        if sw and len(val) == 7 and val.startswith("#"):
            try:
                sw.config(bg=val)
            except Exception:
                pass

    def _current_colors(self) -> dict:
        return {k: self._vars[k].get().strip() for k in COLOR_KEYS if k in self._vars}

    def _load_colors(self, colors: dict):
        for k in COLOR_KEYS:
            if k in colors and k in self._vars:
                self._vars[k].set(colors[k])
                self._update_swatch(k)

    # ── Preset actions ───────────────────────────────────────────────────────

    def _apply_preset(self):
        name   = self._preset_var.get()
        colors = self._lookup_preset(name)
        if colors:
            self._load_colors(colors)
        else:
            messagebox.showwarning("Not Found", f"Preset '{name}' not found.", parent=self)

    def _save_preset(self):
        name = self._new_preset_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Enter a name for the preset.", parent=self); return
        if name in THEME_PRESETS:
            messagebox.showwarning("Reserved", f"{name!r} is a built-in preset.", parent=self); return
        self._custom_themes[name] = self._current_colors()
        self._rebuild_preset_menu()
        self._preset_var.set(name)
        self._new_preset_var.set("")
        messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=self)

    def _delete_preset(self):
        name = self._preset_var.get()
        if name in THEME_PRESETS:
            messagebox.showwarning("Built-in", "Cannot delete built-in presets.", parent=self); return
        if name in self._folder_themes:
            messagebox.showwarning("Folder Theme",
                                   f"'{name}' comes from the theme folder and cannot be deleted here.\n"
                                   "Remove or edit the file in the folder instead.", parent=self); return
        if name not in self._custom_themes:
            messagebox.showwarning("Not Found", f"'{name}' is not a custom preset.", parent=self); return
        if messagebox.askyesno("Delete", f"Delete preset '{name}'?", parent=self):
            del self._custom_themes[name]
            self._rebuild_preset_menu()

    def _rebuild_preset_menu(self):
        all_names = self._all_preset_names()
        menu = self._preset_menu["menu"]
        menu.delete(0, "end")
        for n in all_names:
            menu.add_command(label=n, command=lambda v=n: self._preset_var.set(v))
        if all_names and self._preset_var.get() not in all_names:
            self._preset_var.set(all_names[0])

    # ── Import / Export ──────────────────────────────────────────────────────

    def _export_theme(self):
        colors = self._current_colors()
        name   = self._preset_var.get() or "my_theme"
        path   = filedialog.asksaveasfilename(
            parent=self, title="Export Theme",
            defaultextension=".wistheme", initialfile=name.replace(" ", "_"),
            filetypes=[("WIS Theme", "*.wistheme"), ("JSON", "*.json"), ("All", "*.*")])
        if not path: return
        try:
            with open(path, "w") as f:
                json.dump({"wis_theme": True, "name": name, "colors": colors}, f, indent=2)
            messagebox.showinfo("Exported", f"Theme exported to:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e), parent=self)

    def _import_theme(self):
        path = filedialog.askopenfilename(
            parent=self, title="Import Theme",
            filetypes=[("WIS Theme", "*.wistheme"), ("JSON", "*.json"), ("All", "*.*")])
        if not path: return
        try:
            with open(path) as f:
                data = json.load(f)
            if not data.get("wis_theme"):
                messagebox.showwarning("Invalid File", "Not a WIS theme.", parent=self); return
            valid = {k: v for k, v in data.get("colors", {}).items()
                     if k in COLOR_KEYS and isinstance(v, str)
                     and v.startswith("#") and len(v) == 7}
            if not valid:
                messagebox.showwarning("Empty", "No valid colors found.", parent=self); return
            self._load_colors(valid)
            imported_name = data.get("name", os.path.splitext(os.path.basename(path))[0])
            if messagebox.askyesno("Save Preset?",
                                   f"Save as preset '{imported_name}'?", parent=self):
                if imported_name not in THEME_PRESETS:
                    self._custom_themes[imported_name] = valid
                    self._rebuild_preset_menu()
                    self._preset_var.set(imported_name)
        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self)

    # ── Save ─────────────────────────────────────────────────────────────────

    def _save(self):
        # Behaviour values
        for key in ("scan_rate", "send_timeout", "file_delay"):
            try:
                self._store.values[key] = float(self._vars[key].get())
            except ValueError:
                self._store.values[key] = DEFAULTS[key]
        self._store.values["formats"]       = self._vars["formats"].get().strip()
        self._store.values["sound_enabled"] = bool(self._vars["sound_enabled"].get())
        try:
            vol = float(self._vars["sound_volume"].get())
            self._store.values["sound_volume"] = max(0.0, min(1.0, vol))
        except ValueError:
            self._store.values["sound_volume"] = DEFAULTS["sound_volume"]

        # Theme folder — persist the path
        self._store.values["theme_folder"] = self._vars["theme_folder"].get().strip()

        # Color values
        self._store.values.update({
            k: (v if v.startswith("#") and len(v) == 7 else DEFAULTS.get(k))
            for k in COLOR_KEYS
            if (v := self._vars[k].get().strip())
        })

        # Stats config
        for _, key, default in _STATS_ROWS:
            try:
                self._store.stats_config[key] = int(float(self._vars[key].get()))
            except (ValueError, KeyError):
                self._store.stats_config[key] = default

        # Startup / debug
        self._store.auto_start    = self._auto_start_var.get()
        self._store.debug_mode    = self._debug_var.get()
        self._store.custom_themes = self._custom_themes
        # shared_profiles already mutated in-place by SharedProfileManager

        try:    self._on_save(self._store)
        finally: self.destroy()


# ─────────────────────────────────────────────
#  CHART WIDGETS
# ─────────────────────────────────────────────

class BarChart(tk.Canvas, IChartWidget):
    def __init__(self, parent, data, color=None, bg=None, **kw):
        super().__init__(parent, bg=bg or C["bg2"], highlightthickness=0, **kw)
        self._data  = data
        self._color = color or C["accent"]
        self.bind("<Configure>", lambda e: self._draw())

    def update_data(self, data: list):
        self._data = data
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10 or not self._data:
            if not self._data:
                self.create_text(w // 2, h // 2, text="No data yet",
                                 fill=C["fg2"], font=("Segoe UI", 9))
            return
        pad_l, pad_r, pad_t, pad_b = 48, 16, 28, 52
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b
        max_val = max((v for _, v in self._data), default=1) or 1
        n     = len(self._data)
        gap   = 6
        bar_w = max(6, min(60, (chart_w - gap * (n + 1)) // n))
        self.create_line(pad_l, pad_t, pad_l, pad_t + chart_h, fill=C["border"], width=1)
        self.create_line(pad_l, pad_t + chart_h, pad_l + chart_w, pad_t + chart_h,
                         fill=C["border"], width=1)
        for i in range(5):
            y  = pad_t + chart_h - int(chart_h * i / 4)
            yv = max_val * i / 4
            self.create_line(pad_l - 3, y, pad_l + chart_w, y,
                             fill=C["border"], dash=(2, 4), width=1)
            self.create_text(pad_l - 5, y, text=str(round(yv)),
                             fill=C["fg2"], font=("Segoe UI", 7), anchor="e")
        total_w = n * bar_w + (n + 1) * gap
        start_x = pad_l + max(0, (chart_w - total_w) // 2) + gap
        for i, (lbl, val) in enumerate(self._data):
            x0 = start_x + i * (bar_w + gap)
            x1 = x0 + bar_w
            bh = int(chart_h * val / max_val) if max_val else 0
            y0 = pad_t + chart_h - bh
            y1 = pad_t + chart_h
            self.create_rectangle(x0+2, y0+2, x1+2, y1+2, fill=C["bg"], outline="")
            self.create_rectangle(x0, y0, x1, y1, fill=self._color, outline="", width=0)
            if bh > 14:
                self.create_text((x0+x1)//2, y0+6, text=str(val),
                                 fill=C["bg"], font=("Segoe UI", 7, "bold"), anchor="n")
            else:
                self.create_text((x0+x1)//2, y0-6, text=str(val),
                                 fill=C["fg"], font=("Segoe UI", 7), anchor="s")
            short = lbl if len(lbl) <= 9 else lbl[:8] + "…"
            self.create_text((x0+x1)//2, y1 + 10, text=short,
                             fill=C["fg2"], font=("Segoe UI", 7), anchor="n", width=bar_w + gap)


class PieChart(tk.Canvas, IChartWidget):
    PALETTE = ["#4f8ef7","#2ecc8f","#f0a500","#e05252",
               "#a78bfa","#fb923c","#34d399","#f472b6"]

    def __init__(self, parent, data, bg=None, **kw):
        super().__init__(parent, bg=bg or C["bg2"], highlightthickness=0, **kw)
        self._data = data
        self.bind("<Configure>", lambda e: self._draw())

    def update_data(self, data: list):
        self._data = data
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        total = sum(v for _, v in self._data if v > 0) if self._data else 0
        if total == 0:
            self.create_text(w // 2, h // 2, text="No data yet",
                             fill=C["fg2"], font=("Segoe UI", 9))
            return
        legend_h = min(len(self._data) * 16 + 4, 100)
        pie_area = h - 24 - legend_h - 8
        r  = min(w // 2 - 30, pie_area // 2 - 8, 80)
        cx = w // 2
        cy = 24 + pie_area // 2
        start = -90.0
        for i, (_, val) in enumerate(self._data):
            if val <= 0:
                continue
            extent = 360.0 * val / total
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                            start=start, extent=extent,
                            fill=self.PALETTE[i % len(self.PALETTE)],
                            outline=C["bg2"], width=2)
            start += extent
        ir = int(r * 0.55)
        self.create_oval(cx-ir, cy-ir, cx+ir, cy+ir, fill=C["bg2"], outline="")
        self.create_text(cx, cy,    text=str(total), fill=C["fg"],  font=("Segoe UI", 11, "bold"))
        self.create_text(cx, cy+14, text="total",    fill=C["fg2"], font=("Segoe UI", 7))
        ly = cy + r + 12
        half_w = w // 2
        for i, (lbl, val) in enumerate(self._data):
            pct   = f"{100 * val / total:.0f}%"
            lx    = 16 + (i % 2) * half_w
            lyi   = ly + (i // 2) * 16
            color = self.PALETTE[i % len(self.PALETTE)]
            self.create_rectangle(lx, lyi+2, lx+10, lyi+12, fill=color, outline="")
            short = lbl if len(lbl) <= 14 else lbl[:13] + "…"
            self.create_text(lx+14, lyi+7, text=f"{short}  {val} ({pct})",
                             fill=C["fg2"], font=("Segoe UI", 7), anchor="w")


# ─────────────────────────────────────────────
#  STATS WINDOW
# ─────────────────────────────────────────────

class StatsWindow(BasePopup):
    def __init__(self, parent, stats: StatisticsStore):
        super().__init__(parent, "Statistics", "Send history & analytics", size="860x640")
        self.resizable(True, True)
        self._stats = stats
        self._build()

    def _build(self):
        b  = self.body
        nb = ttk.Notebook(b)
        nb.pack(fill="both", expand=True)
        style = ttk.Style()
        style.configure("TNotebook",     background=C["bg"],  borderwidth=0)
        style.configure("TNotebook.Tab", background=C["bg3"], foreground=C["fg2"],
                        padding=[10, 5], font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", C["bg2"])],
                  foreground=[("selected", C["accent"])])

        tab_names = ["Overview", "Webhooks", "Folders", "Errors", "Recent"]
        self._tabs = {n: tk.Frame(nb, bg=C["bg"]) for n in tab_names}
        for name, frame in self._tabs.items():
            nb.add(frame, text=f"  {name}  ")

        self._build_overview()
        self._build_webhooks()
        self._build_folders()
        self._build_errors()
        self._build_recent()

        mk_btn(self._footer_frame, "Close",           self.destroy,
               color=C["bg3"],    fg=C["fg2"]).pack(side="right")
        mk_btn(self._footer_frame, "Clear All Stats", self._clear_stats,
               color=C["danger"], fg="white").pack(side="left")
        mk_btn(self._footer_frame, "Refresh",       self._refresh_all,
               color=C["bg3"],    fg=C["accent"]).pack(side="left", padx=(0, 6))

    def _repopulate(self, panel: TreePanel, rows):
        panel.clear()
        for i, row in enumerate(rows):
            panel.insert(i, row if isinstance(row, tuple) else (row,))

    def _build_overview(self):
        p = self._tabs["Overview"]
        summary = tk.Frame(p, bg=C["bg2"], pady=8)
        summary.pack(fill="x", padx=8, pady=(8, 4))
        sends  = self._stats.sends
        total  = len(sends)
        ok     = sum(1 for s in sends if s.get("ok"))
        fail   = total - ok
        rate   = f"{100 * ok / total:.1f}%" if total else "—"
        for val, lbl, col in [
            (str(total), "Total Sent",   C["accent"]),
            (str(ok),    "Successful",   C["accent2"]),
            (str(fail),  "Failed",       C["danger"]),
            (rate,       "Success Rate", C["warning"]),
            (str(len(self._stats.errors)), "Errors", C["fg2"]),
        ]:
            f = tk.Frame(summary, bg=C["bg2"])
            f.pack(side="left", padx=18)
            tk.Label(f, text=val, bg=C["bg2"], fg=col,  font=("Segoe UI", 18, "bold")).pack()
            tk.Label(f, text=lbl, bg=C["bg2"], fg=C["fg2"], font=("Segoe UI", 8)).pack()

        chart_frame = tk.Frame(p, bg=C["bg"])
        chart_frame.pack(fill="both", expand=True, padx=8, pady=4)
        mk_label(chart_frame, "Images Sent — Last 12 Months",
                 fg=C["fg2"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 2))
        n = self._stats._config.get("months", 12)
        self._monthly_chart = BarChart(chart_frame, data=self._stats.months_data(n),
                                       color=C["accent"], bg=C["bg2"], height=220)
        self._monthly_chart.pack(fill="both", expand=True)

        ext_row = tk.Frame(p, bg=C["bg"])
        ext_row.pack(fill="x", padx=8, pady=(4, 8))
        mk_label(ext_row, "By File Type", fg=C["fg2"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        self._ext_pie = PieChart(ext_row, data=self._stats.ext_data(),
                                 bg=C["bg2"], height=150)
        self._ext_pie.pack(fill="x")

    def _build_webhooks(self):
        p = self._tabs["Webhooks"]
        mk_label(p, "Images Sent per Webhook", fg=C["fg2"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self._webhook_bar = BarChart(p, data=self._stats.webhook_data(),
                                     color=C["accent2"], bg=C["bg2"], height=220)
        self._webhook_bar.pack(fill="x", padx=8, pady=4)
        mk_label(p, "Webhook Breakdown", fg=C["fg2"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self._webhook_tree = TreePanel(p,
            columns=("name", "sent", "failed", "rate"),
            headings=("Webhook", "Sent", "Failed", "Success Rate"),
            widths=(220, 80, 80, 120), height=8)
        self._webhook_tree.pack(fill="both", expand=True, padx=8, pady=4)
        self._repopulate(self._webhook_tree, self._stats.webhook_table())

    def _build_folders(self):
        p = self._tabs["Folders"]
        mk_label(p, "Images Sent per Folder", fg=C["fg2"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self._folder_bar = BarChart(p,
            data=[(os.path.basename(l) or l, v) for l, v in self._stats.folder_data()],
            color=C["warning"], bg=C["bg2"], height=200)
        self._folder_bar.pack(fill="x", padx=8, pady=4)
        mk_label(p, "Folder Detail", fg=C["fg2"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self._folder_tree = TreePanel(p,
            columns=("path", "sent"),
            headings=("Folder Path", "Images Sent"),
            widths=(480, 100), height=8)
        self._folder_tree.pack(fill="both", expand=True, padx=8, pady=4)
        self._repopulate(self._folder_tree, self._stats.folder_data())

    def _build_errors(self):
        p = self._tabs["Errors"]
        mk_label(p, "Error Breakdown", fg=C["fg2"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        err_row = tk.Frame(p, bg=C["bg"])
        err_row.pack(fill="x", padx=8, pady=4)
        self._error_pie = PieChart(err_row, data=self._stats.error_type_data(),
                                   bg=C["bg2"], height=200)
        self._error_pie.pack(side="left", fill="both", expand=True)
        self._error_bar = BarChart(err_row, data=self._stats.error_type_data(),
                                   color=C["danger"], bg=C["bg2"], height=200)
        self._error_bar.pack(side="left", fill="both", expand=True)
        mk_label(p, "Recent Errors", fg=C["fg2"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self._error_tree = TreePanel(p,
            columns=("time", "type", "file", "webhook", "detail"),
            headings=("Time", "Type", "File", "Webhook", "Detail"),
            widths=(80, 100, 160, 120, 220), height=8)
        self._error_tree.pack(fill="both", expand=True, padx=8, pady=4)
        errors = list(reversed(self._stats.errors[-200:]))
        self._repopulate(self._error_tree, [
            (e.get("time",""), e.get("type",""), e.get("file",""),
             e.get("webhook",""), e.get("detail",""))
            for e in errors
        ])

    def _build_recent(self):
        p    = self._tabs["Recent"]
        hdr  = tk.Frame(p, bg=C["bg"])
        hdr.pack(fill="x", padx=8, pady=(10, 2))
        ok   = sum(1 for s in self._stats.sends if s.get("ok"))
        fail = len(self._stats.sends) - ok
        mk_label(hdr, "Recent Sends (latest 500)", fg=C["fg2"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        mk_label(hdr, f"  {ok} ok  |  {fail} failed", fg=C["fg2"],
                 font=("Segoe UI", 8)).pack(side="left", padx=8)
        self._recent_tree = TreePanel(p,
            columns=("time", "file", "webhook", "folder", "ext", "status"),
            headings=("Time", "File", "Webhook", "Folder", "Ext", "Status"),
            widths=(90, 200, 120, 140, 50, 70), height=22)
        self._recent_tree.pack(fill="both", expand=True, padx=8, pady=4)
        self._populate_recent()

    def _populate_recent(self):
        recent = list(reversed(self._stats.sends[-500:]))
        self._repopulate(self._recent_tree, [
            (s.get("time",""), s.get("file",""), s.get("webhook",""),
             os.path.basename(s.get("folder","")) or s.get("folder",""),
             s.get("ext",""), "✓ OK" if s.get("ok") else "✗ Fail")
            for s in recent
        ])

    def _refresh_all(self):
        n = self._stats._config.get("months", 12)
        self._monthly_chart.update_data(self._stats.months_data(n))
        self._ext_pie.update_data(self._stats.ext_data())
        self._webhook_bar.update_data(self._stats.webhook_data())
        self._repopulate(self._webhook_tree, self._stats.webhook_table())
        self._folder_bar.update_data(
            [(os.path.basename(l) or l, v) for l, v in self._stats.folder_data()])
        self._repopulate(self._folder_tree, self._stats.folder_data())
        self._error_pie.update_data(self._stats.error_type_data())
        self._error_bar.update_data(self._stats.error_type_data())
        errors = list(reversed(self._stats.errors[-200:]))
        self._repopulate(self._error_tree, [
            (e.get("time",""), e.get("type",""), e.get("file",""),
             e.get("webhook",""), e.get("detail",""))
            for e in errors
        ])
        self._populate_recent()

    def _clear_stats(self):
        if messagebox.askyesno("Clear Stats",
                               "Delete ALL statistics history? This cannot be undone.",
                               parent=self):
            self._stats.clear()
            self._refresh_all()


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────

class WIS:
    def __init__(self, root: tk.Tk,
                 sender: ISender,
                 audio:  IAudioPlayer,
                 store:  SettingsStore,
                 stats:  StatisticsStore):
        self.root   = root
        self._store = store
        self._stats = stats

        self.root.title("WIS — Webhook Image Sender")
        self.root.minsize(720, 540)
        self.root.geometry("820x640")

        self._auto_start_var = tk.BooleanVar(value=store.auto_start)
        self._debug_var      = tk.BooleanVar(value=store.debug_mode)

        self._monitoring = MonitoringService(
            sender=sender, audio=audio, stats=stats,
            on_log=self._log_from_thread,
            on_counters=self._update_counters,
        )

        C.update({k: store.values[k] for k in DEFAULTS if k in store.values})
        self.root.configure(bg=C["bg"])
        apply_treeview_style()
        self._build_ui()

        if store.auto_start and self._ready():
            self.root.after(1000, self.start_monitoring)

    def _build_ui(self):
        tb = tk.Frame(self.root, bg=C["bg2"])
        tb.pack(fill="x", side="top")
        mk_label(tb, "WIS", fg=C["accent"], bg=C["bg2"],
                 font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=8)
        mk_label(tb, "Webhook Image Sender", fg=C["fg2"], bg=C["bg2"],
                 font=("Segoe UI", 10)).pack(side="left")
        self._status_pill = mk_label(tb, "  IDLE  ", fg=C["fg2"], bg=C["bg3"],
                                     font=("Segoe UI", 8, "bold"))
        self._status_pill.pack(side="right", padx=16, pady=8, ipadx=6, ipady=3)
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x", side="top")

        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=C["bg"], width=270)
        left.pack(side="left", fill="y", padx=14, pady=12)
        left.pack_propagate(False)
        self._build_left(left)

        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(0, 14), pady=12)
        self._build_right(right)

    def _build_left(self, p):
        mk_section(p, "MONITORED FOLDERS")
        self._folder_lbl = tk.Label(p, text=self._folder_summary(),
                                    bg=C["bg2"], fg=C["fg"], font=("Segoe UI", 9),
                                    wraplength=250, justify="left", padx=8, pady=6, anchor="nw")
        self._folder_lbl.pack(fill="x", pady=(0, 4))
        mk_btn(p, "Manage Folders",  self._open_folders,  color=C["bg3"], fg=C["accent"]).pack(fill="x", pady=2)
        tk.Frame(p, bg=C["bg"], height=10).pack()
        mk_section(p, "WEBHOOKS")
        self._webhook_lbl = tk.Label(p, text=self._webhook_summary(),
                                     bg=C["bg2"], fg=C["fg"], font=("Segoe UI", 9),
                                     wraplength=250, justify="left", padx=8, pady=6, anchor="nw")
        self._webhook_lbl.pack(fill="x", pady=(0, 4))
        mk_btn(p, "Manage Webhooks", self._open_webhooks, color=C["bg3"], fg=C["accent"]).pack(fill="x", pady=2)
        tk.Frame(p, bg=C["bg"], height=10).pack()
        mk_btn(p, "Settings",   self._open_settings, color=C["bg3"], fg=C["fg"]).pack(fill="x", pady=2)
        mk_btn(p, "Statistics", self._open_stats,    color=C["bg3"], fg=C["accent"]).pack(fill="x", pady=2)
        tk.Frame(p, bg=C["bg"], height=8).pack()
        self._start_btn = mk_btn(p, "Start Monitoring", self.start_monitoring,
                                  color=C["accent2"], fg=C["bg"])
        self._start_btn.pack(fill="x", pady=3)
        self._stop_btn = mk_btn(p, "Stop Monitoring", self.stop_monitoring,
                                 color=C["danger"], fg="white")
        self._stop_btn.pack(fill="x", pady=3)
        self._stop_btn.config(state="disabled")

    def _build_right(self, p):
        hdr = tk.Frame(p, bg=C["bg"])
        hdr.pack(fill="x", pady=(0, 6))
        mk_label(hdr, "ACTIVITY LOG", fg=C["fg2"], font=("Segoe UI", 7, "bold")).pack(side="left")
        mk_btn(hdr, "Clear", self.clear_log, color=C["bg3"], fg=C["fg2"]).pack(side="right")

        stats_bar = tk.Frame(p, bg=C["bg2"], pady=6)
        stats_bar.pack(fill="x", pady=(0, 6))
        self._s_sent  = self._pill(stats_bar, "0", "Sent")
        self._s_fail  = self._pill(stats_bar, "0", "Failed")
        self._s_hooks = self._pill(stats_bar, "0", "Webhooks")
        self._s_dirs  = self._pill(stats_bar, "0", "Folders")
        self._refresh_pill_stats()

        log_wrap = tk.Frame(p, bg=C["bg3"],
                            highlightthickness=1, highlightbackground=C["border"])
        log_wrap.pack(fill="both", expand=True)
        self._log_box = tk.Text(log_wrap, bg=C["bg3"], fg=C["fg"],
                                insertbackground=C["accent"], relief="flat", bd=0,
                                font=("Consolas", 9), wrap="word", state="disabled")
        self._log_box.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(log_wrap, orient="vertical", command=self._log_box.yview)
        sb.pack(side="right", fill="y")
        self._log_box.configure(yscrollcommand=sb.set)
        for tag, fg in [("ok",  C["accent2"]), ("err",   C["danger"]),
                         ("warn", C["warning"]), ("info",  C["accent"]),
                         ("debug", C["fg2"]),   ("ts",    C["fg2"])]:
            self._log_box.tag_config(tag, foreground=fg)

    def _pill(self, parent, value, label):
        f = tk.Frame(parent, bg=C["bg2"])
        f.pack(side="left", padx=14)
        v = mk_label(f, value, fg=C["accent"], bg=C["bg2"], font=("Segoe UI", 16, "bold"))
        v.pack()
        mk_label(f, label, fg=C["fg2"], bg=C["bg2"], font=("Segoe UI", 8)).pack()
        return v

    def _summary(self, items: list, none_msg: str, all_disabled_msg: str,
                 label_fn: Callable) -> str:
        enabled = [x for x in items if x.get("enabled", True)]
        if not items:   return none_msg
        if not enabled: return all_disabled_msg
        lines = [label_fn(x) for x in enabled[:4]]
        if len(enabled) > 4:
            lines.append(f"  +{len(enabled) - 4} more")
        return "\n".join(lines)

    def _folder_summary(self) -> str:
        return self._summary(
            self._store.folders,
            "No folders configured", "All folders disabled",
            lambda f: f"• {os.path.basename(f['path']) or f['path']}"
                      + (" (recursive)" if f.get("recursive") else ""),
        )

    def _webhook_summary(self) -> str:
        return self._summary(
            self._store.webhooks,
            "No webhooks configured", "All webhooks disabled",
            lambda w: f"• {w.get('name', 'Unnamed')}",
        )

    def _refresh_pill_stats(self):
        self._s_hooks.config(
            text=str(sum(1 for w in self._store.webhooks if w.get("enabled", True))))
        self._s_dirs.config(
            text=str(sum(1 for f in self._store.folders  if f.get("enabled", True))))

    def _open_folders(self):
        def on_save(v):
            self._store.folders = v
            self._store.save()
            self._folder_lbl.config(text=self._folder_summary())
            self._refresh_pill_stats()
            self.log("Folder list updated", "info")
        FolderManager(self.root, self._store.folders, on_save)

    def _open_webhooks(self):
        def on_save(v):
            self._store.webhooks = v
            self._store.save()
            self._webhook_lbl.config(text=self._webhook_summary())
            self._refresh_pill_stats()
            self.log("Webhook list updated", "info")
        WebhookManager(self.root, self._store.webhooks, self._store.shared_profiles, on_save)

    def _open_settings(self):
        def on_save(updated_store: SettingsStore):
            C.update(updated_store.values)
            apply_treeview_style()
            updated_store.save()
            self.log("Settings saved — restart to fully apply color changes", "warn")
        SettingsManager(self.root, self._store, on_save)

    def _open_stats(self):
        StatsWindow(self.root, self._stats)

    def log(self, message: str, kind: str = "info"):
        ts   = time.strftime("%H:%M:%S")
        icon = _LOG_ICONS.get(kind, "·")
        self._log_box.config(state="normal")
        self._log_box.insert("end", f"[{ts}] ", "ts")
        self._log_box.insert("end", f"{icon} {message}\n", kind)
        self._log_box.see("end")
        self._log_box.config(state="disabled")

    def _log_from_thread(self, message: str, kind: str):
        self.root.after(0, self.log, message, kind)

    def _update_counters(self, sent: int, fail: int):
        self.root.after(0, lambda: (
            self._s_sent.config(text=str(sent)),
            self._s_fail.config(text=str(fail)),
        ))

    def clear_log(self):
        self._log_box.config(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.config(state="disabled")

    def _ready(self) -> bool:
        return (
            any(f.get("enabled") and os.path.isdir(f.get("path", "")) for f in self._store.folders)
            and any(w.get("enabled") and w.get("url") for w in self._store.webhooks)
        )

    def start_monitoring(self):
        active_webhooks = [w for w in self._store.webhooks
                           if w.get("enabled", True) and w.get("url")]
        if not active_webhooks:
            self.log("No webhooks configured.", "warn"); return

        # Resolve shared profiles into webhook copies
        profile_map = {p["name"]: p for p in self._store.shared_profiles}
        resolved_webhooks = []
        for w in active_webhooks:
            wc = dict(w)
            if w.get("shared_profile_enabled") and w.get("shared_profile"):
                wc["_resolved_profile"] = profile_map.get(w["shared_profile"], {})
            else:
                wc["_resolved_profile"] = {}
            resolved_webhooks.append(wc)

        valid, invalid = [], []
        for f in self._store.folders:
            if not f.get("enabled", True):
                continue
            (valid if os.path.isdir(f.get("path", "")) else invalid).append(f)
        for f in invalid:
            self.log(f"Folder not found, skipping: {f['path']}", "warn")
        if not valid:
            self.log("No valid folders found.", "err"); return

        self._s_sent.config(text="0")
        self._s_fail.config(text="0")
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status_pill.config(text="  MONITORING  ", bg="#1a3320", fg=C["accent2"])

        self._monitoring.start(valid, resolved_webhooks, self._store.values, self._store.debug_mode)
        names = ", ".join(w["name"] for w in resolved_webhooks)
        self.log(f"Started — {len(valid)} folder(s) → {len(resolved_webhooks)} webhook(s): {names}", "ok")

    def stop_monitoring(self):
        self._monitoring.stop()
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._status_pill.config(text="  STOPPED  ", bg="#2a1a1a", fg=C["danger"])
        self.log("Monitoring stopped", "warn")
        Thread(target=self._stats.save, daemon=True).start()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    base  = os.path.dirname(os.path.abspath(__file__))
    store = SettingsStore(os.path.join(base, "wis_settings.json"))
    store.load()
    stats = StatisticsStore(os.path.join(base, "wis_stats.json"), store.stats_config)
    stats.load()
    sender: ISender      = HttpSender()
    audio:  IAudioPlayer = PygameAudioPlayer() if _PYGAME_OK else NullAudioPlayer()
    root = tk.Tk()
    WIS(root, sender=sender, audio=audio, store=store, stats=stats)
    root.mainloop()


if __name__ == "__main__":
    main()
