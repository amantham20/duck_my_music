"""
Media State Monitor Module
Monitors Windows Media Transport Controls to detect active media sessions 
and their playback states (playing/paused/stopped).
"""

import sys
import logging
import asyncio
from typing import Set, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MediaState:
    """Represents the state of a media session."""
    app_name: str
    is_playing: bool
    is_paused: bool
    title: Optional[str] = None


class MediaStateMonitor:
    """
    Monitors Windows Media Transport Controls to track media session states.
    This allows us to distinguish between:
    - Media is playing (active audio)
    - Media is paused (no audio but session exists)
    - Media is stopped/closed (no session)
    """
    
    def __init__(self):
        self._available = False
        self._session_manager = None
        
        if sys.platform != 'win32':
            logger.warning("MediaStateMonitor only works on Windows")
            return
        
        # Test if winsdk is available
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager
            )
            self._available = True
            logger.info("Media state monitor initialized (using Windows Media Controls)")
        except ImportError:
            logger.warning("winsdk not available, media state monitoring disabled")
    
    async def _get_session_manager(self):
        """Get or create the session manager."""
        if self._session_manager is None:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as SessionManager
            )
            self._session_manager = await SessionManager.request_async()
        return self._session_manager
    
    async def _get_all_media_states_async(self) -> Dict[str, MediaState]:
        """Get states of all media sessions asynchronously."""
        if not self._available:
            return {}
        
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
            )
            
            session_manager = await self._get_session_manager()
            sessions = session_manager.get_sessions()
            
            media_states = {}
            
            for session in sessions:
                try:
                    app_id = session.source_app_user_model_id
                    if not app_id:
                        continue
                    
                    # Get playback info
                    playback_info = session.get_playback_info()
                    if not playback_info:
                        continue
                    
                    status = playback_info.playback_status
                    
                    # Try to get media title
                    title = None
                    try:
                        media_props = await session.try_get_media_properties_async()
                        if media_props:
                            title = media_props.title
                    except Exception:
                        pass
                    
                    # Extract app name from app_id (e.g., "MSEdge.exe" from full ID)
                    app_name = app_id.split('!')[-1] if '!' in app_id else app_id
                    
                    state = MediaState(
                        app_name=app_name,
                        is_playing=(status == PlaybackStatus.PLAYING),
                        is_paused=(status == PlaybackStatus.PAUSED),
                        title=title
                    )
                    
                    media_states[app_name.lower()] = state
                    logger.debug(f"Media session: {app_name} - Playing: {state.is_playing}, Paused: {state.is_paused}")
                    
                except Exception as e:
                    logger.debug(f"Error processing session: {e}")
            
            return media_states
            
        except Exception as e:
            logger.error(f"Error getting media states: {e}")
            return {}
    
    def _run_async(self, coro):
        """Run an async function from sync code."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    def get_all_media_states(self) -> Dict[str, MediaState]:
        """Get states of all media sessions synchronously."""
        if not self._available:
            return {}
        return self._run_async(self._get_all_media_states_async())
    
    def has_active_media_session(self, app_names: list[str]) -> bool:
        """
        Check if any of the specified apps have an active media session.
        An active session means the app is either playing OR paused.
        Returns False only if there's no media session at all.
        """
        if not self._available:
            return False
        
        app_names_lower = [name.lower() for name in app_names]
        media_states = self.get_all_media_states()
        
        for app_name_lower in app_names_lower:
            # Check if any media state matches this app
            for state_app_name, state in media_states.items():
                # Match by partial name (e.g., "chrome" matches "chrome.exe")
                app_base = app_name_lower.replace('.exe', '')
                if app_base in state_app_name or state_app_name in app_base:
                    # Has a media session (either playing or paused)
                    logger.debug(f"Found active media session for {app_name_lower}: playing={state.is_playing}, paused={state.is_paused}")
                    return True
        
        return False
    
    def is_media_playing(self, app_names: list[str]) -> bool:
        """
        Check if any of the specified apps are actively playing media.
        Returns True only if media is currently playing (not paused).
        """
        if not self._available:
            return False
        
        app_names_lower = [name.lower() for name in app_names]
        media_states = self.get_all_media_states()
        
        for app_name_lower in app_names_lower:
            for state_app_name, state in media_states.items():
                app_base = app_name_lower.replace('.exe', '')
                if app_base in state_app_name or state_app_name in app_base:
                    if state.is_playing:
                        logger.debug(f"Media is actively playing in {app_name_lower}")
                        return True
        
        return False
    
    def is_media_paused(self, app_names: list[str]) -> bool:
        """
        Check if any of the specified apps have paused media.
        Returns True if there's a media session that is paused (not playing).
        """
        if not self._available:
            return False
        
        app_names_lower = [name.lower() for name in app_names]
        media_states = self.get_all_media_states()
        
        for app_name_lower in app_names_lower:
            for state_app_name, state in media_states.items():
                app_base = app_name_lower.replace('.exe', '')
                if app_base in state_app_name or state_app_name in app_base:
                    if state.is_paused:
                        logger.debug(f"Media is paused in {app_name_lower}")
                        return True
        
        return False
