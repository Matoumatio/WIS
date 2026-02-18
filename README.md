# WIS — Webhook Image Sender

A lightweight desktop app that monitors a folder for new images and automatically sends them to a webhook URL

## Features

- **Folder monitoring** — watches a chosen directory for newly added image files
- **Automatic webhook delivery** — sends new images via HTTP POST as soon as they appear
- **Auto-start** — optionally begin monitoring immediately on launch
- **Persistent settings** — folder path, webhook URL, and preferences are saved between sessions
- **Debug mode** — verbose logging to help troubleshoot detection and sending issues
- **Supported formats** — `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`

## Requirements

- Python 3.7+
- `requests` library

Install dependencies :

```bash
pip install requests
```

> `tkinter` is included with most standard Python installations. If it's missing, install it via your system package manager (e.g. `sudo apt install python3-tk` on Debian/Ubuntu)

## Usage

```bash
python WIS.py
```

1. Click **Browse** to select the folder you want to monitor
2. Enter your **Webhook URL** in the provided field
3. Optionally check **Auto-start monitoring when opening the app**
4. Click **Start Monitoring**

WIS will scan the folder every second. Any image file added after monitoring begins will be sent to the webhook automatically. Files that existed in the folder before monitoring started are ignored

## Settings

Settings are saved automatically to `webhook_settings.json` in the same directory as `WIS.py`. This file stores :

- `folder_path` — last used folder
- `webhook_url` — last used webhook URL
- `auto_start` — whether to start monitoring on launch

## How It Works

When monitoring starts, WIS takes a snapshot of all existing image files in the folder and marks them as already sent. It then polls the folder once per second. When a new image file appears, it waits one second to ensure the file is fully written, verifies the file is non-empty, and then POSTs it to the webhook as `multipart/form-data`

A success is recorded for HTTP responses `200`, `201`, or `204`. Any other status code or network error is logged in the UI

## Notes

- Only files placed directly in the monitored folder are detected — subdirectories are not scanned recursively
- The sent-files list resets each time you stop and restart monitoring
- Webhook endpoints must accept `multipart/form-data` file uploads
