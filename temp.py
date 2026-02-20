import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import os
import time
import requests
import json
from threading import Thread
import mimetypes

# ─────────────────────────────────────────────

# COLOUR / FONT CONSTANTS  (dark industrial)

# ─────────────────────────────────────────────

BG        = “#0f1117”
BG2       = “#181c26”
BG3       = “#1f2433”
ACCENT    = “#4f8ef7”
ACCENT2   = “#2ecc8f”
DANGER    = “#e05252”
WARNING   = “#f0a500”
FG        = “#d6dce8”
FG2       = “#7a8499”
BORDER    = “#2a3045”
MONO      = (“Consolas”, 9)
SANS      = (“Segoe UI”, 9)
SANS_B    = (“Segoe UI”, 9, “bold”)
SANS_SM   = (“Segoe UI”, 8)
TITLE_F   = (“Segoe UI”, 11, “bold”)

def styled_button(parent, text, command, color=ACCENT, fg=BG, **kw):
btn = tk.Button(
parent, text=text, command=command,
bg=color, fg=fg, activebackground=color,
activeforeground=fg, relief=“flat”, bd=0,
padx=12, pady=5, font=SANS_B, cursor=“hand2”, **kw
)
btn.bind(”<Enter>”, lambda e: btn.config(bg=_lighten(color)))
btn.bind(”<Leave>”, lambda e: btn.config(bg=color))
return btn

