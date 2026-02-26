# WIS — Webhook Image Sender

A desktop app that monitors folders for new images and automatically sends them to one or more webhook URLs

## Features

- **Multiple folders** — monitor any number of directories simultaneously, each with an independent enable toggle and optional recursive subfolder scanning
- **Multiple webhooks** — send every detection to all enabled webhooks at once
- **Statistics dashboard** — track sends per month, per webhook, per folder, file type breakdowns, error analytics, and a full recent-send history
- **Theme system** — 8 built-in color presets, a live color editor with swatch previews, and support for saving, exporting, and importing custom themes
- **Sound notifications** — plays `validation.mp3` on success and `exclamation.mp3` on failure (volume adjustable)
- **Auto-start** — optionally begin monitoring immediately on launch
- **Persistent settings** — all configuration is saved between sessions in `wis_settings.json`
- **Debug mode** — verbose scan logging to help troubleshoot detection issues
- **Supported formats** — `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp` (configurable)

## Requirements

- Python 3.7+
- `requests`
- `pygame` (optional — required for sound notifications)

```bash
pip install requests pygame
```

> `tkinter` is included with most standard Python installations. If missing: `sudo apt install python3-tk` (Debian/Ubuntu)

## Quick Start

The project includes automation scripts to set up the virtual environment and install dependencies automatically:

### Windows:
Simply run `run_wish_windows.bat`. This will create the `.venv`, install requirements, and launch the app without a persistent console window.

### Linux:
```bash
chmod +x run_wish_linux.sh
./run_wish_linux.sh
```

### Manual Setup:
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```


## Usage

```bash
python WIS.pyw
```

1. Click **Manage Folders** to add the directories you want to monitor
2. Click **Manage Webhooks** to add your webhook URLs
3. Click **Start Monitoring**

## Folder Manager

Each folder entry has two toggles:

| Toggle | Effect |
|---|---|
| On/Off | Include or exclude this folder from the current session |
| Recursive | Also scan all subfolders within the directory |

## Webhook Manager

Add as many webhooks as needed. When a new image is detected, WIS sends it to every enabled webhook. Each delivery is logged individually with its success or failure status

## Settings

Click the **Settings** button to configure all options in one place:

### Behaviour

| Setting | Default | Description |
|---|---|---|
| Scan rate | `1.0 s` | How often folders are polled |
| Send timeout | `30 s` | HTTP request timeout per webhook |
| File settle delay | `0.8 s` | Wait after detection before sending |
| Extensions | `.jpg,.jpeg,.png,.gif,.bmp,.webp` | Watched file types |

### Sound Notifications

| Setting | Default | Description |
|---|---|---|
| Sound enabled | On | Play sounds on send success / failure |
| Volume | `0.8` | Sound volume from `0.0` to `1.0` |

### Startup & Debug

| Setting | Default | Description |
|---|---|---|
| Auto-start on launch | Off | Begin monitoring automatically when the app opens |
| Debug mode | Off | Log every scan cycle to the activity log |

### Statistics

| Setting | Default | Description |
|---|---|---|
| Max send records | `10 000` | How many send entries are kept in history |
| Max error records | `2 000` | How many error entries are kept in history |
| Months in bar chart | `12` | How many months the Overview chart covers |
| Autosave every N sends | `10` | How frequently stats are flushed to disk |

### Theme Presets & Color Editor

See [Themes](#themes) below

All settings are saved to `wis_settings.json` in the same directory as `WIS.pyw`

> **Migration note:** If you have an existing `webhook_settings.json` from an earlier version, WIS will automatically rename it to `wis_settings.json` on first launch

## Statistics

Click **Statistics** to open the analytics dashboard. It is divided into five tabs:

| Tab | Contents |
|---|---|
| **Overview** | Summary pills (total sent, successful, failed, success rate, error count), a bar chart of images sent over the last N months, and a donut chart of sends by file extension |
| **Webhooks** | Bar chart of sends per webhook and a table with per-webhook sent / failed / success-rate breakdown |
| **Folders** | Bar chart of sends per folder and a detail table with full paths and counts |
| **Errors** | Side-by-side pie and bar chart of error types (HTTP errors, timeouts, connection errors, etc.) plus a scrollable table of recent errors with timestamp, type, file, webhook, and detail |
| **Recent** | Chronological table of the last 500 sends showing time, filename, webhook, folder, extension, and OK / Fail status |

Statistics persist to `wis_stats.json` in the same directory. Use **↻ Refresh** to update all charts live, or **Clear All Stats** to wipe the history

## Themes

WIS ships with 8 built-in color presets accessible from **Settings → Theme Presets**:

| Preset | Description |
|---|---|
| Dark Blue *(default)* | Deep navy with blue accent |
| Midnight | True black with purple accent |
| Mocha | Warm brown tones |
| Solarized Dark | Classic Solarized palette |
| Nord | Arctic, north-bluish palette |
| Dracula | Purple-tinted dark theme |
| Rose Pine | Muted rose and pine tones |
| Light | Clean light theme |

### Color Editor

Below the preset selector, every UI color has an editable hex field with a live swatch preview that updates as you type. Changes apply after clicking **Save & Close** (a full restart applies them everywhere).

### Custom Presets

1. Adjust colors in the editor
2. Type a name in the **Save as** field and click **Save Preset**
3. The preset appears in the dropdown alongside built-in themes and persists between sessions
4. Select a custom preset and click **Delete Custom** to remove it

### Import / Export

- **⬆ Export Theme** — saves the current color editor values to a `.wistheme` file that can be shared
- **⬇ Import Theme** — loads a `.wistheme` or `.json` file, validates its colors, and optionally saves it as a named custom preset

## Sound Notifications

Place `validation.mp3` and `exclamation.mp3` in the same directory as `WIS.pyw`. WIS will play:

- `validation.mp3` — when a file is successfully delivered to **all** webhooks
- `exclamation.mp3` — when delivery fails on **any** webhook

Sounds require `pygame`. If it is not installed, a notice is shown in the Settings menu

## How It Works

When monitoring starts, WIS snapshots all existing image files in each folder and marks them as already seen. It then polls at the configured scan rate. When a new image appears, WIS waits for the file settle delay, verifies the file is non-empty, and POSTs it to every enabled webhook as `multipart/form-data`

HTTP `200`, `201`, and `204` are treated as success. Anything else, or a network error, is logged, counted as a failure, and recorded in the statistics history

## Data Files

| File | Purpose |
|---|---|
| `wis_settings.json` | All app settings, webhook list, folder list, theme presets |
| `wis_stats.json` | Send history and error log used by the Statistics dashboard |

Both files are created automatically in the same directory as `WIS.pyw`

## Notes

- The seen-files list resets each time monitoring is stopped and restarted
- Webhook endpoints must accept `multipart/form-data` file uploads
- Color changes require an app restart to apply fully
