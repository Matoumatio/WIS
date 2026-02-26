import tkinter as tk
from tkinter import ttk
from models.theme import ThemeModel

class ThemeManager:
    """Handles the application of colors and styles to the Tkinter enviroment."""

    @staticmethod
    def lighten_color(hex_color: str, amount: int = 25) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return "#{:02x}{:02x}{:02x}".format(
            min(255, r + amount), min(255, g + amount), min(255, b + amount),
        )
    
    @classmethod
    def apply_ttk_styles(cls, theme: ThemeModel):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview", 
                        background=theme.bg2, 
                        foreground=theme.fg,
                        fieldbackground=theme.bg2, 
                        rowheight=26, 
                        font=("Segoe UI", 9))
        
        style.configure("Treeview.Heading", 
                        background=theme.bg3, 
                        foreground=theme.accent,
                        font=("Segoe UI", 9, "bold"), 
                        relief="flat")
        
        style.map("Treeview",
                  background=[("selected", theme.bg3)],
                  foreground=[("selected", theme.accent)])

        # Scrollbar Styling
        style.configure("Vertical.TScrollbar", 
                        background=theme.bg3,
                        troughcolor=theme.bg2, 
                        arrowcolor=theme.fg2)
    
    @classmethod
    def update_widget_theme(cls, widget, theme: ThemeModel):
        if hasattr(widget, 'theme_roles'):
            update_map = {}
            for tk_prop, theme_key in widget.theme_roles.items():
                color = getattr(theme, theme_key)
                update_map[tk_prop] = color
            
            
            widget.configure(**update_map)

            if isinstance(widget, tk.Button) and "bg" in widget.theme_roles:
                    hover = cls.lighten_color(getattr(theme, widget.theme_roles["bg"]))
                    widget.configure(activebackground=hover)
    
    @classmethod
    def apply_theme_recursive(cls, container, theme: ThemeModel):
        if isinstance(container, (tk.Frame, tk.LabelFrame, tk.Tk, tk.Toplevel)):
            role_bg = getattr(container, "theme_roles", {}).get("bg", "bg")
            container.configure(bg=getattr(theme, role_bg))
        
        for child in container.winfo_children():
            cls.update_widget_theme(child, theme)
            cls.apply_theme_recursive(child, theme)

