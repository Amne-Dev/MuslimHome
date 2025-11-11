# Prayer Times MVP

A lightweight PyQt-based desktop application for Windows that displays Islamic daily prayer times, supports bilingual (English/Arabic) UI, and plays Adhan audio at the scheduled prayer times.

## Features

- Auto-detects user location via IP lookup with manual override.
- Manual override accepts city/country with optional latitude/longitude/timezone for fine-grained control.
- Settings dialog pulls the full list of AlAdhan-supported countries and cities with an offline fallback.
- Fetches daily prayer times and Hijri date from the AlAdhan API.
- Presents the five daily prayers in a simple table with the next prayer countdown.
- Plays configurable Adhan audio clips (full or short) per prayer using `playsound3`.
- Scheduler runs in the background to trigger Adhan playback and daily refresh.
- System tray icon for quick show/hide, refresh, and startup toggle actions.
- Optional launch-on-startup setting managed through the tray menu (Windows).
- Toggle between English and Arabic translations, including RTL layout for Arabic.
- Switch between light and dark themes or follow the system theme from the Settings dialog.

## Project Structure

```
project-root/
├── main.py            # Application entry point
├── ui.py              # PyQt window + dialogs
├── prayer_times.py    # API integration and location helpers
├── adhan_player.py    # Audio playback wrapper
├── scheduler.py       # APScheduler integration
├── translations.json  # UI translations (English/Arabic)
├── config.json        # User preferences and defaults
├── requirements.txt   # Python dependencies
└── assets/
    ├── README.txt     # Instructions for Adhan audio assets
    ├── adhan_full.mp3 # (Place your file here)
    └── adhan_short.mp3
```

## Getting Started

1. Create/activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Add your Adhan audio files to the `assets/` directory and ensure the paths in `config.json` match.

4. Run the application:
   ```powershell
   python main.py
   ```

## Configuration

- `config.json`
  - `language`: default UI language (`"en"` or `"ar"`).
- `theme`: preferred color theme (`"light"`, `"dark"`, or `"system"` to follow the OS).
  - `auto_location`: when `true`, the app uses IP-based geolocation each refresh.
  - `launch_on_startup`: enable (`true`) or disable (`false`) registration with Windows startup.
  - `location`: fallback/manual location data (city, country, latitude, longitude, timezone). Only `city` and `country` are required; the rest are optional.
  - `adhan`: configure audio file paths and prayers that use the short Adhan.
  - `calculation`: controls the AlAdhan computation method and school.

## Testing

1. Install development dependencies:
   ```powershell
   pip install -r requirements-dev.txt
   ```

2. Run the test suite:
   ```powershell
   pytest
   ```

The included tests validate location handling and API integrations via mocked responses.

## Packaging (Optional)

You can build a Windows executable with PyInstaller:
```powershell
pyinstaller --name PrayerTimes --onefile main.py
```
Adjust spec files/assets as needed to bundle translations and audio files.

## Notes

- Ensure outbound HTTPS access so the app can call the AlAdhan and ipinfo APIs.
- Manual location entry requires city and country; coordinates/timezone are optional and can be refined later.
- The scheduler uses the timezone returned by the API; update the configuration if you move between timezones.
