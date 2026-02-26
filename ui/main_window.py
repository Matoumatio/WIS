import tkinter as tk
from models.theme import ThemeModel
from ui.components.factory import WidgetFactory
from ui.styles.theme_manager import ThemeManager

class MainWindow:
    
    def __init__(self, root: tk.Tk, theme: ThemeModel, commands: dict):
        self.root = root
        self.theme = theme
        self.factory = WidgetFactory(theme)
        self.commands = commands

        self.root.configure(bg=theme.bg)
        ThemeManager.apply_ttk_styles(theme)

        self._setup_ui()
    
    def _setup_ui(self):
        # 1. Top Bar
        top_bar = tk.Frame(self.root, bg=self.theme.bg2)
        top_bar.pack(fill="x", side="top")
        
        self.factory.create_label(top_bar, "WIS", is_header=True).pack(side="left", padx=16, pady=8)
        self.factory.create_label(top_bar, "Webhook Image Sender", color=self.theme.fg2).pack(side="left")

        # 2. Main Content Wrapper
        content = tk.Frame(self.root, bg=self.theme.bg)
        content.pack(fill="both", expand=True)
        
        # 3. Left Sidebar (Controls)
        sidebar = tk.Frame(content, bg=self.theme.bg, width=270)
        sidebar.pack(side="left", fill="y", padx=14, pady=12)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)
        
        # 4. Right Area (Log and Stats)
        right_area = tk.Frame(content, bg=self.theme.bg)
        right_area.pack(side="left", fill="both", expand=True, padx=(0, 14), pady=12)
        self._build_activity_log(right_area)

        # Status
        self.status_pill = self.factory.create_label(top_bar, "  IDLE  ", color=self.theme.fg2)
        self.status_pill.config(bg=self.theme.bg3, font=("Segoe UI", 8, "bold"))
        self.status_pill.pack(side="right", padx=16, pady=8, ipadx=6, ipady=3)
    
    def _build_sidebar(self, parent):
        self.factory.create_section_header(parent, "Monitored Folders").pack(fill="x")
        
        self.folder_summary_lbl = tk.Label(parent, text="No folders configured", 
                                           bg=self.theme.bg2, fg=self.theme.fg, 
                                           font=("Segoe UI", 9), wraplength=250, 
                                           justify="left", padx=8, pady=6, anchor="nw")
        self.folder_summary_lbl.pack(fill="x", pady=(0,4))
        
        self.factory.create_button(parent, "Manage Folders", self.commands.get("manage_folders"), style="secondary").pack(fill="x", pady=2)
        
        tk.Frame(parent, bg=self.theme.bg, height=10).pack()
        
        self.factory.create_section_header(parent, "Webhooks").pack(fill="x")

        self.webhook_summary_lbl = tk.Label(parent, text="No webhooks configured",
                                            bg=self.theme.bg2, fg=self.theme.fg,
                                            font=("Segoe UI", 9), wraplength=250,
                                            justify="left", padx=8, pady=6, anchor="nw")
        self.webhook_summary_lbl.pack(fill="x", pady=(0,4))
        
        self.factory.create_button(parent, "Manage Webhooks", self.commands.get("manage_webhooks"), style="secondary").pack(fill="x", pady=2)
        
        tk.Frame(parent, bg=self.theme.bg, height=10).pack()
        self.factory.create_button(parent, "Settings", lambda: None, style="secondary").pack(fill="x", pady=2)
        self.factory.create_button(parent, "Statistics", lambda: None, style="secondary").pack(fill="x", pady=2)
        
        tk.Frame(parent, bg=self.theme.bg, height=10).pack()
        self.start_btn = self.factory.create_button(parent, "Start Monitoring", self.commands.get("start"))
        self.start_btn.pack(fill="x", pady=3)

    def _build_activity_log(self, parent):
        # 1. Header with Title and Clear Button
        header = tk.Frame(parent, bg=self.theme.bg)
        header.pack(fill="x", pady=(0, 6))
        
        self.factory.create_label(header, "ACTIVITY LOG", color=self.theme.fg2).pack(side="left")
        self.factory.create_button(header, "Clear", self._clear_log, style="secondary").pack(side="right")

        # 2. Quick Stats Bar (The Pills)
        stats_bar = tk.Frame(parent, bg=self.theme.bg2, pady=6)
        stats_bar.pack(fill="x", pady=(0, 6))
        
        # We store references to update them later
        self.stat_sent = self._create_stat_pill(stats_bar, "0", "Sent")
        self.stat_fail = self._create_stat_pill(stats_bar, "0", "Failed")
        self.stat_hooks = self._create_stat_pill(stats_bar, "0", "Webhooks")
        self.stat_dirs = self._create_stat_pill(stats_bar, "0", "Folders")

        # 3. The Log Text Box
        log_wrap = tk.Frame(parent, bg=self.theme.bg3, 
                            highlightthickness=1, highlightbackground=self.theme.border)
        log_wrap.pack(fill="both", expand=True)

        self.log_box = tk.Text(log_wrap, bg=self.theme.bg3, fg=self.theme.fg,
                               insertbackground=self.theme.accent, relief="flat", bd=0,
                               font=("Consolas", 9), wrap="word", state="disabled")
        self.log_box.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        # Scrollbar for the log
        from tkinter import ttk
        sb = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log_box.yview)
        sb.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=sb.set)

        # Configure color tags for the log
        self._setup_log_tags()

    def _create_stat_pill(self, parent, value, label):
        """Helper to create the stat pills (Value on top, Label below)."""
        container = tk.Frame(parent, bg=self.theme.bg2)
        container.pack(side="left", padx=14)
        
        val_lbl = tk.Label(container, text=value, bg=self.theme.bg2, 
                           fg=self.theme.accent, font=("Segoe UI", 16, "bold"))
        val_lbl.pack()
        
        tk.Label(container, text=label.upper(), bg=self.theme.bg2, 
                 fg=self.theme.fg2, font=("Segoe UI", 8)).pack()
        
        return val_lbl

    def _setup_log_tags(self):
        """Pre-configures text tags for coloring log levels."""
        tags = {
            "ok": self.theme.accent2,
            "err": self.theme.danger,
            "warn": self.theme.warning,
            "info": self.theme.accent,
            "debug": self.theme.fg2,
            "ts": self.theme.fg2
        }
        for tag, color in tags.items():
            self.log_box.tag_config(tag, foreground=color)

    def _clear_log(self):
        """Clears all text from the log box."""
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def append_log(self, message: str, level: str = "info"):
        """Appends a new message to the log box with a timestamp."""
        import time
        timestamp = time.strftime("%H:%M:%S")
        
        icons = {"ok": "✓", "err": "✕", "warn": "!", "info": "·", "debug": ">"}
        icon = icons.get(level, "·")

        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{timestamp}] ", "ts")
        self.log_box.insert("end", f"{icon} {message}\n", level)
        self.log_box.see("end")
        self.log_box.config(state="disabled")