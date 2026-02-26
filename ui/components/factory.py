import tkinter as tk
from ui.styles.theme_manager import ThemeManager
from models.theme import ThemeModel

class WidgetFactory:
    """
    Factory class to create styled widgets based on the current application theme
    """

    def __init__(self, theme: ThemeModel):
        self.theme = theme
    
    def _tag_widget(self, widget, **roles):
        widget.theme_roles = roles
        return widget
    
    def create_label(self, parent, text, is_header=False, color=None):
        fg_role = "accent" if is_header else "fg"
        if color:
            fg_role = "fg"
        font = ("Segoe UI", 9, "bold") if is_header else ("Segoe UI", 9)
        lbl = tk.Label(parent, text=text, bg=parent["bg"], fg=getattr(self.theme, fg_role), font=font)

        return self._tag_widget(lbl, fg=fg_role)

    def create_button(self, parent, text, command, style="primary"):
        """Creates a styled flat button with hover effects."""
        bg_role = "accent" if style == "primary" else "bg3"
        fg_role = "bg" if style == "primary" else "accent"
        
        if style == "danger":
            bg_role, fg_role = "danger", "fg"

        bg_color = getattr(self.theme, bg_role)
        fg_color = getattr(self.theme, fg_role)
        
        hover_color = ThemeManager.lighten_color(bg_color)

        btn = tk.Button(parent, text=text, command=command, 
                        bg=bg_color, 
                        fg=fg_color,
                        activebackground=hover_color,
                        activeforeground=fg_color,
                        relief="flat", bd=0, padx=12, pady=5,
                        font=("Segoe UI", 9, "bold"), cursor="hand2")

        btn.bind("<Enter>", lambda e: btn.config(
            bg=ThemeManager.lighten_color(getattr(self.theme, bg_role))
        ))
        btn.bind("<Leave>", lambda e: btn.config(
            bg=getattr(self.theme, bg_role)
        ))

        return self._tag_widget(btn, bg=bg_role, fg=fg_role)
    
    def create_entry(self, parent, textvariable=None, width=40):
         """Creates a styled text entry with a custom border color."""
         entry = tk.Entry(parent, textvariable=textvariable, width=width,
                        bg=self.theme.bg3, fg=self.theme.fg, 
                        insertbackground=self.theme.accent,
                        relief="flat", bd=0, font=("Segoe UI", 9),
                        highlightthickness=1, 
                        highlightbackground=self.theme.border,
                        highlightcolor=self.theme.accent)
         
         return self._tag_widget(entry, bg="bg3", fg="fg",insertbackground="accent", 
                                highlightbackground="border", highlightcolor="accent")

    def create_section_header(self, parent, text):
        """Creates a small uppercase header with a separator line below it."""
        container = tk.Frame(parent, bg=parent["bg"])
        self._tag_widget(container, bg="bg")
        
        lbl = tk.Label(container, text=text.upper(), bg=parent["bg"], 
                 fg=self.theme.fg2, font=("Segoe UI", 7, "bold"))
        lbl.pack(anchor="w")
        self._tag_widget(lbl, bg="bg", fg="fg2")
        
        line = tk.Frame(container, bg=self.theme.border, height=1)
        line.pack(fill="x", pady=3)
        self._tag_widget(line, bg="border")
        
        return container
    
    def create_checkbox(self, parent, text, variable, command=None):
        """Creates a styled checkbox."""
        cb = tk.Checkbutton(parent, text=text, variable=variable, command=command,
                            bg=parent["bg"], fg=self.theme.fg, 
                            selectcolor=self.theme.bg3, activebackground=parent["bg"],
                            activeforeground=self.theme.fg, font=("Segoe UI", 9),
                            highlightthickness=0, bd=0)
        return self._tag_widget(cb, bg="bg", fg="fg", 
                                selectcolor="bg3", activebackground="bg", activeforeground="fg")

    def create_color_swatch(self, parent, color_hex):
        """Creates a small square showing a color."""
        frame = tk.Frame(parent, width=18, height=18, bg=color_hex, 
                         relief="flat", highlightthickness=1, 
                         highlightbackground=self.theme.border)
        frame.pack_propagate(False)
        
        return self._tag_widget(frame, highlightbackground="border")