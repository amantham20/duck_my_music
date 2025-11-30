"""
Audio Monitor Module
Monitors audio sessions on Windows to detect when applications are producing sound.
"""

import sys
import logging
from abc import ABC, abstractmethod
from typing import List, Set, Optional

logger = logging.getLogger(__name__)


class AudioMonitor(ABC):
    """Abstract base class for audio monitoring."""
    
    @abstractmethod
    def get_active_audio_apps(self) -> Set[str]:
        """Returns a set of process names that are currently producing audio."""
        pass
    
    @abstractmethod
    def is_app_playing_audio(self, app_names: List[str]) -> bool:
        """Check if any of the specified apps are currently playing audio."""
        pass


class WindowsAudioMonitor(AudioMonitor):
    """Windows implementation using pycaw to monitor audio sessions."""
    
    def __init__(self):
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            from comtypes import CLSCTX_ALL, CoInitialize, CoUninitialize
            self.AudioUtilities = AudioUtilities
            self.ISimpleAudioVolume = ISimpleAudioVolume
            self.CLSCTX_ALL = CLSCTX_ALL
            self.CoInitialize = CoInitialize
            self.CoUninitialize = CoUninitialize
            self._available = True
            logger.info("Windows audio monitor initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import pycaw: {e}")
            self._available = False
    
    def get_active_audio_apps(self) -> Set[str]:
        """Get all apps currently producing audio (not muted and volume > 0)."""
        if not self._available:
            return set()
        
        active_apps = set()
        try:
            # Initialize COM for this thread
            self.CoInitialize()
            try:
                sessions = self.AudioUtilities.GetAllSessions()
                for session in sessions:
                    if session.Process:
                        try:
                            # Get the audio meter to check if actually producing sound
                            meter = session._ctl.QueryInterface(
                                self._get_audio_meter_interface()
                            )
                            peak = meter.GetPeakValue()
                            
                            if peak > 0.0001:  # Threshold for actual audio output
                                process_name = session.Process.name()
                                active_apps.add(process_name.lower())
                                logger.debug(f"Active audio: {process_name} (peak: {peak:.4f})")
                        except Exception as e:
                            # Some sessions don't support peak metering
                            logger.debug(f"Could not get peak for {session.Process.name()}: {e}")
            finally:
                # Uninitialize COM when done
                self.CoUninitialize()
        except Exception as e:
            logger.error(f"Error getting audio sessions: {e}")
        
        return active_apps
    
    def _get_audio_meter_interface(self):
        """Get the IAudioMeterInformation interface."""
        from pycaw.pycaw import IAudioMeterInformation
        return IAudioMeterInformation
    
    def is_app_playing_audio(self, app_names: List[str]) -> bool:
        """Check if any of the specified apps are currently playing audio."""
        if not self._available:
            return False
        
        app_names_lower = [name.lower() for name in app_names]
        active_apps = self.get_active_audio_apps()
        
        for active_app in active_apps:
            if active_app in app_names_lower:
                logger.debug(f"Detected audio from: {active_app}")
                return True
        
        return False


class MacAudioMonitor(AudioMonitor):
    """macOS implementation for audio monitoring."""
    
    def __init__(self):
        self._available = False
        # Note: macOS audio monitoring requires different approach
        # This is a placeholder - full implementation would use 
        # CoreAudio or a tool like Background Music
        logger.warning("macOS audio monitor is not fully implemented")
    
    def get_active_audio_apps(self) -> Set[str]:
        """Get all apps currently producing audio on macOS."""
        # Would need CoreAudio implementation
        return set()
    
    def is_app_playing_audio(self, app_names: List[str]) -> bool:
        """Check if any of the specified apps are playing audio on macOS."""
        return False


def create_audio_monitor() -> AudioMonitor:
    """Factory function to create the appropriate audio monitor for the platform."""
    if sys.platform == 'win32':
        return WindowsAudioMonitor()
    elif sys.platform == 'darwin':
        return MacAudioMonitor()
    else:
        raise NotImplementedError(f"Platform {sys.platform} is not supported")
