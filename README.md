# Muslim Home – Prayer Times Companion

Muslim Home is a friendly Windows desktop app that keeps you on time for every Salah. Install it once, let it live in the system tray, and enjoy clear schedules, Adhan reminders, and a beautiful bilingual experience tailored to your day.

## Download & Install

1. Visit the **Releases** page on GitHub and download the latest `MuslimHomeSetup.exe`.
2. Run the installer (Windows may show a SmartScreen prompt—choose **More info → Run anyway**).
3. The app installs to `C:\Program Files (x86)\Muslim Home` and adds shortcuts to the Start menu (desktop shortcut optional).
4. Launch Muslim Home after installation; the onboarding screen will guide you through language and location choices.

### System Requirements

- Windows 10 or 11 (64-bit recommended)
- Internet access for initial setup and daily schedule/ weather updates
- Audio device for Adhan playback (optional but encouraged!)

## What You Get

- **Prayer schedules**: real-time daily times plus a seven-day timetable view.
- **Adhan notifications**: full or short audio per prayer, snooze/dismiss buttons, and tray alerts.
- **Smart location**: automatic detection with easy manual override using an offline city catalog.
- **Weather glance**: current conditions and a five-day forecast for your location.
- **Daily inspiration**: curated Qur’an verses with share/copy shortcuts.
- **Light & dark themes**: follow Windows or pick your favourite.
- **Bilingual UI**: instant switch between English and Arabic, with full RTL support.

## Using Muslim Home

### Tray Controls

- Closed windows keep the app running in the tray. Double-click the tray icon to reopen it.
- Right-click the tray icon for quick actions: show/hide, refresh schedules, toggle launch on startup, or quit.

### Settings Overview

- **Language & Theme**: switch any time via the sidebar or tray.
- **Location**: stay on auto-detect or choose a specific city/country. Advanced users can enter latitude/longitude/timezone for precise adjustments.
- **Adhan**: decide which prayers use the short clip, change audio files, or mute entirely.
- **Prayers**: view calculation method and madhhab; update if you follow a different convention.
- **Qur’an bookmark**: save your place and jump straight back to it.

### Weekly Timetable

Expand the timetable card on the Home page to preview the next seven days. Dates and day names adapt to the selected language, and the tile highlights the current day.

## Tips & Troubleshooting

- **Missed onboarding?** Reset from Settings → General → “Restart welcome tour.”
- **Audio not playing?** Ensure your sound device is active and volume is up. The tray menu can pause/resume Adhan playback.
- **Manual location blank?** Start typing the country; once selected, the city dropdown fills automatically.
- **Startup toggle not sticking?** Windows may block startup entries in managed environments; check if your account has permission to add startup apps.
- **Config location:** User preferences live in `%APPDATA%\Muslim Home\config.json`. Delete that file to reset the app to defaults.

## Stay Updated

- Check GitHub Releases for new builds and changelog notes.
- Enable **Watch → Releases only** on the repo to get notified automatically.

## Need Help?

- Open an issue on GitHub with steps to reproduce the problem.
- Include logs from `%APPDATA%\Muslim Home\logs` (if present) and your Windows version.
- Feature ideas welcome! Let us know what would make Muslim Home even more useful.

---

_May this companion help you stay mindful of Salah and bring barakah into your digital routine._

---

<details>
<summary>Developer Notes</summary>

Muslim Home is built with Python 3.12, PyQt5, APScheduler, and PyInstaller. To run from source:

```powershell
git clone https://github.com/<your-account>/Prayer.git
cd Prayer
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Run tests with `pip install -r requirements-dev.txt` followed by `pytest`.

Packaging uses PyInstaller (app build) + Inno Setup (installer). Mutable configs are stored in `%APPDATA%\Muslim Home` to avoid UAC prompts.

</details>
