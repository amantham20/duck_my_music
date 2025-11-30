"""
Duck My Music - Main Application
Automatically ducks Spotify when other applications play audio.
"""

import json
import logging
import signal
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any

from audio_monitor import create_audio_monitor
from volume_controller import create_volume_controller, VolumeFader
from system_tray import SystemTray
from spotify_controller import SpotifyController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('duck_my_music.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    default_config = {
        "duck_level": 0.1,
        "normal_level": 1.0,
        "fade_duration": 0.8,
        "fade_steps": 20,
        "check_interval": 0.1,
        "pause_when_ducked": True,
        "monitored_apps": [
            "chrome.exe",
            "firefox.exe", 
            "msedge.exe",
            "brave.exe",
            "opera.exe",
            "discord.exe",
            "zoom.exe",
            "teams.exe",
            "vlc.exe"
        ],
        "music_apps": [
            "Spotify.exe",
            "spotify.exe"
        ]
    }
    
    try:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # Merge with defaults
                default_config.update(user_config)
                logger.info(f"Loaded configuration from {config_path}")
        else:
            # Create default config file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Created default configuration at {config_path}")
    except Exception as e:
        logger.warning(f"Could not load config, using defaults: {e}")
    
    return default_config


class DuckMyMusic:
    """Main application class for audio ducking."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.enabled = True
        
        # Initialize components
        logger.info("Initializing audio monitor...")
        self.audio_monitor = create_audio_monitor()
        
        logger.info("Initializing volume controller...")
        self.volume_controller = create_volume_controller()
        
        logger.info("Initializing Spotify controller...")
        self.spotify_controller = SpotifyController()
        
        logger.info("Initializing volume fader...")
        self.fader = VolumeFader(
            controller=self.volume_controller,
            music_apps=config['music_apps'],
            duck_level=config['duck_level'],
            normal_level=config['normal_level'],
            fade_duration=config['fade_duration'],
            fade_steps=config['fade_steps'],
            pause_when_ducked=config.get('pause_when_ducked', True),
            spotify_controller=self.spotify_controller
        )
        
        # System tray
        logger.info("Initializing system tray...")
        self.tray = SystemTray(
            on_toggle=self._on_toggle,
            on_quit=self._on_quit
        )
        
        # State tracking
        self._was_ducked = False
        self._monitor_thread: threading.Thread = None
        self._shutdown_event = threading.Event()
    
    def _on_toggle(self, enabled: bool):
        """Handle enable/disable toggle from tray."""
        self.enabled = enabled
        logger.info(f"Ducking {'enabled' if enabled else 'disabled'}")
        
        if not enabled and self.fader.is_ducked:
            # Restore volume when disabled
            self.fader.restore()
    
    def _on_quit(self):
        """Handle quit request from tray."""
        self.stop()
    
    def _monitor_loop(self):
        """Main monitoring loop that checks for audio and controls ducking."""
        logger.info("Monitor loop started")
        check_interval = self.config['check_interval']
        monitored_apps = self.config['monitored_apps']
        restore_delay = self.config.get('restore_delay', 0.5)
        
        silence_start_time = None  # Track when Chrome went silent
        
        while not self._shutdown_event.is_set():
            try:
                if self.enabled:
                    # Check if any monitored app is playing audio
                    other_audio_playing = self.audio_monitor.is_app_playing_audio(monitored_apps)
                    
                    if other_audio_playing and not self.fader.is_ducked:
                        # Chrome started playing - duck immediately
                        logger.info("Chrome audio detected - ducking Spotify")
                        self.fader.duck()
                        self._was_ducked = True
                        silence_start_time = None
                        
                    elif other_audio_playing and self.fader.is_ducked:
                        # Chrome still playing - reset silence timer
                        silence_start_time = None
                        
                    elif not other_audio_playing and self.fader.is_ducked:
                        # Chrome went silent
                        if silence_start_time is None:
                            # Start tracking silence
                            silence_start_time = time.time()
                            logger.debug("Chrome went silent, waiting...")
                        elif time.time() - silence_start_time >= restore_delay:
                            # Chrome has been silent long enough - restore
                            logger.info("Chrome paused/stopped - restoring Spotify")
                            self.fader.restore()
                            self._was_ducked = False
                            silence_start_time = None
                
                self._shutdown_event.wait(check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                self._shutdown_event.wait(1)  # Wait longer on error
    
    def start(self):
        """Start the application."""
        if self.running:
            return
        
        logger.info("Starting Duck My Music...")
        self.running = True
        self._shutdown_event.clear()
        
        # Start system tray
        self.tray.start()
        
        # Start monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        # Show startup notification
        self.tray.notify("Duck My Music", "Running in background")
        
        logger.info("Duck My Music started successfully")
    
    def stop(self):
        """Stop the application."""
        if not self.running:
            return
        
        logger.info("Stopping Duck My Music...")
        self.running = False
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Restore volume before exit
        self.fader.force_restore()
        
        # Stop components
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        
        self.tray.stop()
        
        logger.info("Duck My Music stopped")
    
    def run_forever(self):
        """Run the application until interrupted."""
        self.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()


def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("Duck My Music - Starting")
    logger.info("=" * 50)
    
    # Load configuration
    config = load_config()
    
    # Log configuration
    logger.info(f"Duck level: {config['duck_level']}")
    logger.info(f"Fade duration: {config['fade_duration']}s")
    logger.info(f"Monitored apps: {', '.join(config['monitored_apps'])}")
    logger.info(f"Music apps: {', '.join(config['music_apps'])}")
    
    # Create and run application
    app = DuckMyMusic(config)
    
    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        app.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the application
    app.run_forever()


if __name__ == "__main__":
    main()
