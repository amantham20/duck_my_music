"""
Duck My Music - GUI Application
Provides a graphical interface for configuring and controlling the audio ducking.
"""

import json
import logging
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import winreg

from audio_monitor import create_audio_monitor
from volume_controller import create_volume_controller, VolumeFader
from spotify_controller import SpotifyController
from system_tray import SystemTray

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

CONFIG_PATH = "config.json"
APP_NAME = "Duck My Music"
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_script_path():
    """Get the path to the main script."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)


def load_config():
    """Load configuration from JSON file."""
    default_config = {
        "duck_level": 0.1,
        "normal_level": 1.0,
        "fade_duration": 0.8,
        "fade_steps": 20,
        "check_interval": 0.1,
        "pause_when_ducked": True,
        "restore_delay": 0.5,
        "start_minimized": False,
        "run_on_startup": False,
        "monitored_apps": ["chrome.exe"],
        "music_apps": ["Spotify.exe", "spotify.exe"]
    }
    
    try:
        config_file = Path(CONFIG_PATH)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
    except Exception as e:
        logger.warning(f"Could not load config: {e}")
    
    return default_config


def save_config(config):
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        logger.info("Configuration saved")
        return True
    except Exception as e:
        logger.error(f"Could not save config: {e}")
        return False


def is_startup_enabled():
    """Check if app is set to run on Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_startup_enabled(enabled):
    """Enable or disable running on Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE)
        
        if enabled:
            # Get the path to the pyw file for silent startup
            script_dir = os.path.dirname(os.path.abspath(__file__))
            pyw_path = os.path.join(script_dir, "duck_my_music_gui.pyw")
            
            # Try to use venv pythonw.exe first
            venv_pythonw = os.path.join(script_dir, "venv", "Scripts", "pythonw.exe")
            if os.path.exists(venv_pythonw):
                startup_cmd = f'"{venv_pythonw}" "{pyw_path}" --minimized'
            else:
                # Fallback to system Python
                python_path = sys.executable
                pythonw_path = python_path.replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw_path):
                    startup_cmd = f'"{pythonw_path}" "{pyw_path}" --minimized'
                else:
                    startup_cmd = f'"{python_path}" "{pyw_path}" --minimized'
            
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_cmd)
            logger.info(f"Added to startup: {startup_cmd}")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                logger.info("Removed from startup")
            except FileNotFoundError:
                pass
        
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"Could not modify startup: {e}")
        return False


class DuckMyMusicGUI:
    """Main GUI application class."""
    
    def __init__(self, start_minimized=False):
        self.config = load_config()
        self.running = False
        self.enabled = True
        self.start_minimized = start_minimized
        
        # Initialize components (will be created when started)
        self.audio_monitor = None
        self.volume_controller = None
        self.spotify_controller = None
        self.fader = None
        self.monitor_thread = None
        self.shutdown_event = threading.Event()
        self.silence_start_time = None
        
        # Create GUI
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("450x550")
        self.root.resizable(False, False)
        
        # Set icon (if available)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create system tray
        self.tray = None
        
        # Build the GUI
        self._create_widgets()
        
        # Load current startup state
        self.startup_var.set(is_startup_enabled())
        
        # Start minimized if requested (auto-start monitoring and minimize to tray)
        if self.start_minimized:
            self.root.after(100, self._start_and_minimize)
        else:
            # Auto-start monitoring even when not minimized
            self.root.after(100, self.start_monitoring)
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎵 Duck My Music", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Stopped")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 11))
        self.status_label.pack()
        
        # Control buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start", command=self.start_monitoring, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self.stop_monitoring, width=15, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.minimize_btn = ttk.Button(btn_frame, text="▼ Minimize to Tray", command=self.minimize_to_tray, width=18)
        self.minimize_btn.pack(side=tk.LEFT)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Duck level slider
        ttk.Label(settings_frame, text="Duck Level (volume when ducked):").pack(anchor=tk.W)
        self.duck_level_var = tk.DoubleVar(value=self.config.get('duck_level', 0.1))
        duck_frame = ttk.Frame(settings_frame)
        duck_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.duck_slider = ttk.Scale(duck_frame, from_=0, to=0.5, variable=self.duck_level_var, orient=tk.HORIZONTAL)
        self.duck_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.duck_label = ttk.Label(duck_frame, text=f"{self.duck_level_var.get()*100:.0f}%", width=5)
        self.duck_label.pack(side=tk.LEFT, padx=(5, 0))
        self.duck_level_var.trace_add('write', lambda *_: self.duck_label.config(text=f"{self.duck_level_var.get()*100:.0f}%"))
        
        # Fade duration slider
        ttk.Label(settings_frame, text="Fade Duration (seconds):").pack(anchor=tk.W)
        self.fade_duration_var = tk.DoubleVar(value=self.config.get('fade_duration', 0.8))
        fade_frame = ttk.Frame(settings_frame)
        fade_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.fade_slider = ttk.Scale(fade_frame, from_=0.1, to=3.0, variable=self.fade_duration_var, orient=tk.HORIZONTAL)
        self.fade_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.fade_label = ttk.Label(fade_frame, text=f"{self.fade_duration_var.get():.1f}s", width=5)
        self.fade_label.pack(side=tk.LEFT, padx=(5, 0))
        self.fade_duration_var.trace_add('write', lambda *_: self.fade_label.config(text=f"{self.fade_duration_var.get():.1f}s"))
        
        # Restore delay slider
        ttk.Label(settings_frame, text="Restore Delay (wait before restoring):").pack(anchor=tk.W)
        self.restore_delay_var = tk.DoubleVar(value=self.config.get('restore_delay', 0.5))
        restore_frame = ttk.Frame(settings_frame)
        restore_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.restore_slider = ttk.Scale(restore_frame, from_=0.1, to=3.0, variable=self.restore_delay_var, orient=tk.HORIZONTAL)
        self.restore_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.restore_label = ttk.Label(restore_frame, text=f"{self.restore_delay_var.get():.1f}s", width=5)
        self.restore_label.pack(side=tk.LEFT, padx=(5, 0))
        self.restore_delay_var.trace_add('write', lambda *_: self.restore_label.config(text=f"{self.restore_delay_var.get():.1f}s"))
        
        # Checkboxes
        self.pause_var = tk.BooleanVar(value=self.config.get('pause_when_ducked', True))
        ttk.Checkbutton(settings_frame, text="Pause Spotify when ducked", variable=self.pause_var).pack(anchor=tk.W, pady=(0, 5))
        
        self.startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Run on Windows startup", variable=self.startup_var, 
                       command=self.toggle_startup).pack(anchor=tk.W, pady=(0, 5))
        
        self.start_minimized_var = tk.BooleanVar(value=self.config.get('start_minimized', False))
        ttk.Checkbutton(settings_frame, text="Start minimized to tray", variable=self.start_minimized_var).pack(anchor=tk.W)
        
        # Monitored apps
        apps_frame = ttk.LabelFrame(main_frame, text="Monitored Apps (trigger ducking)", padding="10")
        apps_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.apps_var = tk.StringVar(value=", ".join(self.config.get('monitored_apps', ['chrome.exe'])))
        self.apps_entry = ttk.Entry(apps_frame, textvariable=self.apps_var)
        self.apps_entry.pack(fill=tk.X)
        ttk.Label(apps_frame, text="(comma-separated, e.g., chrome.exe, discord.exe)", font=("Segoe UI", 8)).pack(anchor=tk.W)
        
        # Save button
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill=tk.X)
        
        ttk.Button(save_frame, text="💾 Save Settings", command=self.save_settings).pack(side=tk.LEFT)
        ttk.Button(save_frame, text="↻ Reset to Defaults", command=self.reset_defaults).pack(side=tk.LEFT, padx=(10, 0))
    
    def _start_and_minimize(self):
        """Start monitoring and minimize to tray."""
        self.start_monitoring()
        self.minimize_to_tray()
    
    def start_monitoring(self):
        """Start the audio monitoring."""
        if self.running:
            return
        
        try:
            # Initialize components
            self.audio_monitor = create_audio_monitor()
            self.volume_controller = create_volume_controller()
            self.spotify_controller = SpotifyController()
            
            self.fader = VolumeFader(
                controller=self.volume_controller,
                music_apps=self.config['music_apps'],
                duck_level=self.duck_level_var.get(),
                normal_level=self.config['normal_level'],
                fade_duration=self.fade_duration_var.get(),
                fade_steps=self.config['fade_steps'],
                pause_when_ducked=self.pause_var.get(),
                spotify_controller=self.spotify_controller
            )
            
            self.running = True
            self.shutdown_event.clear()
            
            # Start monitor thread
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            # Update UI
            self.status_var.set("✅ Running - Monitoring for audio...")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            logger.info("Monitoring started")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start monitoring: {e}")
            logger.error(f"Failed to start: {e}")
    
    def stop_monitoring(self):
        """Stop the audio monitoring."""
        if not self.running:
            return
        
        self.running = False
        self.shutdown_event.set()
        
        # Restore volume
        if self.fader:
            self.fader.force_restore()
        
        # Wait for thread
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        # Update UI
        self.status_var.set("⏹ Stopped")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        logger.info("Monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        import time
        
        check_interval = self.config.get('check_interval', 0.1)
        monitored_apps = [app.strip() for app in self.apps_var.get().split(',')]
        restore_delay = self.restore_delay_var.get()
        
        while not self.shutdown_event.is_set():
            try:
                if self.enabled:
                    other_audio_playing = self.audio_monitor.is_app_playing_audio(monitored_apps)
                    
                    if other_audio_playing and not self.fader.is_ducked:
                        self.root.after(0, lambda: self.status_var.set("🔊 Chrome playing - Spotify ducked"))
                        self.fader.duck()
                        self.silence_start_time = None
                        
                    elif other_audio_playing and self.fader.is_ducked:
                        self.silence_start_time = None
                        
                    elif not other_audio_playing and self.fader.is_ducked:
                        if self.silence_start_time is None:
                            self.silence_start_time = time.time()
                        elif time.time() - self.silence_start_time >= restore_delay:
                            self.root.after(0, lambda: self.status_var.set("✅ Running - Monitoring for audio..."))
                            self.fader.restore()
                            self.silence_start_time = None
                
                self.shutdown_event.wait(check_interval)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                self.shutdown_event.wait(1)
    
    def save_settings(self):
        """Save current settings to config file."""
        self.config['duck_level'] = self.duck_level_var.get()
        self.config['fade_duration'] = self.fade_duration_var.get()
        self.config['restore_delay'] = self.restore_delay_var.get()
        self.config['pause_when_ducked'] = self.pause_var.get()
        self.config['start_minimized'] = self.start_minimized_var.get()
        self.config['monitored_apps'] = [app.strip() for app in self.apps_var.get().split(',')]
        
        if save_config(self.config):
            messagebox.showinfo("Saved", "Settings saved successfully!\nRestart monitoring to apply changes.")
        else:
            messagebox.showerror("Error", "Failed to save settings.")
    
    def reset_defaults(self):
        """Reset settings to defaults."""
        self.duck_level_var.set(0.1)
        self.fade_duration_var.set(0.8)
        self.restore_delay_var.set(0.5)
        self.pause_var.set(True)
        self.apps_var.set("chrome.exe")
    
    def toggle_startup(self):
        """Toggle Windows startup setting."""
        enabled = self.startup_var.get()
        if not set_startup_enabled(enabled):
            # Revert if failed
            self.startup_var.set(not enabled)
            messagebox.showerror("Error", "Failed to modify startup settings.")
    
    def minimize_to_tray(self):
        """Minimize the window to system tray."""
        self.root.withdraw()
        
        if self.tray is None:
            self.tray = SystemTray(
                on_toggle=self._on_tray_toggle,
                on_quit=self._on_tray_quit,
                on_show=self._on_tray_show
            )
            self.tray.start()
        
        self.tray.notify("Duck My Music", "Running in background. Double-click tray icon to restore.")
    
    def _on_tray_show(self):
        """Handle show window from tray."""
        self.root.after(0, self.restore_from_tray)
    
    def _on_tray_toggle(self, enabled):
        """Handle enable/disable from tray."""
        self.enabled = enabled
        if not enabled and self.fader and self.fader.is_ducked:
            self.fader.restore()
    
    def _on_tray_quit(self):
        """Handle quit from tray."""
        self.root.after(0, self.quit_app)
    
    def restore_from_tray(self):
        """Restore window from tray."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def on_close(self):
        """Handle window close button."""
        if self.running:
            result = messagebox.askyesnocancel(
                "Minimize or Quit?",
                "Duck My Music is running.\n\n"
                "Yes = Minimize to tray\n"
                "No = Stop and quit\n"
                "Cancel = Go back"
            )
            if result is True:  # Yes - minimize
                self.minimize_to_tray()
            elif result is False:  # No - quit
                self.quit_app()
            # Cancel - do nothing
        else:
            self.quit_app()
    
    def quit_app(self):
        """Quit the application."""
        self.stop_monitoring()
        
        if self.tray:
            self.tray.stop()
        
        self.root.destroy()
    
    def run(self):
        """Run the GUI application."""
        # Bind tray icon double-click to restore (via polling)
        def check_tray_restore():
            # This is a simple way to handle restore - could be improved
            self.root.after(500, check_tray_restore)
        
        self.root.after(500, check_tray_restore)
        self.root.mainloop()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Duck My Music - GUI")
    parser.add_argument('--minimized', action='store_true', help='Start minimized to tray')
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    app = DuckMyMusicGUI(start_minimized=args.minimized)
    app.run()


if __name__ == "__main__":
    main()
