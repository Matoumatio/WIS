import tkinter as tk
from tkinter import ttk, messagebox
from ui.components.factory import WidgetFactory
from ui.components.tree_panel import TreePanel
from ui.components.charts import BarChart

class StatsDashboard(tk.Toplevel):
    def __init__(self, parent, stats_manager, theme):
        super().__init__(parent)
        self.title("Statistics")
        self.geometry("860x640")
        self.configure(bg=theme.bg)
        self.grab_set()
        
        self.stats = stats_manager
        self.theme = theme
        self.factory = WidgetFactory(theme)
        
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg=self.theme.bg2)
        header.pack(fill="x", side="top")
        self.factory.create_label(header, "Statistics Dashboard", is_header=True).pack(side="left", padx=15, pady=10)
        
        style = ttk.Style()
        style.configure("TNotebook", background=self.theme.bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.theme.bg3, foreground=self.theme.fg2, padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", self.theme.bg2)], foreground=[("selected", self.theme.accent)])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_overview = tk.Frame(self.nb, bg=self.theme.bg)
        self.tab_recent = tk.Frame(self.nb, bg=self.theme.bg)
        
        self.nb.add(self.tab_overview, text=" Overview ")
        self.nb.add(self.tab_recent, text=" Recent History ")

        self._setup_overview_tab()
        self._setup_recent_tab()

        # 3. Footer
        footer = tk.Frame(self, bg=self.theme.bg)
        footer.pack(fill="x", side="bottom", padx=12, pady=12)
        
        self.factory.create_button(footer, "Refresh Data", self._refresh_all, style="secondary").pack(side="left")
        self.factory.create_button(footer, "Close", self.destroy).pack(side="right")

    def _setup_overview_tab(self):
        # Resumen rápido (Pills)
        summary_frame = tk.Frame(self.tab_overview, bg=self.theme.bg2, pady=10)
        summary_frame.pack(fill="x", padx=5, pady=5)
        
        total = len(self.stats.sends)
        ok = sum(1 for s in self.stats.sends if s.get("ok"))
        rate = f"{(ok/total*100):.1f}%" if total > 0 else "0%"
        
        for val, lbl, color in [(str(total), "TOTAL SENT", self.theme.accent), 
                                (rate, "SUCCESS RATE", self.theme.warning),
                                (str(len(self.stats.errors)), "ERRORS", self.theme.danger)]:
            f = tk.Frame(summary_frame, bg=self.theme.bg2)
            f.pack(side="left", expand=True)
            tk.Label(f, text=val, fg=color, bg=self.theme.bg2, font=("Segoe UI", 16, "bold")).pack()
            tk.Label(f, text=lbl, fg=self.theme.fg2, bg=self.theme.bg2, font=("Segoe UI", 7, "bold")).pack()

        self.factory.create_section_header(self.tab_overview, "Monthly Volume").pack(fill="x", pady=(10, 0))
        
        monthly_data = self.stats.get_monthly_data(12)
        self.month_chart = BarChart(self.tab_overview, self.theme, monthly_data, height=200)
        self.month_chart.pack(fill="both", expand=True, padx=5, pady=5)

    def _setup_recent_tab(self):
        self.factory.create_section_header(self.tab_recent, "Last 500 Activities").pack(fill="x")
        
        self.recent_table = TreePanel(
            self.tab_recent,
            columns=("time", "file", "webhook", "status"),
            headings=("Time", "File Name", "Webhook", "Status"),
            widths=(80, 250, 150, 80),
            theme=self.theme,
            height=15
        )
        self.recent_table.pack(fill="both", expand=True, pady=5)
        self._fill_recent_table()

    def _fill_recent_table(self):
        self.recent_table.clear()
        for i, s in enumerate(reversed(self.stats.sends[-500:])):
            status = "âœ“ OK" if s.get("ok") else "âœ— FAIL"
            self.recent_table.insert(i, (s.get("time"), s.get("file"), s.get("webhook"), status))

    def _refresh_all(self):
        self.stats.load()
        self.month_chart.update_data(self.stats.get_monthly_data(12))
        self._fill_recent_table()
        messagebox.showinfo("Stats", "Data refreshed from disk.")