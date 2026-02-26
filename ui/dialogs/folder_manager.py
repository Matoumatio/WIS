import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Callable
from models.folder import FolderModel
from models.theme import ThemeModel
from ui.components.factory import WidgetFactory
from ui.components.tree_panel import TreePanel

class FolderManager(tk.Toplevel):
    """
    Popup dialog to manage monitored directories.
    """

    def __init__(self, parent, folders: List[FolderModel], theme: ThemeModel, on_save: Callable):
        super().__init__(parent)
        self.title("Folder Manager")
        self.configure(bg=theme.bg)
        self.geometry("640x540")
        self.resizable(False, False)
        self.grab_set() # Modal dialog

        self.theme = theme
        self.factory = WidgetFactory(theme)
        # Work on a copy to allow "Cancel"
        self.folders = [FolderModel(f.path, f.is_enabled, f.is_recursive) for f in folders]
        self.on_save = on_save

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        # 1. Header
        header = tk.Frame(self, bg=self.theme.bg2)
        header.pack(fill="x", side="top")
        self.factory.create_label(header, "Folder Manager", is_header=True).pack(side="left", padx=14, pady=10)
        
        # 2. Main Body
        body = tk.Frame(self, bg=self.theme.bg)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # Treeview Panel
        self.panel = TreePanel(body, 
                               columns=("on", "rec", "path"),
                               headings=("On", "Rec", "Folder Path"),
                               widths=(44, 44, 440),
                               theme=self.theme)
        self.panel.pack(fill="x")

        # Action Buttons for the list
        actions = tk.Frame(body, bg=self.theme.bg)
        actions.pack(fill="x", pady=(4, 12))
        self.factory.create_button(actions, "Toggle Enable", self._toggle_enabled, style="secondary").pack(side="left", padx=(0, 4))
        self.factory.create_button(actions, "Toggle Recursive", self._toggle_recursive, style="secondary").pack(side="left", padx=4)
        self.factory.create_button(actions, "Remove", self._remove_folder, style="danger").pack(side="left", padx=4)

        # Add New Folder Section
        self.factory.create_section_header(body, "Add New Folder").pack(fill="x")
        
        path_row = tk.Frame(body, bg=self.theme.bg)
        path_row.pack(fill="x", pady=6)
        
        self.path_var = tk.StringVar()
        self.factory.create_button(path_row, "Browse", self._browse_folder, style="secondary").pack(side="right", padx=(6, 0))
        self.factory.create_entry(path_row, textvariable=self.path_var).pack(side="left", fill="x", expand=True)

        self.rec_var = tk.BooleanVar(value=True)

        cb = tk.Checkbutton(body, text="Recursive (include subfolders)", variable=self.rec_var,
                            bg=self.theme.bg, fg=self.theme.fg, selectcolor=self.theme.bg3,
                            activebackground=self.theme.bg, font=("Segoe UI", 9))
        cb.pack(anchor="w", pady=4)

        self.factory.create_button(body, "+ Add Folder", self._add_folder).pack(anchor="w", pady=10)

        # 3. Footer
        footer = tk.Frame(self, bg=self.theme.bg)
        footer.pack(fill="x", side="bottom", padx=12, pady=12)
        self.factory.create_button(footer, "Save & Close", self._save).pack(side="right", padx=(4, 0))
        self.factory.create_button(footer, "Cancel", self.destroy, style="secondary").pack(side="right")

    def _refresh_list(self):
        self.panel.clear()
        for i, folder in enumerate(self.folders):
            self.panel.insert(i, (
                "✔" if folder.is_enabled else "—",
                "✔" if folder.is_recursive else "—",
                folder.path
            ))

    def _browse_folder(self):
        path = filedialog.askdirectory(parent=self)
        if path:
            self.path_var.set(path)

    def _add_folder(self):
        path = self.path_var.get().strip()
        if not path or path in [f.path for f in self.folders]:
            return
        self.folders.append(FolderModel(path=path, is_recursive=self.rec_var.get()))
        self.path_var.set("")
        self._refresh_list()

    def _toggle_enabled(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            self.folders[idx].is_enabled = not self.folders[idx].is_enabled
            self._refresh_list()

    def _toggle_recursive(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            self.folders[idx].is_recursive = not self.folders[idx].is_recursive
            self._refresh_list()

    def _remove_folder(self):
        idx = self.panel.selected_idx()
        if idx is not None:
            del self.folders[idx]
            self._refresh_list()

    def _save(self):
        self.on_save(self.folders)
        self.destroy()