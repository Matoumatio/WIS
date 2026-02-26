import tkinter as tk
from models.theme import ThemeModel

class BarChart(tk.Canvas):
    def __init__(self, parent, theme: ThemeModel, data: list, color_key="accent", **kwargs):
        super().__init__(parent, bg=theme.bg2, highlightthickness=0, **kwargs)
        self.theme = theme
        self.data = data
        self.color = getattr(theme, color_key)
        self.bind("<Configure>", lambda e: self.draw())

    def update_data(self, data: list):
        self.data = data
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        
        if not self.data or w < 50 or h < 50:
            self.create_text(w//2, h//2, text="No data available", fill=self.theme.fg2)
            return

        pad_l, pad_r, pad_t, pad_b = 45, 15, 25, 45
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b
        
        max_val = max((v for _, v in self.data), default=1) or 1
        n = len(self.data)
        gap = 6
        bar_w = max(4, (chart_w - gap * (n + 1)) // n)
        
        self.create_line(pad_l, pad_t, pad_l, pad_t + chart_h, fill=self.theme.border) # Eje Y
        self.create_line(pad_l, pad_t + chart_h, pad_l + chart_w, pad_t + chart_h, fill=self.theme.border) # Eje X

        for i in range(5):
            y = pad_t + chart_h - int(chart_h * i / 4)
            val = round(max_val * i / 4)
            self.create_line(pad_l - 3, y, pad_l + chart_w, y, fill=self.theme.border, dash=(2, 4))
            self.create_text(pad_l - 8, y, text=str(val), fill=self.theme.fg2, font=("Segoe UI", 7), anchor="e")

        start_x = pad_l + gap
        for i, (label, value) in enumerate(self.data):
            x0 = start_x + i * (bar_w + gap)
            x1 = x0 + bar_w
            
            bar_h = int(chart_h * value / max_val)
            y0 = pad_t + chart_h - bar_h
            y1 = pad_t + chart_h
            
            self.create_rectangle(x0 + 2, y0 + 2, x1 + 2, y1 + 2, fill=self.theme.bg, outline="")
            self.create_rectangle(x0, y0, x1, y1, fill=self.color, outline="")
            
            if bar_h > 15:
                self.create_text((x0+x1)//2, y0 + 8, text=str(value), fill=self.theme.bg, font=("Segoe UI", 7, "bold"))
            else:
                self.create_text((x0+x1)//2, y0 - 8, text=str(value), fill=self.theme.fg, font=("Segoe UI", 7))

            short_label = label if len(label) < 10 else label[:8] + ".."
            self.create_text((x0+x1)//2, y1 + 12, text=short_label, fill=self.theme.fg2, font=("Segoe UI", 7), anchor="n")