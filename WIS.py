import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import time
import requests
import json
from threading import Thread
import mimetypes

# ─────────────────────────────────────────────
#  DEFAULTS
# ─────────────────────────────────────────────
DEFAULTS = {
    "bg":           "#0f1117",
    "bg2":          "#181c26",
    "bg3":          "#1f2433",
    "accent":       "#4f8ef7",
    "accent2":      "#2ecc8f",
    "danger":       "#e05252",
    "warning":      "#f0a500",
    "fg":           "#d6dce8",
    "fg2":          "#7a8499",
    "border":       "#2a3045",
    "scan_rate":    1.0,
    "send_timeout": 30,
    "file_delay":   0.8,
    "formats":      ".jpg,.jpeg,.png,.gif,.bmp,.webp",
}

C = dict(DEFAULTS)  # live colour dict, mutated by settings


def _lighten(hex_color, amt=25):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(min(255,r+amt), min(255,g+amt), min(255,b+amt))


def apply_treeview_style():
    """Set ttk dark theme once globally."""
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Treeview",
                background=C["bg2"], foreground=C["fg"],
                fieldbackground=C["bg2"], rowheight=26,
                font=("Segoe UI", 9))
    s.configure("Treeview.Heading",
                background=C["bg3"], foreground=C["accent"],
                font=("Segoe UI", 9, "bold"), relief="flat")
    s.map("Treeview",
          background=[("selected", C["bg3"])],
          foreground=[("selected", C["accent"])])
    s.configure("Vertical.TScrollbar",
                background=C["bg3"], troughcolor=C["bg2"],
                arrowcolor=C["fg2"])


# ─────────────────────────────────────────────
#  WIDGET FACTORY HELPERS
# ─────────────────────────────────────────────

def mk_btn(parent, text, command, color=None, fg=None, **kw):
    color = color or C["bg3"]
    fg    = fg    or C["accent"]
    b = tk.Button(parent, text=text, command=command,
                  bg=color, fg=fg,
                  activebackground=_lighten(color), activeforeground=fg,
                  relief="flat", bd=0, padx=12, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2", **kw)
    b.bind("<Enter>", lambda e: b.config(bg=_lighten(color)))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


def mk_entry(parent, textvariable=None, width=40):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=C["bg3"], fg=C["fg"], insertbackground=C["accent"],
                    relief="flat", bd=0, font=("Segoe UI", 9),
                    highlightthickness=1,
                    highlightbackground=C["border"],
                    highlightcolor=C["accent"])


def mk_label(parent, text, fg=None, font=None, bg=None, **kw):
    bg = bg if bg is not None else C["bg"]
    return tk.Label(parent, text=text, bg=bg, fg=fg or C["fg"],
                    font=font or ("Segoe UI", 9), **kw)


def mk_sep(parent):
    """Horizontal separator — always uses pack on parent."""
    tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=6)


def mk_chk(parent, text, variable, command=None, bg=None):
    bg = bg if bg is not None else C["bg"]
    c = tk.Checkbutton(parent, text=text, variable=variable,
                       bg=bg, fg=C["fg"], selectcolor=C["bg3"],
                       activebackground=bg, activeforeground=C["fg"],
                       font=("Segoe UI", 9), highlightthickness=0,
                       command=command)
    return c


def mk_section(parent, text):
    tk.Label(parent, text=text, bg=C["bg"], fg=C["fg2"],
             font=("Segoe UI", 7, "bold")).pack(anchor="w")
    tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=3)


# ─────────────────────────────────────────────
#  TREEVIEW PANEL  (reusable)
# ─────────────────────────────────────────────

