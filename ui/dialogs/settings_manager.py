import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Callable
from models.theme import ThemeModel
from ui.components.factory import WidgetFactory
from ui.styles.theme_manager import ThemeManager

class SettingsManager(tk.Toplevel):
    """
    Dialog to manage appliacation behaviour, sounds, statistics, and themes.
    """

    def __init__(self, parent, config_manager, theme: ThemeModel, on_save: Callable):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=theme.bg)
        self.geometry("560x720")
        self.resizable(False, False)
        self.grab_set()
        self.config = config_manager

        self.theme = theme
        self.factory = WidgetFactory(theme)
        self.on_save = on_save
        
        self.themes_dict = self.config.get("themes")
        self.current_theme_name = tk.StringVar(value=self.config.get("theme_active", "Dark Blue"))

        self.vars: Dict[str, tk.Variable] = {}
        self.swatches: Dict[str, tk.Frame] = {}

        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=self.theme.bg2)
        header.pack(fill="x", side="top")
        self.factory.create_label(header, "Settings", is_header=True).pack(side="left", padx=14, pady=10)

        # Scrollable Area
        container = tk.Frame(self, bg=self.theme.bg)
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(container, bg=self.theme.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=self.theme.bg)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=530)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._fill_settings()

        # Footer
        footer = tk.Frame(self, bg=self.theme.bg)
        footer.pack(fill="x", side="bottom", padx=12, pady=12)
        self.factory.create_button(footer, "Save & Apply", self._save).pack(side="right")
        self.factory.create_button(footer, "Cancel", self.destroy, style="secondary").pack(side="right", padx=8)

    def _fill_settings(self):
        f = self.scrollable_frame

        
        
        # --- Behavior Section ---
        self.factory.create_section_header(f, "Behavior").pack(fill="x", pady=(10, 5))
        self._add_num_input("Scan Rate (seconds):", "scan_rate", 1.0)
        self._add_num_input("Send Timeout (seconds):", "send_timeout", 30)
        self._add_num_input("File Settle Delay:", "file_delay", 0.8)
        
        self.vars["formats"] = tk.StringVar(value=self.config.get("formats"))
        row = tk.Frame(f, bg=f["bg"])
        row.pack(fill="x", pady=2)
        self.factory.create_label(row, "Extensions:").pack(side="left")
        self.factory.create_entry(row, textvariable=self.vars["formats"]).pack(side="right", expand=True, fill="x")

        # --- Sound Section ---
        self.factory.create_section_header(f, "Sound Notifications").pack(fill="x", pady=(10, 5))
        self.vars["sound_enabled"] = tk.BooleanVar(value=self.config.get("sound_enabled"))
        self.factory.create_checkbox(f, "Enable Sound Notifications", self.vars["sound_enabled"]).pack(anchor="w")
        self._add_num_input("Volume (0.0 - 1.0):", "sound_volume", 0.8)

         # --- Theme Selector Section ---

        self.factory.create_section_header(f, "Theme Selection").pack(fill="x", pady=(10, 5))
        
        row_theme = tk.Frame(f, bg=f["bg"])
        row_theme.pack(fill="x", pady=5)
        
        self.factory.create_label(row_theme, "Active Theme:").pack(side="left")
        
        # Dropdown con los nombres de los temas
        theme_names = list(self.themes_dict.keys())
        self.theme_menu = ttk.Combobox(row_theme, textvariable=self.current_theme_name, values=theme_names, state="readonly")
        self.theme_menu.pack(side="right", expand=True, fill="x", padx=10)
        self.theme_menu.bind("<<ComboboxSelected>>", self._on_theme_dropdown_change)

        # --- Theme Editor Section ---
        self.factory.create_section_header(f, "Color Editor (Live Preview)").pack(fill="x", pady=(10, 5))
        color_grid = tk.Frame(f, bg=f["bg"])
        color_grid.pack(fill="x")

        color_keys = ["bg", "bg2", "bg3", "accent", "accent2", "danger", "warning", "fg", "fg2", "border"]
        for i, key in enumerate(color_keys):
            r, c = divmod(i, 2)
            cell = tk.Frame(color_grid, bg=f["bg"])
            cell.grid(row=r, column=c, sticky="w", padx=5, pady=2)
            
            self.vars[key] = tk.StringVar(value=getattr(self.theme, key))
            lbl = self.factory.create_label(cell, f"{key}:", color=self.theme.fg2)
            lbl.configure(width=8, anchor="w")
            lbl.pack(side="left")
            entry = self.factory.create_entry(cell, textvariable=self.vars[key], width=10)
            entry.pack(side="left")
            
            swatch = self.factory.create_color_swatch(cell, self.vars[key].get())
            swatch.pack(side="left", padx=5)
            self.swatches[key] = swatch
            
            # Live Preview binding
            self.vars[key].trace_add("write", lambda *args, k=key: self._update_swatch(k))

        self.factory.create_label(row_theme, "Save as:").pack(side="left", padx=(10, 0))
        self.new_theme_name_var = tk.StringVar(value="")
        self.factory.create_entry(row_theme, textvariable=self.new_theme_name_var, width=15).pack(side="left")

    def _add_num_input(self, label, key, default):
        row = tk.Frame(self.scrollable_frame, bg=self.scrollable_frame["bg"])
        row.pack(fill="x", pady=2)
        self.factory.create_label(row, label).pack(side="left")
        self.vars[key] = tk.StringVar(value=str(self.config.get(key, default)))
        self.factory.create_entry(row, textvariable=self.vars[key], width=10).pack(side="right")
    
    def _on_theme_dropdown_change(self, event):
        """When a theme is selected from dropdown, update hex entries."""
        selected_name = self.current_theme_name.get()
        selected_colors = self.themes_dict.get(selected_name)
        
        if selected_colors:
            for key, value in selected_colors.items():
                if key in self.vars:
                    self.vars[key].set(value)
    
    def _on_preset_change(self, event):
        """Actualiza los campos de texto de colores al elegir un preset del combo."""
        selected_name = self.active_name_var.get()
        colors = self.themes_dict.get(selected_name)
        if colors:
            for key, val in colors.items():
                if key in self.vars:
                    self.vars[key].set(val)

    def _update_swatch(self, key):
        val = self.vars[key].get()
        if len(val) == 7 and val.startswith("#"):
            try: self.swatches[key].config(bg=val)
            except: pass

    def _save(self):
        
        color_keys = ["bg", "bg2", "bg3", "accent", "accent2", "danger", "warning", "fg", "fg2", "border"]
        current_editor_colors = {k: self.vars[k].get() for k in color_keys}

        active_name = self.current_theme_name.get()
        new_name_theme = self.new_theme_name_var.get().strip()
        presets_protected = ["Dark Blue"] 

        if new_name_theme:
            self.themes_dict[new_name_theme] = current_editor_colors
            self.config.set("theme_active", new_name_theme)

        elif active_name in presets_protected:
            original_colors = self.themes_dict.get(active_name)
            
            if current_editor_colors != original_colors:
                self.themes_dict["Custom"] = current_editor_colors
                self.config.set("theme_active", "Custom")
            else:
                self.config.set("theme_active", active_name)
        else:
            self.themes_dict[active_name] = current_editor_colors
            self.config.set("theme_active", active_name)

        self.config.set("themes", self.themes_dict)

        # Update config manager
        for key, var in self.vars.items():
            val = var.get()
            # Basic type conversion
            if isinstance(self.config.defaults.get(key), float):
                try: val = float(val)
                except: val = self.config.defaults.get(key)
            elif isinstance(self.config.defaults.get(key), bool):
                val = bool(val)
            
            self.config.set(key, val)
        
        self.config.save()
        self.on_save()
        self.destroy()