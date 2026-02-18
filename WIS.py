import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import os
import time
import requests
import json
from pathlib import Path
from threading import Thread
import mimetypes

class WebhookImageSender:
    def __init__(self, root):
        self.root = root
        self.root.title("Webhook Image Sender")
        self.root.geometry("600x540")
        
        # Settings file path
        self.settings_file = os.path.join(os.path.dirname(__file__), 'webhook_settings.json')
        
        # Variables
        self.folder_path = tk.StringVar()
        self.webhook_url = tk.StringVar()
        self.auto_start = tk.BooleanVar()
        self.is_monitoring = False
        self.monitoring_thread = None
        self.sent_files = set()
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        # Load saved settings
        self.load_settings()
        
        self.create_widgets()
        
        # Auto-start if enabled
        if self.auto_start.get() and self.folder_path.get() and self.webhook_url.get():
            self.root.after(1000, self.start_monitoring)  # Start after 1 second
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Folder selection
        ttk.Label(main_frame, text="Folder to Monitor:").grid(row=0, column=0, sticky=tk.W, pady=5)
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT, padx=5)
        
        # Webhook URL
        ttk.Label(main_frame, text="Webhook URL:").grid(row=2, column=0, sticky=tk.W, pady=5)
        webhook_entry = ttk.Entry(main_frame, textvariable=self.webhook_url, width=60)
        webhook_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        webhook_entry.bind('<FocusOut>', lambda e: self.save_settings())
        
        # Auto-start checkbox
        auto_start_check = ttk.Checkbutton(main_frame, text="Auto-start monitoring when opening the app", 
                                           variable=self.auto_start, command=self.save_settings)
        auto_start_check.grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # Debug checkbox
        self.debug_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(button_frame, text="Debug Mode", variable=self.debug_mode).pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Status: Idle", foreground="blue")
        self.status_label.grid(row=6, column=0, sticky=tk.W, pady=5)
        
        # Log area
        ttk.Label(main_frame, text="Log:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.log_text = scrolledtext.ScrolledText(main_frame, width=70, height=15, wrap=tk.WORD)
        self.log_text.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(8, weight=1)
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.log(f"Selected folder: {folder}")
            self.save_settings()
    
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.folder_path.set(settings.get('folder_path', ''))
                    self.webhook_url.set(settings.get('webhook_url', ''))
                    self.auto_start.set(settings.get('auto_start', False))
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to JSON file"""
        try:
            settings = {
                'folder_path': self.folder_path.get(),
                'webhook_url': self.webhook_url.get(),
                'auto_start': self.auto_start.get()
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        
    def start_monitoring(self):
        if not self.folder_path.get():
            self.log("ERROR: Please select a folder to monitor")
            return
            
        if not self.webhook_url.get():
            self.log("ERROR: Please enter a webhook URL")
            return
            
        if not os.path.exists(self.folder_path.get()):
            self.log("ERROR: Selected folder does not exist")
            return
            
        self.is_monitoring = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Status: Monitoring...", foreground="green")
        
        # Initialize sent_files with existing files
        self.initialize_existing_files()
        
        # Start monitoring thread
        self.monitoring_thread = Thread(target=self.monitor_folder, daemon=True)
        self.monitoring_thread.start()
        
        if self.auto_start.get():
            self.log("Auto-started monitoring folder for new images/GIFs")
        else:
            self.log("Started monitoring folder for new images/GIFs")
        
    def stop_monitoring(self):
        self.is_monitoring = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Stopped", foreground="red")
        self.log("Stopped monitoring")
        
    def initialize_existing_files(self):
        """Mark all existing files as already sent to avoid sending them on startup"""
        folder = self.folder_path.get()
        try:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.supported_formats:
                        # Store absolute path
                        abs_path = os.path.abspath(file_path)
                        self.sent_files.add(abs_path)
            self.log(f"Found {len(self.sent_files)} existing images (will not send these)")
        except Exception as e:
            self.log(f"Error initializing files: {str(e)}")
        
    def monitor_folder(self):
        folder = self.folder_path.get()
        self.log(f"Monitoring: {folder}")
        scan_count = 0
        
        while self.is_monitoring:
            try:
                scan_count += 1
                
                # Debug logging
                if self.debug_mode.get():
                    self.log(f"[Debug] Scan #{scan_count}")
                
                # Get all current image files
                current_files = []
                
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    
                    # Check if it's a file (not directory)
                    if not os.path.isfile(file_path):
                        continue
                    
                    # Check extension
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in self.supported_formats:
                        continue
                    
                    # Use absolute path for consistency
                    abs_path = os.path.abspath(file_path)
                    current_files.append(abs_path)
                    
                    # Debug: show all found files
                    if self.debug_mode.get():
                        status = "SENT" if abs_path in self.sent_files else "NEW"
                        self.log(f"[Debug] Found: {file} [{status}]")
                    
                    # Check if this is a new file
                    if abs_path not in self.sent_files:
                        self.log(f"New file detected: {file}")
                        # Wait a bit to ensure file is fully written
                        time.sleep(1)
                        
                        # Verify file still exists and is readable
                        if os.path.exists(abs_path):
                            try:
                                # Try to get file size to ensure it's complete
                                size = os.path.getsize(abs_path)
                                if size > 0:
                                    self.send_file(abs_path)
                                    self.sent_files.add(abs_path)
                                else:
                                    self.log(f"Skipping {file} - file is empty")
                            except Exception as e:
                                self.log(f"Error accessing {file}: {str(e)}")
                    
            except Exception as e:
                self.log(f"ERROR monitoring folder: {str(e)}")
                
            time.sleep(1)  # Check every 1 second
            
    def send_file(self, file_path):
        try:
            filename = os.path.basename(file_path)
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, mime_type)}
                
                response = requests.post(
                    self.webhook_url.get(),
                    files=files,
                    timeout=30
                )
                
                if response.status_code in [200, 201, 204]:
                    self.log(f"✓ Successfully sent: {filename}")
                else:
                    self.log(f"✗ Failed to send {filename}: HTTP {response.status_code}")
                    
        except requests.exceptions.RequestException as e:
            self.log(f"✗ Network error sending {filename}: {str(e)}")
        except Exception as e:
            self.log(f"✗ Error sending {filename}: {str(e)}")

def main():
    root = tk.Tk()
    app = WebhookImageSender(root)
    root.mainloop()

if __name__ == "__main__":
    main()