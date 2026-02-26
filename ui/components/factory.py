import tkinter as tk
from ui.styles.theme_manager import ThemeManager
from models.theme import ThemeModel

class WidgetFactory:
    """
    Factory class to create styled widgets based on the current application theme
    """

    def __init__(self, theme: ThemeModel):
        self.theme = theme
    
    def create_label(self, parent, text, is_header=False, color=None):
        fg = color or (self.theme.accent if is_header else self.theme.fg)
        font = ("Segoe UI", 9, "bold") if is_header else ("Segoe UI", 9)
        return tk.Label(parent, text=text, bg=parent["bg"], fg=fg, font=font)

    def create_button(self, parent, text, command, style="primary"):
        """Creates a styled flat button with hover effects."""
        bg_color = self.theme.accent if style == "primary" else self.theme.bg3
        fg_color = self.theme.bg if style == "primary" else self.theme.accent
        
        if style == "danger":
            bg_color = self.theme.danger
            fg_color = "white"

        hover_color = ThemeManager.lighten_color(bg_color)

        btn = tk.Button(parent, text=text, command=command, 
                        bg=bg_color, fg=fg_color,
                        activebackground=hover_color, activeforeground=fg_color,
                        relief="flat", bd=0, padx=12, pady=5,
                        font=("Segoe UI", 9, "bold"), cursor="hand2")

        btn.bind("<Enter>", lambda e: btn.config(bg=hover_color))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg_color))
        return btn
    
    def create_entry(self, parent, textvariable=None, width=40):
         """Creates a styled text entry with a custom border color."""
         return tk.Entry(parent, textvariable=textvariable, width=width,
                        bg=self.theme.bg3, fg=self.theme.fg, 
                        insertbackground=self.theme.accent,
                        relief="flat", bd=0, font=("Segoe UI", 9),
                        highlightthickness=1, 
                        highlightbackground=self.theme.border,
                        highlightcolor=self.theme.accent)

    def create_section_header(self, parent, text):
        """Creates a small uppercase header with a separator line below it."""
        container = tk.Frame(parent, bg=parent["bg"])
        tk.Label(container, text=text.upper(), bg=parent["bg"], 
                 fg=self.theme.fg2, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        
        tk.Frame(container, bg=self.theme.border, height=1).pack(fill="x", pady=3)
        
        return container