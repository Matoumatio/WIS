import tkinter as tk
from tkinter import ttk
from models.theme import ThemeModel

class TreePanel(tk.Frame):
    """
    A reusable frame containing a themed ttk. Treeview with a vertical scrollbar.
    """

    def __init__(self, parent, columns, headings, widths, theme: ThemeModel, height=7):
        super().__init__(parent, bg=theme.bg)

        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                 height=height, selectmode="browse")

        # Configure columns
        for col, hd, w in zip(columns, headings, widths):
            self.tree.heading(col, text=hd)
            self.tree.column(col, width=w, 
                             anchor="center" if w <= 60 else "w",
                             stretch=(col == columns[-1]))
            
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
    
    def selected_idx(self) -> int:
        """Returns the index of the currently selected row."""
        selection = self.tree.selection()
        return int(selection[0]) if selection else None
    
    def clear(self):
        """Removes all items from the tree."""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def insert(self, iid, values):
        """Inserts a new row."""
        self.tree.insert("", "end", iid=str(iid), values=values)