# Duck My Music 🎵🔊

A Windows application that runs in the background and automatically "ducks" (lowers) your Spotify volume when other applications play audio (like Chrome, Discord, Zoom, etc.), then smoothly restores it when the audio stops.

## Features

- **Automatic Audio Detection**: Monitors audio output from applications like Chrome, Firefox, Discord, Zoom, Teams, VLC, and more
- **Smooth Volume Fading**: Gradually fades Spotify volume down and back up for a seamless experience
- **System Tray Integration**: Runs quietly in the background with a tray icon to enable/disable and quit
- **Configurable**: Customize duck level, fade duration, monitored apps, and more via `config.json`
- **Cross-platform**: Works on Windows (full support) and macOS (partial support)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository:
   ```bash
   cd duck_my_music
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
python duck_my_music.py
```

The application will:
1. Start running in the background
2. Show a green speaker icon in your system tray
3. Automatically monitor for audio from configured applications
4. Duck Spotify when other audio plays, restore when it stops

### System Tray Menu

Right-click the tray icon to access:
- **✓ Enabled / ○ Disabled**: Toggle ducking on/off
- **Quit Duck My Music**: Exit the application

### Running at Startup (Windows)

To run automatically when Windows starts:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `duck_my_music.pyw` (or create a batch file)
3. Or use Task Scheduler for more control

## Configuration

Edit `config.json` to customize behavior:

```json
{
    "duck_level": 0.15,        // Volume when ducked (0.0 - 1.0)
    "normal_level": 1.0,       // Normal volume level (0.0 - 1.0)
    "fade_duration": 0.8,      // Fade time in seconds
    "fade_steps": 20,          // Number of volume steps during fade
    "check_interval": 0.1,     // How often to check for audio (seconds)
    "monitored_apps": [        // Apps that trigger ducking
        "chrome.exe",
        "firefox.exe",
        "msedge.exe",
        "discord.exe",
        "zoom.exe",
        "teams.exe",
        ...
    ],
    "music_apps": [            // Apps to duck (your music player)
        "Spotify.exe",
        "spotify.exe"
    ]
}
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `duck_level` | 0.15 | Volume level when ducked (15%) |
| `normal_level` | 1.0 | Normal volume level (100%) |
| `fade_duration` | 0.8 | How long the fade takes (seconds) |
| `fade_steps` | 20 | Smoothness of the fade |
| `check_interval` | 0.1 | How often to check for audio |
| `monitored_apps` | [...] | List of apps that trigger ducking |
| `music_apps` | [...] | List of music apps to control |

## Adding More Applications

To monitor additional applications, add their process name to `monitored_apps` in `config.json`:

```json
"monitored_apps": [
    "chrome.exe",
    "your_app.exe"
]
```

To find an app's process name:
1. Open Task Manager
2. Go to the "Details" tab
3. Find your application and note its name

## Troubleshooting

### Spotify volume not changing
- Make sure Spotify is running and playing music
- Check that the process name matches in `config.json`
- Verify the app has audio permissions in Windows

### No tray icon appears
- Some Windows configurations may hide system tray icons
- Click the ^ arrow in the system tray to find hidden icons

### High CPU usage
- Increase `check_interval` in config (e.g., 0.2 or 0.5)

### Log file
Check `duck_my_music.log` for detailed information about what the application is doing.

## Technical Details

### How it Works

1. **Audio Monitoring**: Uses Windows Core Audio API (via pycaw) to detect which applications are producing audio
2. **Peak Detection**: Monitors audio peak levels to determine if an app is actually playing sound (not just open)
3. **Volume Control**: Adjusts the per-application volume mixer level for Spotify
4. **Smooth Fading**: Uses threaded volume adjustments with small steps for smooth transitions

### Platform Support

| Platform | Audio Monitoring | Volume Control | System Tray |
|----------|-----------------|----------------|-------------|
| Windows  | ✅ Full         | ✅ Full        | ✅ Full     |
| macOS    | ⚠️ Limited*    | ⚠️ Limited*   | ✅ Full     |

*macOS requires additional tools like "Background Music" for per-app audio control

## License

MIT License - Feel free to use and modify as you like!

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## Building from Source

### Building the Windows Executable

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Generate the icon:
   ```bash
   python create_icon.py
   ```

3. Build the executable:
   ```bash
   pyinstaller duck_my_music.spec --clean
   ```

4. The executable will be in the `dist/` folder as `DuckMyMusic.exe`

### Automated Releases

This project uses GitHub Actions for automated releases. When you push a tag starting with `v` (e.g., `v1.0.0`), it will automatically:
- Build the Windows executable
- Create a GitHub release
- Upload the executable and a zip file

To create a release:
```bash
git tag v1.0.0
git push origin v1.0.0
```
