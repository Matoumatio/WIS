import tkinter as tk
from tkinter import messagebox
from typing import List, Callable
from models.webhook import WebhookModel, SharedProfileModel
from models.theme import ThemeModel
from ui.components.factory import WidgetFactory
from ui.components.tree_panel import TreePanel
from ui.dialogs.profile_manager import ProfileManager

class WebhookManager(tk.Toplevel):
    """
    Dialog to manage webhook endpoints and link them to identity profiles.
    """

    def __init__(self, parent, webhooks: List[WebhookModel], profiles: List[SharedProfileModel], 
                 theme: ThemeModel, on_save: Callable, on_profiles_update: Callable):
        super().__init__(parent)
        self.title("Webhook Manager")
        self.configure(bg=theme.bg)
        self.geometry("620x620")
        self.resizable(False, False)
        self.grab_set()

        self.theme = theme
        self.factory = WidgetFactory(theme)
        self.webhooks = [WebhookModel(w.name, w.url, w.is_enabled, w.shared_profile_name) for w in webhooks]
        self.profiles = profiles
        self.on_save = on_save
        self.on_profiles_update = on_profiles_update
        self._edit_idx = None

        self._build_ui()
        self._refresh_list()
    

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=self.theme.bg2)
        header.pack(fill="x", side="top")
        self.factory.create_label(header, "Webhook Manager", is_header=True).pack(side="left", padx=14, pady=10)

        body = tk.Frame(self, bg=self.theme.bg)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # List
        self.panel = TreePanel(body, 
                               columns=("on", "name", "profile", "url"),
                               headings=("On", "Name", "Profile", "URL"),
                               widths=(44, 120, 120, 260), theme=self.theme, height=7)
        self.panel.pack(fill="x")

        # Actions
        actions = tk.Frame(body, bg=self.theme.bg)
        actions.pack(fill="x", pady=4)
        self.factory.create_button(actions, "Edit", self._load_to_edit, style="secondary").pack(side="left", padx=(0, 4))
        self.factory.create_button(actions, "Toggle", self._toggle, style="secondary").pack(side="left", padx=4)
        self.factory.create_button(actions, "Remove", self._remove, style="danger").pack(side="left", padx=4)

        # Form
        self.factory.create_section_header(body, "Add / Edit Webhook").pack(fill="x", pady=(10, 5))
        
        self.name_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.profile_var = tk.StringVar()
        self.use_profile_var = tk.BooleanVar()

        # Name and URL
        for label, var in [("Name:", self.name_var), ("URL:", self.url_var)]:
            row = tk.Frame(body, bg=self.theme.bg)
            row.pack(fill="x", pady=2)
            lbl = self.factory.create_label(row, label, color=self.theme.fg2)
            lbl.configure(width=8, anchor="w")
            lbl.pack(side="left")
            self.factory.create_entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        # Shared Profile Option
        profile_frame = tk.Frame(body, bg=self.theme.bg, pady=5)
        profile_frame.pack(fill="x")
        
        tk.Checkbutton(profile_frame, text="Override Identity", variable=self.use_profile_var,
                       bg=self.theme.bg, fg=self.theme.fg, selectcolor=self.theme.bg3).pack(side="left")
        
        self.profile_menu = tk.OptionMenu(profile_frame, self.profile_var, "")
        self.profile_menu.config(bg=self.theme.bg3, fg=self.theme.fg, relief="flat", bd=0)
        self.profile_menu.pack(side="left", padx=10)
        self._update_profile_dropdown()

        self.factory.create_button(profile_frame, "Manage Profiles", self._open_profiles, style="secondary").pack(side="left")

        self.commit_btn = self.factory.create_button(body, "+ Add Webhook", self._commit)
        self.commit_btn.pack(pady=10)

        # Footer
        footer = tk.Frame(self, bg=self.theme.bg)
        footer.pack(fill="x", side="bottom", padx=12, pady=12)
        self.factory.create_button(footer, "Save & Close", self._save).pack(side="right")

    def _update_profile_dropdown(self):
        menu = self.profile_menu["menu"]
        menu.delete(0, "end")
        names = [p.name for p in self.profiles]
        for name in names:
            menu.add_command(label=name, command=lambda v=name: self.profile_var.set(v))
        if names and not self.profile_var.get():
            self.profile_var.set(names[0])

    def _refresh_list(self):
        self.panel.clear()
        for i, w in enumerate(self.webhooks):
            self.panel.insert(i, (
                "✔" if w.is_enabled else "—",
                w.name,
                w.shared_profile_name or "—",
                w.url
            ))

    def _open_profiles(self):
        def on_profiles_save(updated_profiles):
            self.on_profiles_update(updated_profiles)
            self.profiles = updated_profiles
            self._update_profile_dropdown()
        ProfileManager(self, self.profiles, self.theme, on_profiles_save)

    def _load_to_edit(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            w = self.webhooks[idx]
            self.name_var.set(w.name)
            self.url_var.set(w.url)
            self.use_profile_var.set(bool(w.shared_profile_name))
            if w.shared_profile_name: self.profile_var.set(w.shared_profile_name)
            self._edit_idx = idx
            self.commit_btn.config(text="Update Webhook")

    def _commit(self):
        name = self.name_var.get().strip()
        url = self.url_var.get().strip()
        if not name or not url: return

        profile = self.profile_var.get() if self.use_profile_var.get() else None
        new_w = WebhookModel(name, url, True, profile)

        if self._edit_idx is not None:
            new_w.is_enabled = self.webhooks[self._edit_idx].is_enabled
            self.webhooks[self._edit_idx] = new_w
            self._edit_idx = None
            self.commit_btn.config(text="+ Add Webhook")
        else:
            self.webhooks.append(new_w)
            
        self.name_var.set(""); self.url_var.set("")
        self._refresh_list()

    def _toggle(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            self.webhooks[idx].is_enabled = not self.webhooks[idx].is_enabled
            self._refresh_list()

    def _remove(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            del self.webhooks[idx]
            self._refresh_list()

    def _save(self):
        self.on_save(self.webhooks)
        self.destroy()