class TreePanel(tk.Frame):
    def __init__(self, parent, columns, headings, widths, height=9):
        super().__init__(parent, bg=C["bg"])
        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                  height=height, selectmode="browse")
        for col, hd, w in zip(columns, headings, widths):
            self.tree.heading(col, text=hd)
            anchor = "center" if w <= 60 else "w"
            self.tree.column(col, width=w, anchor=anchor,
                             stretch=(col == columns[-1]))
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def selected_idx(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def insert(self, iid, values):
        self.tree.insert("", "end", iid=str(iid), values=values)


# ─────────────────────────────────────────────
#  BASE POPUP
#
#  Layout (top → bottom, all via pack on self):
#    [header frame]
#    [body frame]          ← subclasses put content here
#    [footer frame]        ← added by self._add_footer()
#
#  RULE: never call pack/grid on `self` (Toplevel) inside subclass —
#  only add children to self.body.
# ─────────────────────────────────────────────

class BasePopup(tk.Toplevel):
    def __init__(self, parent, title, subtitle="", size="560x500"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.geometry(size)

        # ── header ──
        hdr = tk.Frame(self, bg=C["bg2"])
        hdr.pack(fill="x", side="top")
        mk_label(hdr, title, fg=C["accent"], bg=C["bg2"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=14, pady=10)
        if subtitle:
            mk_label(hdr, subtitle, fg=C["fg2"], bg=C["bg2"],
                     font=("Segoe UI", 8)).pack(side="left")

        # ── footer (packed to bottom BEFORE body so body fills remaining space) ──
        self._footer_frame = tk.Frame(self, bg=C["bg"])
        self._footer_frame.pack(fill="x", side="bottom", padx=12, pady=8)
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", side="bottom")

        # ── body (fills all space between header and footer) ──
        self.body = tk.Frame(self, bg=C["bg"])
        self.body.pack(fill="both", expand=True, padx=14, pady=10, side="top")

    def add_footer_buttons(self, save_cmd, cancel_cmd=None):
        """Call this at the END of subclass _build() to add Save/Cancel."""
        mk_btn(self._footer_frame, "Save & Close", save_cmd,
               color=C["accent"], fg=C["bg"]).pack(side="right", padx=(4, 0))
        mk_btn(self._footer_frame, "Cancel",
               cancel_cmd or self.destroy,
               color=C["bg3"], fg=C["fg2"]).pack(side="right")


# ─────────────────────────────────────────────
#  WEBHOOK MANAGER
# ─────────────────────────────────────────────

class WebhookManager(BasePopup):
    def __init__(self, parent, webhooks, on_save):
        super().__init__(parent, "Webhook Manager",
                         "One detection is sent to all enabled webhooks",
                         size="600x500")
        self.webhooks  = [dict(w) for w in webhooks]
        self.on_save   = on_save
        self._edit_idx = None
        self._build()
        self._refresh()

    def _build(self):
        b = self.body

        # ── list ──
        self.panel = TreePanel(b,
            columns=("on", "name", "url"),
            headings=("On", "Name", "URL"),
            widths=(44, 140, 340))
        self.panel.pack(fill="both", expand=True)

        act = tk.Frame(b, bg=C["bg"])
        act.pack(fill="x", pady=(4, 0))
        mk_btn(act, "Edit",   self._edit,   color=C["bg3"], fg=C["accent"]).pack(side="left", padx=(0, 4))
        mk_btn(act, "Toggle", self._toggle, color=C["bg3"], fg=C["warning"]).pack(side="left", padx=4)
        mk_btn(act, "Remove", self._remove, color=C["bg3"], fg=C["danger"]).pack(side="left", padx=4)

        tk.Frame(b, bg=C["border"], height=1).pack(fill="x", pady=8)

        # ── add / edit form  (pure pack, no grid mixing) ──
        mk_label(b, "Add / Edit Webhook", fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        # Name row
        name_row = tk.Frame(b, bg=C["bg"])
        name_row.pack(fill="x", pady=2)
        mk_label(name_row, "Name:", fg=C["fg2"], width=6, anchor="w").pack(side="left")
        self._name_var = tk.StringVar()
        mk_entry(name_row, textvariable=self._name_var, width=26).pack(side="left", padx=(4, 0))

        # URL row
        url_row = tk.Frame(b, bg=C["bg"])
        url_row.pack(fill="x", pady=2)
        mk_label(url_row, "URL:", fg=C["fg2"], width=6, anchor="w").pack(side="left")
        self._url_var = tk.StringVar()
        mk_entry(url_row, textvariable=self._url_var, width=56).pack(side="left", padx=(4, 0), fill="x", expand=True)

        # Buttons
        btn_row = tk.Frame(b, bg=C["bg"])
        btn_row.pack(fill="x", pady=(8, 0))
        self._add_btn = mk_btn(btn_row, "+ Add", self._commit, color=C["accent2"], fg=C["bg"])
        self._add_btn.pack(side="left")
        mk_btn(btn_row, "Clear", self._clear_form, color=C["bg3"], fg=C["fg2"]).pack(side="left", padx=8)

        self.add_footer_buttons(self._save)

    def _refresh(self):
        self.panel.clear()
        for i, w in enumerate(self.webhooks):
            on = "✔" if w.get("enabled", True) else "—"
            self.panel.insert(i, (on, w.get("name", ""), w.get("url", "")))

    def _edit(self):
        idx = self.panel.selected_idx()
        if idx is None: return
        w = self.webhooks[idx]
        self._name_var.set(w.get("name", ""))
        self._url_var.set(w.get("url", ""))
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
        if self._edit_idx is not None:
            self.webhooks[self._edit_idx].update(name=name, url=url)
            self._edit_idx = None
        else:
            self.webhooks.append({"name": name, "url": url, "enabled": True})
        self._clear_form()
        self._refresh()

    def _clear_form(self):
        self._name_var.set("")
        self._url_var.set("")
        self._edit_idx = None
        self._add_btn.config(text="+ Add")

    def _save(self):
        try:
            self.on_save(self.webhooks)
        finally:
            self.destroy()


# ─────────────────────────────────────────────
#  FOLDER MANAGER
# ─────────────────────────────────────────────

class FolderManager(BasePopup):
    def __init__(self, parent, folders, on_save):
        super().__init__(parent, "Folder Manager",
                         "All enabled folders are scanned simultaneously",
                         size="640x540")
        self.folders  = [dict(f) for f in folders]
        self.on_save  = on_save
        self._build()
        self._refresh()

    def _build(self):
        b = self.body

        # ── TOP: tree + action buttons (fixed height, does NOT expand) ──
        top = tk.Frame(b, bg=C["bg"])
        top.pack(fill="x", side="top")

        self.panel = TreePanel(top,
            columns=("on", "rec", "path"),
            headings=("On", "Recursive", "Folder Path"),
            widths=(44, 80, 440),
            height=7)
        self.panel.pack(fill="x")

        act = tk.Frame(top, bg=C["bg"])
        act.pack(fill="x", pady=(4, 0))
        mk_btn(act, "Toggle",           self._toggle,     color=C["bg3"], fg=C["warning"]).pack(side="left", padx=(0, 4))
        mk_btn(act, "Toggle Recursive", self._toggle_rec, color=C["bg3"], fg=C["accent"]).pack(side="left", padx=4)
        mk_btn(act, "Remove",           self._remove,     color=C["bg3"], fg=C["danger"]).pack(side="left", padx=4)

        tk.Frame(b, bg=C["border"], height=1).pack(fill="x", pady=8, side="top")

        # ── BOTTOM: add form (fixed, always visible) ──
        bottom = tk.Frame(b, bg=C["bg"])
        bottom.pack(fill="x", side="top")

        mk_label(bottom, "Add Folder", fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))

        # Path row: Browse packed RIGHT first, then entry fills remaining space
        path_row = tk.Frame(bottom, bg=C["bg"])
        path_row.pack(fill="x", pady=(0, 6))
        self._path_var = tk.StringVar()
        mk_btn(path_row, "Browse", self._browse,
               color=C["bg3"], fg=C["fg"]).pack(side="right", padx=(6, 0))
        self._path_entry = mk_entry(path_row, textvariable=self._path_var, width=2)
        self._path_entry.pack(side="left", fill="x", expand=True)

        # Recursive checkbox
        self._recursive_var = tk.BooleanVar(value=True)
        mk_chk(bottom, "Recursive (include subfolders)", self._recursive_var,
               bg=C["bg"]).pack(anchor="w", pady=(0, 8))

        # Add button in its own frame so it is never clipped
        add_frame = tk.Frame(bottom, bg=C["bg"])
        add_frame.pack(fill="x")
        mk_btn(add_frame, "+ Add Folder", self._add,
               color=C["accent2"], fg=C["bg"]).pack(side="left")

        self.add_footer_buttons(self._save)

    def _refresh(self):
        self.panel.clear()
        for i, f in enumerate(self.folders):
            on  = "✔" if f.get("enabled",   True)  else "—"
            rec = "✔" if f.get("recursive", False) else "—"
            self.panel.insert(i, (on, rec, f.get("path", "")))

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
            messagebox.showwarning("Missing", "Select or type a folder path.", parent=self)
            return
        if not os.path.isdir(path):
            messagebox.showwarning("Invalid", f"Not a valid directory:\n{path}", parent=self)
            return
        existing = [f["path"] for f in self.folders]
        if path in existing:
            messagebox.showinfo("Duplicate", "This folder is already in the list.", parent=self)
            return
        self.folders.append({
            "path":      path,
            "enabled":   True,
            "recursive": self._recursive_var.get()
        })
        self._path_var.set("")
        self._refresh()

    def _save(self):
        try:
            self.on_save(self.folders)
        finally:
            self.destroy()


# ─────────────────────────────────────────────
#  SETTINGS MANAGER
# ─────────────────────────────────────────────

class SettingsManager(BasePopup):
    def __init__(self, parent, settings, on_save):
        super().__init__(parent, "Settings", size="500x560")
        self.settings = dict(settings)
        self.on_save  = on_save
        self._vars    = {}
        self._build()

    def _build(self):
        b = self.body

        # Scrollable canvas so content fits on small screens
        canvas = tk.Canvas(b, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(b, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["bg"])
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(inner_id, width=canvas.winfo_width())
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(inner_id, width=e.width))

        # ── Behaviour ──
        self._section(inner, "Behaviour")
        self._num_row(inner, "Scan rate (seconds)",         "scan_rate",    1.0)
        self._num_row(inner, "Send timeout (seconds)",      "send_timeout", 30)
        self._num_row(inner, "File settle delay (seconds)", "file_delay",   0.8)

        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── File types ──
        self._section(inner, "Watched Extensions")
        mk_label(inner, "Comma-separated  (e.g.  .jpg,.png,.gif)",
                 fg=C["fg2"], font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 4))
        self._vars["formats"] = tk.StringVar(value=self.settings.get("formats", DEFAULTS["formats"]))
        mk_entry(inner, textvariable=self._vars["formats"], width=50).pack(anchor="w", pady=(0, 4))

        tk.Frame(inner, bg=C["bg"], height=6).pack()

        # ── Colours ──
        self._section(inner, "Colours (hex codes)")

        colour_defs = [
            ("bg",      "Background"),
            ("bg2",     "Surface / header"),
            ("bg3",     "Input / card"),
            ("accent",  "Accent (blue)"),
            ("accent2", "Success (green)"),
            ("danger",  "Danger (red)"),
            ("warning", "Warning (orange)"),
            ("fg",      "Primary text"),
            ("fg2",     "Secondary text"),
            ("border",  "Borders"),
        ]

        grid = tk.Frame(inner, bg=C["bg"])
        grid.pack(fill="x", pady=4)

        for i, (key, lbl_text) in enumerate(colour_defs):
            row_frame = tk.Frame(grid, bg=C["bg"])
            row_frame.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=2)
            mk_label(row_frame, lbl_text, fg=C["fg2"],
                     font=("Segoe UI", 8), width=18, anchor="w").pack(side="left")
            self._vars[key] = tk.StringVar(value=self.settings.get(key, DEFAULTS.get(key, "")))
            mk_entry(row_frame, textvariable=self._vars[key], width=10).pack(side="left")

        tk.Frame(inner, bg=C["bg"], height=4).pack()
        mk_btn(inner, "Reset colours to defaults", self._reset_colours,
               color=C["bg3"], fg=C["fg2"]).pack(anchor="w", pady=4)

        self.add_footer_buttons(self._save)

    def _section(self, parent, text):
        mk_label(parent, text, fg=C["accent"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=(2, 6))

    def _num_row(self, parent, label_text, key, default):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=2)
        mk_label(row, label_text, fg=C["fg"], width=30, anchor="w").pack(side="left")
        self._vars[key] = tk.StringVar(value=str(self.settings.get(key, default)))
        mk_entry(row, textvariable=self._vars[key], width=8).pack(side="left", padx=(6, 0))

    def _reset_colours(self):
        for k in ["bg","bg2","bg3","accent","accent2","danger","warning","fg","fg2","border"]:
            if k in self._vars:
                self._vars[k].set(DEFAULTS[k])

    def _save(self):
        out = {}
        for key in ("scan_rate", "send_timeout", "file_delay"):
            try:
                out[key] = float(self._vars[key].get())
            except ValueError:
                out[key] = DEFAULTS[key]
        out["formats"] = self._vars["formats"].get().strip()
        for key in ["bg","bg2","bg3","accent","accent2","danger","warning","fg","fg2","border"]:
            val = self._vars[key].get().strip()
            out[key] = val if val.startswith("#") and len(val) == 7 else DEFAULTS.get(key)
        try:
            self.on_save(out)
        finally:
            self.destroy()


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────

class WIS:
    def __init__(self, root):
        self.root = root
        self.root.title("WIS — Webhook Image Sender")
        self.root.minsize(720, 540)
        self.root.geometry("820x640")

        self.settings_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "webhook_settings.json")

        self.webhooks: list = []
        self.folders:  list = []
        self.settings: dict = dict(DEFAULTS)

        self.auto_start = tk.BooleanVar()
        self.debug_mode = tk.BooleanVar(value=False)

        self.is_monitoring     = False
        self.monitoring_thread = None
        self.sent_files: set   = set()
        self._sent_count       = 0
        self._fail_count       = 0

        self.load_settings()

        C.update({k: self.settings[k] for k in DEFAULTS if k in self.settings})
        self.root.configure(bg=C["bg"])
        apply_treeview_style()

        self._build_ui()

        if self.auto_start.get() and self._ready():
            self.root.after(1000, self.start_monitoring)

    # ── UI ──────────────────────────────────────

    def _build_ui(self):
        # Title bar
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
                                    wraplength=250, justify="left",
                                    padx=8, pady=6, anchor="nw")
        self._folder_lbl.pack(fill="x", pady=(0, 4))
        mk_btn(p, "Manage Folders", self._open_folders,
               color=C["bg3"], fg=C["accent"]).pack(fill="x", pady=2)

        tk.Frame(p, bg=C["bg"], height=10).pack()

        mk_section(p, "WEBHOOKS")
        self._webhook_lbl = tk.Label(p, text=self._webhook_summary(),
                                     bg=C["bg2"], fg=C["fg"], font=("Segoe UI", 9),
                                     wraplength=250, justify="left",
                                     padx=8, pady=6, anchor="nw")
        self._webhook_lbl.pack(fill="x", pady=(0, 4))
        mk_btn(p, "Manage Webhooks", self._open_webhooks,
               color=C["bg3"], fg=C["accent"]).pack(fill="x", pady=2)

        tk.Frame(p, bg=C["bg"], height=10).pack()
        tk.Frame(p, bg=C["border"], height=1).pack(fill="x", pady=4)

        mk_chk(p, "Auto-start on launch", self.auto_start,
               command=self.save_settings).pack(anchor="w", pady=2)
        mk_chk(p, "Debug mode", self.debug_mode).pack(anchor="w", pady=2)

        tk.Frame(p, bg=C["bg"], height=8).pack()
        mk_btn(p, "Settings", self._open_settings,
               color=C["bg3"], fg=C["fg"]).pack(fill="x", pady=2)

        tk.Frame(p, bg=C["bg"], height=8).pack()

        self.start_btn = mk_btn(p, "Start Monitoring", self.start_monitoring,
                                color=C["accent2"], fg=C["bg"])
        self.start_btn.pack(fill="x", pady=3)

        self.stop_btn = mk_btn(p, "Stop Monitoring", self.stop_monitoring,
                               color=C["danger"], fg="white")
        self.stop_btn.pack(fill="x", pady=3)
        self.stop_btn.config(state="disabled")

    def _build_right(self, p):
        hdr = tk.Frame(p, bg=C["bg"])
        hdr.pack(fill="x", pady=(0, 6))
        mk_label(hdr, "ACTIVITY LOG", fg=C["fg2"],
                 font=("Segoe UI", 7, "bold")).pack(side="left")
        mk_btn(hdr, "Clear", self.clear_log,
               color=C["bg3"], fg=C["fg2"]).pack(side="right")

        stats = tk.Frame(p, bg=C["bg2"], pady=6)
        stats.pack(fill="x", pady=(0, 6))
        self._s_sent  = self._pill(stats, "0", "Sent")
        self._s_fail  = self._pill(stats, "0", "Failed")
        self._s_hooks = self._pill(stats, "0", "Webhooks")
        self._s_dirs  = self._pill(stats, "0", "Folders")
        self._refresh_stats()

        log_wrap = tk.Frame(p, bg=C["bg3"],
                            highlightthickness=1, highlightbackground=C["border"])
        log_wrap.pack(fill="both", expand=True)

        self.log_box = tk.Text(log_wrap, bg=C["bg3"], fg=C["fg"],
                               insertbackground=C["accent"],
                               relief="flat", bd=0,
                               font=("Consolas", 9), wrap="word",
                               state="disabled")
        self.log_box.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log_box.yview)
        sb.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=sb.set)

        self.log_box.tag_config("ok",    foreground=C["accent2"])
        self.log_box.tag_config("err",   foreground=C["danger"])
        self.log_box.tag_config("warn",  foreground=C["warning"])
        self.log_box.tag_config("info",  foreground=C["accent"])
        self.log_box.tag_config("debug", foreground=C["fg2"])
        self.log_box.tag_config("ts",    foreground=C["fg2"])

    def _pill(self, parent, value, label):
        f = tk.Frame(parent, bg=C["bg2"])
        f.pack(side="left", padx=14)
        v = mk_label(f, value, fg=C["accent"], bg=C["bg2"],
                     font=("Segoe UI", 16, "bold"))
        v.pack()
        mk_label(f, label, fg=C["fg2"], bg=C["bg2"],
                 font=("Segoe UI", 8)).pack()
        return v

    # ── Summaries ──────────────────────────────

    def _folder_summary(self):
        enabled = [f for f in self.folders if f.get("enabled", True)]
        if not self.folders: return "No folders configured"
        if not enabled:      return "All folders disabled"
        lines = []
        for f in enabled[:4]:
            rec = " (recursive)" if f.get("recursive") else ""
            name = os.path.basename(f["path"]) or f["path"]
            lines.append(f"• {name}{rec}")
        if len(enabled) > 4:
            lines.append(f"  +{len(enabled)-4} more")
        return "\n".join(lines)

    def _webhook_summary(self):
        enabled = [w for w in self.webhooks if w.get("enabled", True)]
        if not self.webhooks: return "No webhooks configured"
        if not enabled:       return "All webhooks disabled"
        lines = [f"• {w.get('name','Unnamed')}" for w in enabled[:4]]
        if len(enabled) > 4: lines.append(f"  +{len(enabled)-4} more")
        return "\n".join(lines)

    def _refresh_stats(self):
        self._s_hooks.config(text=str(sum(1 for w in self.webhooks if w.get("enabled", True))))
        self._s_dirs.config( text=str(sum(1 for f in self.folders  if f.get("enabled", True))))

    # ── Sub-windows ────────────────────────────

    def _open_folders(self):
        def on_save(v):
            self.folders = v
            self.save_settings()
            self._folder_lbl.config(text=self._folder_summary())
            self._refresh_stats()
            self.log("Folder list updated", "info")
        FolderManager(self.root, self.folders, on_save)

    def _open_webhooks(self):
        def on_save(v):
            self.webhooks = v
            self.save_settings()
            self._webhook_lbl.config(text=self._webhook_summary())
            self._refresh_stats()
            self.log("Webhook list updated", "info")
        WebhookManager(self.root, self.webhooks, on_save)

    def _open_settings(self):
        def on_save(new_s):
            self.settings.update(new_s)
            C.update(new_s)
            apply_treeview_style()
            self.save_settings()
            self.log("Settings saved — restart to fully apply colour changes", "warn")
        SettingsManager(self.root, self.settings, on_save)

    # ── Logging ────────────────────────────────

    def log(self, message, kind="info"):
        icons = {"ok": "✓", "err": "✗", "warn": "!", "info": "·", "debug": ">"}
        ts   = time.strftime("%H:%M:%S")
        icon = icons.get(kind, "·")
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{ts}] ", "ts")
        self.log_box.insert("end", f"{icon} {message}\n", kind)
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    # ── Persistence ────────────────────────────

    def load_settings(self):
        try:
            if not os.path.exists(self.settings_file):
                return
            with open(self.settings_file) as f:
                s = json.load(f)
            self.webhooks = s.get("webhooks", [])
            self.folders  = s.get("folders",  [])
            self.auto_start.set(s.get("auto_start", False))
            for k in DEFAULTS:
                if k in s:
                    self.settings[k] = s[k]
            # Legacy migration
            if not self.webhooks and s.get("webhook_url"):
                self.webhooks = [{"name": "Default", "url": s["webhook_url"], "enabled": True}]
            if not self.folders and s.get("folder_path"):
                self.folders = [{"path": s["folder_path"], "enabled": True, "recursive": False}]
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            s = {"webhooks": self.webhooks, "folders": self.folders,
                 "auto_start": self.auto_start.get()}
            s.update(self.settings)
            with open(self.settings_file, "w") as f:
                json.dump(s, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    # ── Monitoring ─────────────────────────────

    def _ready(self):
        af = [f for f in self.folders  if f.get("enabled") and os.path.isdir(f.get("path",""))]
        aw = [w for w in self.webhooks if w.get("enabled") and w.get("url")]
        return bool(af) and bool(aw)

    def _formats(self):
        raw = self.settings.get("formats", DEFAULTS["formats"])
        return {e.strip().lower() for e in raw.split(",") if e.strip()}

    def start_monitoring(self):
        active_folders  = [f for f in self.folders  if f.get("enabled", True)]
        active_webhooks = [w for w in self.webhooks if w.get("enabled", True) and w.get("url")]

        if not active_folders:
            self.log("No folders configured.", "warn"); return
        if not active_webhooks:
            self.log("No webhooks configured.", "warn"); return

        valid = [f for f in active_folders if os.path.isdir(f.get("path", ""))]
        for f in active_folders:
            if f not in valid:
                self.log(f"Folder not found, skipping: {f['path']}", "warn")
        if not valid:
            self.log("No valid folders found.", "err"); return

        self._sent_count = 0
        self._fail_count = 0
        self._s_sent.config(text="0")
        self._s_fail.config(text="0")
        self.sent_files.clear()

        self.is_monitoring = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._status_pill.config(text="  MONITORING  ", bg="#1a3320", fg=C["accent2"])

        self._snapshot(valid)

        self.monitoring_thread = Thread(
            target=self._loop, args=(valid, active_webhooks), daemon=True)
        self.monitoring_thread.start()

        names = ", ".join(w["name"] for w in active_webhooks)
        self.log(f"Started — {len(valid)} folder(s) → {len(active_webhooks)} webhook(s): {names}", "ok")

    def stop_monitoring(self):
        self.is_monitoring = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._status_pill.config(text="  STOPPED  ", bg="#2a1a1a", fg=C["danger"])
        self.log("Monitoring stopped", "warn")

    def _snapshot(self, folders):
        fmts = self._formats()
        count = 0
        for fc in folders:
            for fp in self._iter_images(fc["path"], fc.get("recursive", False), fmts):
                self.sent_files.add(os.path.abspath(fp))
                count += 1
        self.log(f"Snapshot: {count} existing file(s) marked as seen", "debug")

    def _iter_images(self, root, recursive, fmts):
        if recursive:
            for dirpath, _, files in os.walk(root):
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in fmts:
                        yield os.path.join(dirpath, fn)
        else:
            try:
                for fn in os.listdir(root):
                    fp = os.path.join(root, fn)
                    if os.path.isfile(fp) and os.path.splitext(fn)[1].lower() in fmts:
                        yield fp
            except Exception:
                pass

    def _loop(self, folders, webhooks):
        fmts       = self._formats()
        scan_rate  = float(self.settings.get("scan_rate",  1.0))
        file_delay = float(self.settings.get("file_delay", 0.8))
        scan = 0
        while self.is_monitoring:
            scan += 1
            if self.debug_mode.get():
                self.log(f"Scan #{scan}", "debug")
            for fc in folders:
                try:
                    for fp in self._iter_images(fc["path"], fc.get("recursive", False), fmts):
                        abs_fp = os.path.abspath(fp)
                        if abs_fp in self.sent_files:
                            continue
                        rel = os.path.relpath(abs_fp, fc["path"])
                        self.log(f"New: {rel}  [{os.path.basename(fc['path'])}]", "info")
                        time.sleep(file_delay)
                        if not os.path.exists(abs_fp):
                            continue
                        try:
                            if os.path.getsize(abs_fp) == 0:
                                self.log(f"Empty, skipping: {rel}", "warn")
                                continue
                        except Exception:
                            continue
                        all_ok = all(self._send(abs_fp, wh) for wh in webhooks)
                        self.sent_files.add(abs_fp)
                        if all_ok: self._sent_count += 1
                        else:      self._fail_count += 1
                        self.root.after(0, lambda sc=self._sent_count, fc=self._fail_count: (
                            self._s_sent.config(text=str(sc)),
                            self._s_fail.config(text=str(fc))
                        ))
                except Exception as e:
                    self.log(f"Error scanning {fc['path']}: {e}", "err")
            time.sleep(scan_rate)

    def _send(self, file_path, webhook):
        fname   = os.path.basename(file_path)
        name    = webhook.get("name", "?")
        url     = webhook.get("url", "")
        timeout = int(self.settings.get("send_timeout", 30))
        mime, _ = mimetypes.guess_type(file_path)
        mime    = mime or "application/octet-stream"
        try:
            with open(file_path, "rb") as fh:
                r = requests.post(url, files={"file": (fname, fh, mime)}, timeout=timeout)
            if r.status_code in (200, 201, 204):
                self.log(f"{fname}  →  {name}", "ok"); return True
            self.log(f"HTTP {r.status_code}  {fname}  →  {name}", "err"); return False
        except Exception as e:
            self.log(f"Error  {fname}  →  {name}: {e}", "err"); return False


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    root = tk.Tk()
    WIS(root)
    root.mainloop()


if __name__ == "__main__":
    main()