def _lighten(hex_color):
“”“Slightly lighten a hex colour for hover.”””
hex_color = hex_color.lstrip(”#”)
r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
r = min(255, r + 25)
g = min(255, g + 25)
b = min(255, b + 25)
return f”#{r:02x}{g:02x}{b:02x}”

def styled_entry(parent, textvariable=None, width=40, show=None):
e = tk.Entry(
parent, textvariable=textvariable, width=width,
bg=BG3, fg=FG, insertbackground=ACCENT,
relief=“flat”, bd=0, font=SANS,
highlightthickness=1, highlightbackground=BORDER,
highlightcolor=ACCENT, show=show or “”
)
return e

def styled_label(parent, text, font=None, fg=FG, **kw):
return tk.Label(parent, text=text, bg=BG, fg=fg, font=font or SANS, **kw)

def separator(parent, pady=6):
f = tk.Frame(parent, bg=BORDER, height=1)
f.pack(fill=“x”, pady=pady)
return f

# ─────────────────────────────────────────────

# SUB-WINDOW: Webhook Manager

# ─────────────────────────────────────────────

class WebhookManagerWindow(tk.Toplevel):
def **init**(self, parent, webhooks: list, on_save):
super().**init**(parent)
self.title(“Webhook Manager”)
self.configure(bg=BG)
self.resizable(False, False)
self.grab_set()

```
    self.webhooks = [dict(w) for w in webhooks]   # local copy
    self.on_save = on_save

    self._build()
    self._refresh_list()
    self.geometry("560x480")

def _build(self):
    header = tk.Frame(self, bg=BG2, pady=10)
    header.pack(fill="x")
    tk.Label(header, text="⚙  Webhook Manager", bg=BG2, fg=ACCENT,
             font=TITLE_F).pack(side="left", padx=14)
    tk.Label(header, text="One detection → sent to ALL enabled webhooks",
             bg=BG2, fg=FG2, font=SANS_SM).pack(side="left", padx=6)

    # List frame
    list_frame = tk.Frame(self, bg=BG, padx=12, pady=8)
    list_frame.pack(fill="both", expand=True)

    cols = ("enabled", "name", "url")
    self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                              height=10, selectmode="browse")
    self.tree.heading("enabled", text="On")
    self.tree.heading("name",    text="Name")
    self.tree.heading("url",     text="URL")
    self.tree.column("enabled", width=38,  anchor="center", stretch=False)
    self.tree.column("name",    width=130, anchor="w")
    self.tree.column("url",     width=320, anchor="w")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background=BG2, foreground=FG,
                    fieldbackground=BG2, rowheight=24, font=SANS)
    style.configure("Treeview.Heading", background=BG3, foreground=ACCENT,
                    font=SANS_B, relief="flat")
    style.map("Treeview", background=[("selected", BG3)],
              foreground=[("selected", ACCENT)])

    self.tree.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
    sb.pack(side="right", fill="y")
    self.tree.configure(yscrollcommand=sb.set)

    # Action buttons for list
    act = tk.Frame(self, bg=BG, padx=12, pady=4)
    act.pack(fill="x")
    styled_button(act, "✎  Edit",   self._edit,   color=BG3, fg=ACCENT).pack(side="left", padx=4)
    styled_button(act, "⏻  Toggle", self._toggle, color=BG3, fg=WARNING).pack(side="left", padx=4)
    styled_button(act, "✕  Remove", self._remove, color=BG3, fg=DANGER).pack(side="left", padx=4)

    separator(self)

    # Add-new section
    add_frame = tk.Frame(self, bg=BG, padx=12, pady=6)
    add_frame.pack(fill="x")
    styled_label(add_frame, "Add / Edit Webhook", font=SANS_B, fg=ACCENT).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

    styled_label(add_frame, "Name:").grid(row=1, column=0, sticky="w", padx=(0,6))
    self._name_var = tk.StringVar()
    styled_entry(add_frame, textvariable=self._name_var, width=22).grid(row=1, column=1, sticky="w")

    styled_label(add_frame, "URL:").grid(row=2, column=0, sticky="w", padx=(0,6), pady=4)
    self._url_var = tk.StringVar()
    styled_entry(add_frame, textvariable=self._url_var, width=48).grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

    self._edit_idx = None  # None = adding new

    btn_row = tk.Frame(add_frame, bg=BG)
    btn_row.grid(row=3, column=0, columnspan=3, sticky="w", pady=4)
    self._add_btn = styled_button(btn_row, "＋  Add", self._add_or_update, color=ACCENT2, fg=BG)
    self._add_btn.pack(side="left")
    styled_button(btn_row, "Clear", self._clear_form, color=BG3, fg=FG2).pack(side="left", padx=8)

    separator(self)

    # Bottom save/cancel
    bottom = tk.Frame(self, bg=BG, padx=12, pady=8)
    bottom.pack(fill="x")
    styled_button(bottom, "✔  Save & Close", self._save, color=ACCENT, fg=BG).pack(side="right", padx=4)
    styled_button(bottom, "Cancel", self.destroy, color=BG3, fg=FG2).pack(side="right")

def _refresh_list(self):
    self.tree.delete(*self.tree.get_children())
    for i, w in enumerate(self.webhooks):
        on = "✔" if w.get("enabled", True) else "—"
        self.tree.insert("", "end", iid=str(i),
                         values=(on, w.get("name", ""), w.get("url", "")))

def _selected_idx(self):
    sel = self.tree.selection()
    if not sel:
        return None
    return int(sel[0])

def _edit(self):
    idx = self._selected_idx()
    if idx is None:
        return
    w = self.webhooks[idx]
    self._name_var.set(w.get("name", ""))
    self._url_var.set(w.get("url", ""))
    self._edit_idx = idx
    self._add_btn.config(text="✔  Update")

def _toggle(self):
    idx = self._selected_idx()
    if idx is None:
        return
    self.webhooks[idx]["enabled"] = not self.webhooks[idx].get("enabled", True)
    self._refresh_list()

def _remove(self):
    idx = self._selected_idx()
    if idx is None:
        return
    name = self.webhooks[idx].get("name", "this webhook")
    if messagebox.askyesno("Remove", f"Remove «{name}»?", parent=self):
        del self.webhooks[idx]
        self._refresh_list()

def _add_or_update(self):
    name = self._name_var.get().strip()
    url  = self._url_var.get().strip()
    if not name:
        messagebox.showwarning("Missing", "Please enter a name.", parent=self)
        return
    if not url.startswith("http"):
        messagebox.showwarning("Missing", "Please enter a valid URL.", parent=self)
        return
    if self._edit_idx is not None:
        self.webhooks[self._edit_idx]["name"] = name
        self.webhooks[self._edit_idx]["url"]  = url
    else:
        self.webhooks.append({"name": name, "url": url, "enabled": True})
    self._clear_form()
    self._refresh_list()

def _clear_form(self):
    self._name_var.set("")
    self._url_var.set("")
    self._edit_idx = None
    self._add_btn.config(text="＋  Add")

def _save(self):
    self.on_save(self.webhooks)
    self.destroy()
```

# ─────────────────────────────────────────────

# SUB-WINDOW: Folder Manager

# ─────────────────────────────────────────────

class FolderManagerWindow(tk.Toplevel):
def **init**(self, parent, folders: list, on_save):
super().**init**(parent)
self.title(“Folder Manager”)
self.configure(bg=BG)
self.resizable(False, False)
self.grab_set()

```
    self.folders = [dict(f) for f in folders]
    self.on_save = on_save

    self._build()
    self._refresh_list()
    self.geometry("580x420")

def _build(self):
    header = tk.Frame(self, bg=BG2, pady=10)
    header.pack(fill="x")
    tk.Label(header, text="📁  Folder Manager", bg=BG2, fg=ACCENT,
             font=TITLE_F).pack(side="left", padx=14)
    tk.Label(header, text="All enabled folders are scanned simultaneously",
             bg=BG2, fg=FG2, font=SANS_SM).pack(side="left", padx=6)

    # List
    list_frame = tk.Frame(self, bg=BG, padx=12, pady=8)
    list_frame.pack(fill="both", expand=True)

    cols = ("enabled", "recursive", "path")
    self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                              height=9, selectmode="browse")
    self.tree.heading("enabled",   text="On")
    self.tree.heading("recursive", text="Recursive")
    self.tree.heading("path",      text="Folder Path")
    self.tree.column("enabled",   width=40,  anchor="center", stretch=False)
    self.tree.column("recursive", width=70,  anchor="center", stretch=False)
    self.tree.column("path",      width=400, anchor="w")

    style = ttk.Style()
    style.configure("Treeview", background=BG2, foreground=FG,
                    fieldbackground=BG2, rowheight=24, font=SANS)
    style.configure("Treeview.Heading", background=BG3, foreground=ACCENT,
                    font=SANS_B, relief="flat")
    style.map("Treeview", background=[("selected", BG3)],
              foreground=[("selected", ACCENT)])

    self.tree.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
    sb.pack(side="right", fill="y")
    self.tree.configure(yscrollcommand=sb.set)

    act = tk.Frame(self, bg=BG, padx=12, pady=4)
    act.pack(fill="x")
    styled_button(act, "⏻  Toggle",    self._toggle,    color=BG3, fg=WARNING).pack(side="left", padx=4)
    styled_button(act, "↺  Rec. Toggle", self._toggle_rec, color=BG3, fg=ACCENT).pack(side="left", padx=4)
    styled_button(act, "✕  Remove",    self._remove,    color=BG3, fg=DANGER).pack(side="left", padx=4)

    separator(self)

    # Add section
    add_frame = tk.Frame(self, bg=BG, padx=12, pady=6)
    add_frame.pack(fill="x")
    styled_label(add_frame, "Add Folder", font=SANS_B, fg=ACCENT).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0,6))

    self._path_var = tk.StringVar()
    path_entry = styled_entry(add_frame, textvariable=self._path_var, width=44)
    path_entry.grid(row=1, column=0, sticky="ew", padx=(0,6))

    styled_button(add_frame, "Browse", self._browse, color=BG3, fg=FG).grid(row=1, column=1, padx=4)

    self._recursive_var = tk.BooleanVar(value=True)
    chk = tk.Checkbutton(add_frame, text="Recursive (include subfolders)",
                          variable=self._recursive_var,
                          bg=BG, fg=FG, selectcolor=BG3,
                          activebackground=BG, font=SANS,
                          highlightthickness=0)
    chk.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

    styled_button(add_frame, "＋  Add Folder", self._add, color=ACCENT2, fg=BG).grid(
        row=3, column=0, sticky="w")

    separator(self)

    bottom = tk.Frame(self, bg=BG, padx=12, pady=8)
    bottom.pack(fill="x")
    styled_button(bottom, "✔  Save & Close", self._save, color=ACCENT, fg=BG).pack(side="right", padx=4)
    styled_button(bottom, "Cancel", self.destroy, color=BG3, fg=FG2).pack(side="right")

def _refresh_list(self):
    self.tree.delete(*self.tree.get_children())
    for i, f in enumerate(self.folders):
        on  = "✔" if f.get("enabled", True) else "—"
        rec = "✔" if f.get("recursive", False) else "—"
        self.tree.insert("", "end", iid=str(i),
                         values=(on, rec, f.get("path", "")))

def _selected_idx(self):
    sel = self.tree.selection()
    if not sel:
        return None
    return int(sel[0])

def _toggle(self):
    idx = self._selected_idx()
    if idx is None:
        return
    self.folders[idx]["enabled"] = not self.folders[idx].get("enabled", True)
    self._refresh_list()

def _toggle_rec(self):
    idx = self._selected_idx()
    if idx is None:
        return
    self.folders[idx]["recursive"] = not self.folders[idx].get("recursive", False)
    self._refresh_list()

def _remove(self):
    idx = self._selected_idx()
    if idx is None:
        return
    path = self.folders[idx].get("path", "this folder")
    if messagebox.askyesno("Remove", f"Remove «{path}»?", parent=self):
        del self.folders[idx]
        self._refresh_list()

def _browse(self):
    folder = filedialog.askdirectory(parent=self)
    if folder:
        self._path_var.set(folder)

def _add(self):
    path = self._path_var.get().strip()
    if not path:
        messagebox.showwarning("Missing", "Please select or enter a folder path.", parent=self)
        return
    if not os.path.isdir(path):
        messagebox.showwarning("Invalid", "Path does not exist or is not a directory.", parent=self)
        return
    # Avoid duplicates
    existing = [f["path"] for f in self.folders]
    if path in existing:
        messagebox.showinfo("Duplicate", "This folder is already in the list.", parent=self)
        return
    self.folders.append({"path": path, "enabled": True, "recursive": self._recursive_var.get()})
    self._path_var.set("")
    self._refresh_list()

def _save(self):
    self.on_save(self.folders)
    self.destroy()
```

# ─────────────────────────────────────────────

# MAIN APPLICATION

# ─────────────────────────────────────────────

class WebhookImageSender:
def **init**(self, root):
self.root = root
self.root.title(“WIS — Webhook Image Sender”)
self.root.geometry(“760x620”)
self.root.configure(bg=BG)
self.root.resizable(True, True)

```
    self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webhook_settings.json")

    # State
    self.webhooks: list  = []   # [{name, url, enabled}]
    self.folders: list   = []   # [{path, enabled, recursive}]
    self.auto_start      = tk.BooleanVar()
    self.debug_mode      = tk.BooleanVar(value=False)
    self.is_monitoring   = False
    self.monitoring_thread = None
    self.sent_files      = set()

    self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    self.load_settings()
    self._build_ui()

    if self.auto_start.get() and self._ready_to_monitor():
        self.root.after(1000, self.start_monitoring)

# ── UI BUILD ──────────────────────────────

def _build_ui(self):
    # ── Title bar ──
    title_bar = tk.Frame(self.root, bg=BG2, pady=0)
    title_bar.pack(fill="x")

    tk.Label(title_bar, text="WIS", bg=BG2, fg=ACCENT,
             font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=10)
    tk.Label(title_bar, text="Webhook Image Sender", bg=BG2, fg=FG2,
             font=("Segoe UI", 10)).pack(side="left", pady=10)

    # Status pill (right side of title bar)
    self._status_pill = tk.Label(
        title_bar, text="  ●  IDLE  ", bg=BG3, fg=FG2,
        font=("Segoe UI", 8, "bold"), padx=8, pady=3)
    self._status_pill.pack(side="right", padx=16, pady=10)

    separator(self.root, pady=0)

    # ── Two-column layout ──
    body = tk.Frame(self.root, bg=BG)
    body.pack(fill="both", expand=True, padx=0, pady=0)

    # Left panel
    left = tk.Frame(body, bg=BG, width=260)
    left.pack(side="left", fill="y", padx=16, pady=12)
    left.pack_propagate(False)

    self._build_left_panel(left)

    # Right panel (log)
    right = tk.Frame(body, bg=BG)
    right.pack(side="left", fill="both", expand=True, padx=(0,16), pady=12)

    self._build_right_panel(right)

def _build_left_panel(self, parent):
    # ── Folders section ──
    tk.Label(parent, text="MONITORED FOLDERS", bg=BG, fg=FG2,
             font=("Segoe UI", 7, "bold")).pack(anchor="w")
    separator(parent, pady=3)

    self._folder_summary = tk.Label(
        parent, text=self._folder_summary_text(),
        bg=BG2, fg=FG, font=SANS, wraplength=240,
        justify="left", padx=8, pady=6, anchor="nw")
    self._folder_summary.pack(fill="x", pady=(0,4))

    styled_button(parent, "📁  Manage Folders", self._open_folder_manager,
                  color=BG3, fg=ACCENT).pack(fill="x", pady=2)

    tk.Frame(parent, bg=BG, height=10).pack()

    # ── Webhooks section ──
    tk.Label(parent, text="WEBHOOKS", bg=BG, fg=FG2,
             font=("Segoe UI", 7, "bold")).pack(anchor="w")
    separator(parent, pady=3)

    self._webhook_summary = tk.Label(
        parent, text=self._webhook_summary_text(),
        bg=BG2, fg=FG, font=SANS, wraplength=240,
        justify="left", padx=8, pady=6, anchor="nw")
    self._webhook_summary.pack(fill="x", pady=(0,4))

    styled_button(parent, "⚙  Manage Webhooks", self._open_webhook_manager,
                  color=BG3, fg=ACCENT).pack(fill="x", pady=2)

    tk.Frame(parent, bg=BG, height=12).pack()
    separator(parent, pady=3)

    # ── Options ──
    def chk(text, var, cmd=None):
        c = tk.Checkbutton(parent, text=text, variable=var,
                           bg=BG, fg=FG, selectcolor=BG3,
                           activebackground=BG, font=SANS,
                           highlightthickness=0, command=cmd)
        c.pack(anchor="w", pady=2)

    chk("Auto-start on launch", self.auto_start, self.save_settings)
    chk("Debug mode",           self.debug_mode)

    tk.Frame(parent, bg=BG, height=12).pack()

    # ── Control buttons ──
    self.start_btn = styled_button(parent, "▶  Start Monitoring",
                                   self.start_monitoring, color=ACCENT2, fg=BG)
    self.start_btn.pack(fill="x", pady=3)

    self.stop_btn = styled_button(parent, "■  Stop Monitoring",
                                  self.stop_monitoring, color=DANGER, fg="white")
    self.stop_btn.pack(fill="x", pady=3)
    self.stop_btn.config(state="disabled")

def _build_right_panel(self, parent):
    hdr = tk.Frame(parent, bg=BG)
    hdr.pack(fill="x", pady=(0,6))

    tk.Label(hdr, text="ACTIVITY LOG", bg=BG, fg=FG2,
             font=("Segoe UI", 7, "bold")).pack(side="left")

    styled_button(hdr, "Clear", self.clear_log, color=BG3, fg=FG2).pack(side="right")

    # Stats strip
    stats = tk.Frame(parent, bg=BG2, pady=6)
    stats.pack(fill="x", pady=(0,6))

    self._stat_sent  = self._stat_pill(stats, "0", "Sent")
    self._stat_fails = self._stat_pill(stats, "0", "Failed")
    self._stat_hooks = self._stat_pill(stats, "0", "Webhooks")
    self._stat_dirs  = self._stat_pill(stats, "0", "Folders")
    self._refresh_stats()

    # Log area
    log_frame = tk.Frame(parent, bg=BG3,
                         highlightthickness=1, highlightbackground=BORDER)
    log_frame.pack(fill="both", expand=True)

    self.log_text = tk.Text(
        log_frame, bg=BG3, fg=FG, insertbackground=ACCENT,
        relief="flat", bd=0, font=MONO,
        wrap="word", state="normal"
    )
    self.log_text.pack(side="left", fill="both", expand=True, padx=6, pady=6)

    sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
    sb.pack(side="right", fill="y")
    self.log_text.configure(yscrollcommand=sb.set)

    # Tag colours
    self.log_text.tag_config("ok",      foreground=ACCENT2)
    self.log_text.tag_config("err",     foreground=DANGER)
    self.log_text.tag_config("warn",    foreground=WARNING)
    self.log_text.tag_config("info",    foreground=ACCENT)
    self.log_text.tag_config("debug",   foreground=FG2)
    self.log_text.tag_config("ts",      foreground=FG2)

    self._sent_count  = 0
    self._fail_count  = 0

def _stat_pill(self, parent, value, label):
    f = tk.Frame(parent, bg=BG2)
    f.pack(side="left", padx=14)
    val_lbl = tk.Label(f, text=value, bg=BG2, fg=ACCENT,
                       font=("Segoe UI", 16, "bold"))
    val_lbl.pack()
    tk.Label(f, text=label, bg=BG2, fg=FG2, font=SANS_SM).pack()
    return val_lbl

# ── Summary helpers ──────────────────────

def _folder_summary_text(self):
    enabled = [f for f in self.folders if f.get("enabled", True)]
    total   = len(self.folders)
    if not total:
        return "No folders configured"
    lines = []
    for f in enabled[:4]:
        rec = " ↳" if f.get("recursive") else ""
        lines.append(f"• {os.path.basename(f['path']) or f['path']}{rec}")
    if len(enabled) > 4:
        lines.append(f"  … +{len(enabled)-4} more")
    if not lines:
        return "0 folders enabled"
    return "\n".join(lines)

def _webhook_summary_text(self):
    enabled = [w for w in self.webhooks if w.get("enabled", True)]
    total   = len(self.webhooks)
    if not total:
        return "No webhooks configured"
    lines = []
    for w in enabled[:4]:
        lines.append(f"• {w.get('name', 'Unnamed')}")
    if len(enabled) > 4:
        lines.append(f"  … +{len(enabled)-4} more")
    if not lines:
        return "0 webhooks enabled"
    return "\n".join(lines)

def _refresh_stats(self):
    enabled_hooks  = sum(1 for w in self.webhooks if w.get("enabled", True))
    enabled_dirs   = sum(1 for f in self.folders  if f.get("enabled", True))
    self._stat_hooks.config(text=str(enabled_hooks))
    self._stat_dirs.config(text=str(enabled_dirs))

# ── Sub-window openers ──────────────────

def _open_webhook_manager(self):
    def on_save(new_webhooks):
        self.webhooks = new_webhooks
        self.save_settings()
        self._webhook_summary.config(text=self._webhook_summary_text())
        self._refresh_stats()
        self.log("Webhook list updated", "info")
    WebhookManagerWindow(self.root, self.webhooks, on_save)

def _open_folder_manager(self):
    def on_save(new_folders):
        self.folders = new_folders
        self.save_settings()
        self._folder_summary.config(text=self._folder_summary_text())
        self._refresh_stats()
        self.log("Folder list updated", "info")
    FolderManagerWindow(self.root, self.folders, on_save)

# ── Logging ──────────────────────────────

def log(self, message, kind="info"):
    """kind: ok | err | warn | info | debug"""
    ts = time.strftime("%H:%M:%S")
    icon = {"ok": "✓", "err": "✗", "warn": "⚠", "info": "·", "debug": "▸"}.get(kind, "·")
    self.log_text.config(state="normal")
    self.log_text.insert("end", f"[{ts}] ", "ts")
    self.log_text.insert("end", f"{icon} {message}\n", kind)
    self.log_text.see("end")
    self.log_text.config(state="disabled")

def clear_log(self):
    self.log_text.config(state="normal")
    self.log_text.delete("1.0", "end")
    self.log_text.config(state="disabled")

# ── Settings persistence ─────────────────

def load_settings(self):
    try:
        if os.path.exists(self.settings_file):
            with open(self.settings_file) as f:
                s = json.load(f)
            self.webhooks   = s.get("webhooks",   [])
            self.folders    = s.get("folders",    [])
            self.auto_start.set(s.get("auto_start", False))
            # Legacy migration: single webhook / folder
            if not self.webhooks and s.get("webhook_url"):
                self.webhooks = [{"name": "Default", "url": s["webhook_url"], "enabled": True}]
            if not self.folders and s.get("folder_path"):
                self.folders = [{"path": s["folder_path"], "enabled": True, "recursive": False}]
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings(self):
    try:
        s = {
            "webhooks":   self.webhooks,
            "folders":    self.folders,
            "auto_start": self.auto_start.get(),
        }
        with open(self.settings_file, "w") as f:
            json.dump(s, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")

# ── Monitoring ───────────────────────────

def _ready_to_monitor(self):
    active_folders  = [f for f in self.folders  if f.get("enabled", True) and os.path.isdir(f["path"])]
    active_webhooks = [w for w in self.webhooks if w.get("enabled", True) and w.get("url")]
    return bool(active_folders) and bool(active_webhooks)

def start_monitoring(self):
    active_folders  = [f for f in self.folders  if f.get("enabled", True)]
    active_webhooks = [w for w in self.webhooks if w.get("enabled", True) and w.get("url")]

    if not active_folders:
        self.log("No folders configured. Open Folder Manager to add one.", "warn")
        return
    if not active_webhooks:
        self.log("No webhooks configured. Open Webhook Manager to add one.", "warn")
        return

    # Validate folders exist
    valid_folders = []
    for f in active_folders:
        if os.path.isdir(f["path"]):
            valid_folders.append(f)
        else:
            self.log(f"Folder not found, skipping: {f['path']}", "warn")

    if not valid_folders:
        self.log("None of the enabled folders exist.", "err")
        return

    self._sent_count = 0
    self._fail_count = 0
    self._stat_sent.config(text="0")
    self._stat_fails.config(text="0")

    self.is_monitoring = True
    self.start_btn.config(state="disabled")
    self.stop_btn.config(state="normal")
    self._status_pill.config(text="  ●  MONITORING  ", bg="#1a3320", fg=ACCENT2)

    self._initialize_existing_files(valid_folders)

    self.monitoring_thread = Thread(
        target=self._monitor_loop,
        args=(valid_folders, active_webhooks),
        daemon=True
    )
    self.monitoring_thread.start()

    wh_names = ", ".join(w["name"] for w in active_webhooks)
    self.log(f"Started — {len(valid_folders)} folder(s) → {len(active_webhooks)} webhook(s): {wh_names}", "ok")

def stop_monitoring(self):
    self.is_monitoring = False
    self.start_btn.config(state="normal")
    self.stop_btn.config(state="disabled")
    self._status_pill.config(text="  ●  STOPPED  ", bg="#2a1a1a", fg=DANGER)
    self.log("Monitoring stopped", "warn")

def _initialize_existing_files(self, folders):
    count = 0
    for folder_cfg in folders:
        path      = folder_cfg["path"]
        recursive = folder_cfg.get("recursive", False)
        for fp in self._iter_images(path, recursive):
            self.sent_files.add(os.path.abspath(fp))
            count += 1
    self.log(f"Snapshot: {count} existing image(s) marked as seen", "debug")

def _iter_images(self, root_path, recursive):
    """Yield image file paths in root_path, optionally recursing into subdirs."""
    if recursive:
        for dirpath, _, filenames in os.walk(root_path):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in self.supported_formats:
                    yield os.path.join(dirpath, fn)
    else:
        try:
            for fn in os.listdir(root_path):
                fp = os.path.join(root_path, fn)
                if os.path.isfile(fp) and os.path.splitext(fn)[1].lower() in self.supported_formats:
                    yield fp
        except Exception:
            pass

def _monitor_loop(self, folders, webhooks):
    scan = 0
    while self.is_monitoring:
        scan += 1
        if self.debug_mode.get():
            self.log(f"Scan #{scan} across {len(folders)} folder(s)", "debug")

        for folder_cfg in folders:
            path      = folder_cfg["path"]
            recursive = folder_cfg.get("recursive", False)

            try:
                for fp in self._iter_images(path, recursive):
                    abs_fp = os.path.abspath(fp)
                    if abs_fp in self.sent_files:
                        continue

                    fname = os.path.basename(abs_fp)
                    rel   = os.path.relpath(abs_fp, path)
                    self.log(f"New file: {rel}  [{os.path.basename(path)}]", "info")
                    time.sleep(0.8)  # let file finish writing

                    if not os.path.exists(abs_fp):
                        continue
                    try:
                        if os.path.getsize(abs_fp) == 0:
                            self.log(f"Skipping empty file: {fname}", "warn")
                            continue
                    except Exception:
                        continue

                    # Send to all active webhooks
                    all_ok = True
                    for wh in webhooks:
                        ok = self._send_file(abs_fp, wh)
                        if not ok:
                            all_ok = False

                    self.sent_files.add(abs_fp)
                    if all_ok:
                        self._sent_count += 1
                    else:
                        self._fail_count += 1
                    self.root.after(0, self._update_sent_stats)

            except Exception as e:
                self.log(f"Error scanning {path}: {e}", "err")

        time.sleep(1)

def _update_sent_stats(self):
    self._stat_sent.config(text=str(self._sent_count))
    self._stat_fails.config(text=str(self._fail_count))

def _send_file(self, file_path, webhook):
    fname     = os.path.basename(file_path)
    wh_name   = webhook.get("name", "?")
    wh_url    = webhook.get("url",  "")
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"
    try:
        with open(file_path, "rb") as fh:
            resp = requests.post(
                wh_url,
                files={"file": (fname, fh, mime_type)},
                timeout=30
            )
        if resp.status_code in (200, 201, 204):
            self.log(f"✓ {fname}  →  {wh_name}", "ok")
            return True
        else:
            self.log(f"HTTP {resp.status_code}  {fname}  →  {wh_name}", "err")
            return False
    except requests.exceptions.RequestException as e:
        self.log(f"Network error  {fname}  →  {wh_name}: {e}", "err")
        return False
    except Exception as e:
        self.log(f"Error  {fname}  →  {wh_name}: {e}", "err")
        return False
```

# ─────────────────────────────────────────────

# ENTRY POINT

# ─────────────────────────────────────────────

def main():
root = tk.Tk()
root.minsize(680, 520)
app = WebhookImageSender(root)
root.mainloop()

if **name** == “**main**”:
main()