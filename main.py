import sys
import tkinter as tk
from core.app import WISApplication

def main():
    root = tk.Tk()

    app = WISApplication(root)

    try:
        app.initialize()
        app.run()
    
    except Exception as e:
        print(f"Fatal error booting WIS: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
