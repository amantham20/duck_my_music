"""
Spotify Controller Module
Controls Spotify playback using Windows Media Transport Controls.
"""

import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# Global session manager
_session_manager = None
_spotify_session = None


async def get_spotify_session():
    """Get the Spotify media session using Windows Runtime APIs."""
    global _session_manager, _spotify_session
    
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as SessionManager
        )
        
        if _session_manager is None:
            _session_manager = await SessionManager.request_async()
        
        # Get all sessions and find Spotify
        sessions = _session_manager.get_sessions()
        
        for session in sessions:
            # Get the app info
            app_id = session.source_app_user_model_id
            if app_id and 'spotify' in app_id.lower():
                logger.debug(f"Found Spotify session: {app_id}")
                return session
        
        # If no Spotify found by app_id, try by source
        for session in sessions:
            try:
                info = await session.try_get_media_properties_async()
                if info:
                    # Check if it's from Spotify
                    app_id = session.source_app_user_model_id or ""
                    if 'spotify' in app_id.lower():
                        return session
            except Exception:
                pass
                
        logger.debug("Spotify session not found in media sessions")
        return None
        
    except Exception as e:
        logger.error(f"Error getting Spotify session: {e}")
        return None


async def pause_spotify_async() -> bool:
    """Pause Spotify using Windows Media Transport Controls."""
    try:
        session = await get_spotify_session()
        if session:
            await session.try_pause_async()
            logger.info("Spotify paused via Windows Media Controls")
            return True
        else:
            logger.warning("Could not find Spotify media session")
            return False
    except Exception as e:
        logger.error(f"Error pausing Spotify: {e}")
        return False


async def play_spotify_async() -> bool:
    """Resume Spotify using Windows Media Transport Controls."""
    try:
        session = await get_spotify_session()
        if session:
            await session.try_play_async()
            logger.info("Spotify resumed via Windows Media Controls")
            return True
        else:
            logger.warning("Could not find Spotify media session")
            return False
    except Exception as e:
        logger.error(f"Error resuming Spotify: {e}")
        return False


def run_async(coro):
    """Run an async function from sync code."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


class SpotifyController:
    """Controls Spotify playback state using Windows Media Transport Controls."""
    
    def __init__(self):
        self._is_paused_by_us = False
        self._available = False
        
        # Test if winsdk is available
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager
            )
            self._available = True
            logger.info("Spotify controller initialized (using Windows Media Controls)")
        except ImportError:
            logger.warning("winsdk not available, Spotify pause/play disabled")
    
    @property
    def is_paused_by_us(self) -> bool:
        """Returns True if we paused Spotify (so we know to resume it)."""
        return self._is_paused_by_us
    
    def pause(self) -> bool:
        """Pause Spotify playback."""
        if not self._available:
            return False
            
        if not self._is_paused_by_us:
            logger.info("Pausing Spotify...")
            if run_async(pause_spotify_async()):
                self._is_paused_by_us = True
                return True
        return False
    
    def play(self) -> bool:
        """Resume Spotify playback (only if we paused it)."""
        if not self._available:
            return False
            
        if self._is_paused_by_us:
            logger.info("Resuming Spotify...")
            if run_async(play_spotify_async()):
                self._is_paused_by_us = False
                return True
        return False
    
    def toggle(self) -> bool:
        """Toggle play/pause."""
        if self._is_paused_by_us:
            return self.play()
        else:
            return self.pause()
