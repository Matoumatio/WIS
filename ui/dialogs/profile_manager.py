import tkinter as tk
from tkinter import messagebox
from typing import List, Callable
from models.webhook import SharedProfileModel
from models.theme import ThemeModel
from ui.components.factory import WidgetFactory
from ui.components.tree_panel import TreePanel

class ProfileManager(tk.Toplevel):
    """Dialog to manage shared identity profiles (username + avatar)"""
    def __init__(self, parent, profiles: List[SharedProfileModel], theme: ThemeModel, on_save: Callable):
        super().__init__(parent)
        self.title("Shared Profiles")
        self.configure(bg=theme.bg)
        self.geometry("580x540")
        self.resizable(False, False)
        self.grab_set()

        self.theme = theme
        self.factory = WidgetFactory(theme)
        self.profiles = [SharedProfileModel(p.name, p.username, p.avatar_url) for p in profiles]
        self.on_save = on_save
        self._edit_idx = None

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=self.theme.bg2)
        header.pack(fill="x", side="top")
        self.factory.create_label(header, "Shared Profiles", is_header=True).pack(side="left", padx=14, pady=10)

        body = tk.Frame(self, bg=self.theme.bg)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # List
        self.panel = TreePanel(body, 
                               columns=("name", "username", "avatar"),
                               headings=("Profile Name", "Display Name", "Avatar URL"),
                               widths=(130, 130, 260), theme=self.theme, height=6)
        self.panel.pack(fill="x")

        # Actions
        actions = tk.Frame(body, bg=self.theme.bg)
        actions.pack(fill="x", pady=4)
        self.factory.create_button(actions, "Edit", self._load_to_edit, style="secondary").pack(side="left", padx=(0, 4))
        self.factory.create_button(actions, "Remove", self._remove, style="danger").pack(side="left", padx=4)

        # Form
        self.factory.create_section_header(body, "Add / Edit Profile").pack(fill="x", pady=(10, 5))
        
        self.name_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.avatar_var = tk.StringVar()

        for label, var in [("Profile Name:", self.name_var), 
                           ("Username:", self.user_var), 
                           ("Avatar URL:", self.avatar_var)]:
            row = tk.Frame(body, bg=self.theme.bg)
            row.pack(fill="x", pady=2)
            lbl = self.factory.create_label(row, label, color=self.theme.fg2)
            lbl.configure(width=12, anchor="w")
            lbl.pack(side="left")
            self.factory.create_entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        self.commit_btn = self.factory.create_button(body, "+ Add Profile", self._commit)
        self.commit_btn.pack(pady=10)

        # Footer
        footer = tk.Frame(self, bg=self.theme.bg)
        footer.pack(fill="x", side="bottom", padx=12, pady=12)
        self.factory.create_button(footer, "Save & Close", self._save).pack(side="right")

    def _refresh_list(self):
        self.panel.clear()
        for i, p in enumerate(self.profiles):
            self.panel.insert(i, (p.name, p.username, p.avatar_url))

    def _load_to_edit(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            p = self.profiles[idx]
            self.name_var.set(p.name)
            self.user_var.set(p.username)
            self.avatar_var.set(p.avatar_url)
            self._edit_idx = idx
            self.commit_btn.config(text="Update Profile")

    def _commit(self):
        name = self.name_var.get().strip()
        user = self.user_var.get().strip()
        if not name or not user: return

        new_p = SharedProfileModel(name, user, self.avatar_var.get().strip())
        
        if self._edit_idx is not None:
            self.profiles[self._edit_idx] = new_p
            self._edit_idx = None
            self.commit_btn.config(text="+ Add Profile")
        else:
            self.profiles.append(new_p)
            
        self.name_var.set(""); self.user_var.set(""); self.avatar_var.set("")
        self._refresh_list()

    def _remove(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            del self.profiles[idx]
            self._refresh_list()

    def _save(self):
        self.on_save(self.profiles)
        self.destroy()