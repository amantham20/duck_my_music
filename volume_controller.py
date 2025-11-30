"""
Volume Controller Module
Controls the volume of specific applications with smooth fading.
"""

import sys
import time
import logging
import threading
from typing import Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class VolumeController(ABC):
    """Abstract base class for volume control."""
    
    @abstractmethod
    def get_app_volume(self, app_name: str) -> Optional[float]:
        """Get the current volume of an application (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def set_app_volume(self, app_name: str, volume: float) -> bool:
        """Set the volume of an application (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def is_app_running(self, app_name: str) -> bool:
        """Check if the application is currently running."""
        pass


class WindowsVolumeController(VolumeController):
    """Windows implementation using pycaw for volume control."""
    
    def __init__(self):
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            from comtypes import CoInitialize, CoUninitialize
            self.AudioUtilities = AudioUtilities
            self.ISimpleAudioVolume = ISimpleAudioVolume
            self.CoInitialize = CoInitialize
            self.CoUninitialize = CoUninitialize
            self._available = True
            self._lock = threading.Lock()
            logger.info("Windows volume controller initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import pycaw: {e}")
            self._available = False
    
    def _get_session_for_app(self, app_name: str, sessions=None):
        """Get the audio session for a specific application."""
        if not self._available:
            return None
        
        try:
            if sessions is None:
                sessions = self.AudioUtilities.GetAllSessions()
            app_name_lower = app_name.lower()
            
            for session in sessions:
                if session.Process:
                    process_name = session.Process.name().lower()
                    if process_name == app_name_lower or app_name_lower in process_name:
                        return session
        except Exception as e:
            logger.error(f"Error getting session for {app_name}: {e}")
        
        return None
    
    def get_app_volume(self, app_name: str) -> Optional[float]:
        """Get the current volume of an application."""
        with self._lock:
            try:
                self.CoInitialize()
                try:
                    session = self._get_session_for_app(app_name)
                    if session:
                        volume_interface = session._ctl.QueryInterface(self.ISimpleAudioVolume)
                        return volume_interface.GetMasterVolume()
                finally:
                    self.CoUninitialize()
            except Exception as e:
                logger.error(f"Error getting volume for {app_name}: {e}")
            return None
    
    def set_app_volume(self, app_name: str, volume: float) -> bool:
        """Set the volume of an application."""
        volume = max(0.0, min(1.0, volume))  # Clamp to valid range
        
        with self._lock:
            try:
                self.CoInitialize()
                try:
                    session = self._get_session_for_app(app_name)
                    if session:
                        volume_interface = session._ctl.QueryInterface(self.ISimpleAudioVolume)
                        volume_interface.SetMasterVolume(volume, None)
                        logger.debug(f"Set {app_name} volume to {volume:.2f}")
                        return True
                finally:
                    self.CoUninitialize()
            except Exception as e:
                logger.error(f"Error setting volume for {app_name}: {e}")
            return False
    
    def is_app_running(self, app_name: str) -> bool:
        """Check if the application is running and has an audio session."""
        with self._lock:
            try:
                self.CoInitialize()
                try:
                    return self._get_session_for_app(app_name) is not None
                finally:
                    self.CoUninitialize()
            except Exception:
                return False


class MacVolumeController(VolumeController):
    """macOS implementation for volume control."""
    
    def __init__(self):
        import subprocess
        self.subprocess = subprocess
        self._available = sys.platform == 'darwin'
        if self._available:
            logger.info("macOS volume controller initialized")
        else:
            logger.warning("macOS volume controller not available on this platform")
    
    def get_app_volume(self, app_name: str) -> Optional[float]:
        """Get app volume on macOS - limited implementation."""
        # macOS doesn't have per-app volume by default
        # Would need Background Music or similar
        return None
    
    def set_app_volume(self, app_name: str, volume: float) -> bool:
        """Set app volume on macOS - limited implementation."""
        # Would need Background Music or similar for per-app volume
        return False
    
    def is_app_running(self, app_name: str) -> bool:
        """Check if app is running on macOS."""
        try:
            result = self.subprocess.run(
                ['pgrep', '-x', app_name.replace('.exe', '')],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False


class VolumeFader:
    """Handles smooth volume fading for music applications."""
    
    def __init__(
        self,
        controller: VolumeController,
        music_apps: List[str],
        duck_level: float = 0.1,
        normal_level: float = 1.0,
        fade_duration: float = 0.8,
        fade_steps: int = 20,
        pause_when_ducked: bool = True,
        spotify_controller = None
    ):
        self.controller = controller
        self.music_apps = music_apps
        self.duck_level = duck_level
        self.normal_level = normal_level
        self.fade_duration = fade_duration
        self.fade_steps = fade_steps
        self.pause_when_ducked = pause_when_ducked
        self.spotify_controller = spotify_controller
        
        self._current_target = normal_level
        self._is_ducked = False
        self._fade_thread: Optional[threading.Thread] = None
        self._stop_fade = threading.Event()
        self._lock = threading.Lock()
    
    @property
    def is_ducked(self) -> bool:
        return self._is_ducked
    
    def _get_active_music_app(self) -> Optional[str]:
        """Find which music app is currently running."""
        for app in self.music_apps:
            if self.controller.is_app_running(app):
                return app
        return None
    
    def _fade_to_volume(self, target: float, pause_after: bool = False, play_before: bool = False):
        """Smoothly fade to the target volume."""
        music_app = self._get_active_music_app()
        if not music_app:
            logger.debug("No music app found for fading")
            return
        
        # Resume playback before fading up
        if play_before and self.spotify_controller:
            self.spotify_controller.play()
            time.sleep(0.1)  # Small delay to let playback start
        
        current_volume = self.controller.get_app_volume(music_app)
        if current_volume is None:
            logger.debug(f"Could not get current volume for {music_app}")
            return
        
        step_delay = self.fade_duration / self.fade_steps
        volume_step = (target - current_volume) / self.fade_steps
        
        logger.info(f"Fading {music_app} from {current_volume:.2f} to {target:.2f}")
        
        for i in range(self.fade_steps):
            if self._stop_fade.is_set():
                logger.debug("Fade interrupted")
                return
            
            new_volume = current_volume + (volume_step * (i + 1))
            self.controller.set_app_volume(music_app, new_volume)
            time.sleep(step_delay)
        
        # Ensure we hit the exact target
        self.controller.set_app_volume(music_app, target)
        logger.debug(f"Fade complete: {music_app} at {target:.2f}")
        
        # Pause playback after fading down
        if pause_after and self.spotify_controller:
            self.spotify_controller.pause()
    
    def duck(self):
        """Duck the music volume (fade down) and optionally pause."""
        with self._lock:
            if self._is_ducked:
                return
            
            self._stop_current_fade()
            self._is_ducked = True
            self._current_target = self.duck_level
            
            self._fade_thread = threading.Thread(
                target=self._fade_to_volume,
                args=(self.duck_level, self.pause_when_ducked, False),
                daemon=True
            )
            self._fade_thread.start()
    
    def restore(self):
        """Restore the music volume (fade up) and optionally resume playback."""
        with self._lock:
            if not self._is_ducked:
                return
            
            self._stop_current_fade()
            self._is_ducked = False
            self._current_target = self.normal_level
            
            # Pass play_before=True to resume before fading up
            should_play = self.pause_when_ducked and self.spotify_controller and self.spotify_controller.is_paused_by_us
            
            self._fade_thread = threading.Thread(
                target=self._fade_to_volume,
                args=(self.normal_level, False, should_play),
                daemon=True
            )
            self._fade_thread.start()
    
    def _stop_current_fade(self):
        """Stop any ongoing fade operation."""
        if self._fade_thread and self._fade_thread.is_alive():
            self._stop_fade.set()
            self._fade_thread.join(timeout=0.5)
            self._stop_fade.clear()
    
    def force_restore(self):
        """Immediately restore volume to normal without fading."""
        with self._lock:
            self._stop_current_fade()
            self._is_ducked = False
            
            # Resume playback if we paused it
            if self.spotify_controller and self.spotify_controller.is_paused_by_us:
                self.spotify_controller.play()
            
            music_app = self._get_active_music_app()
            if music_app:
                self.controller.set_app_volume(music_app, self.normal_level)
                logger.info(f"Force restored {music_app} to {self.normal_level}")


def create_volume_controller() -> VolumeController:
    """Factory function to create the appropriate volume controller."""
    if sys.platform == 'win32':
        return WindowsVolumeController()
    elif sys.platform == 'darwin':
        return MacVolumeController()
    else:
        raise NotImplementedError(f"Platform {sys.platform} is not supported")
