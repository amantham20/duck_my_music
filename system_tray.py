"""
System Tray Module
Provides system tray icon and menu for the application.
"""

import logging
import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def create_tray_icon_image(color: str = "#1DB954", size: int = 64) -> Image.Image:
    """Create a simple icon for the system tray."""
    # Create a simple speaker/music icon
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Parse color
    if color.startswith('#'):
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        fill_color = (r, g, b, 255)
    else:
        fill_color = (29, 185, 84, 255)  # Spotify green
    
    # Draw a speaker-like shape
    margin = size // 8
    
    # Speaker body (rectangle)
    body_left = margin
    body_right = size // 3
    body_top = size // 3
    body_bottom = 2 * size // 3
    draw.rectangle([body_left, body_top, body_right, body_bottom], fill=fill_color)
    
    # Speaker cone (triangle)
    cone_points = [
        (body_right, body_top - margin),
        (size // 2, margin),
        (size // 2, size - margin),
        (body_right, body_bottom + margin)
    ]
    draw.polygon(cone_points, fill=fill_color)
    
    # Sound waves (arcs)
    wave_center = (size // 2, size // 2)
    for i in range(1, 4):
        arc_size = (size // 4) + (i * size // 8)
        bbox = [
            wave_center[0] - arc_size // 2,
            wave_center[1] - arc_size,
            wave_center[0] + arc_size,
            wave_center[1] + arc_size
        ]
        # Draw arc segments
        draw.arc(bbox, -60, 60, fill=fill_color, width=3)
    
    return image


class SystemTray:
    """System tray icon manager."""
    
    def __init__(
        self,
        on_toggle: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_show: Optional[Callable] = None
    ):
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.on_show = on_show
        
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._enabled = True
        self._running = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        self._update_icon()
    
    def _update_icon(self):
        """Update the tray icon based on current state."""
        if self._icon:
            color = "#1DB954" if self._enabled else "#666666"
            self._icon.icon = create_tray_icon_image(color)
    
    def _create_menu(self):
        """Create the system tray menu."""
        import pystray
        
        def show_window(icon, item):
            if self.on_show:
                self.on_show()
        
        def toggle_enabled(icon, item):
            self._enabled = not self._enabled
            self._update_icon()
            if self.on_toggle:
                self.on_toggle(self._enabled)
        
        def quit_app(icon, item):
            logger.info("Quit requested from tray")
            if self.on_quit:
                self.on_quit()
            self.stop()
        
        return pystray.Menu(
            pystray.MenuItem("Show Window", show_window, default=True),
            pystray.MenuItem(
                lambda text: "✓ Enabled" if self._enabled else "○ Disabled",
                toggle_enabled
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Duck My Music", quit_app)
        )
    
    def start(self):
        """Start the system tray icon."""
        try:
            import pystray
            
            self._icon = pystray.Icon(
                name="DuckMyMusic",
                icon=create_tray_icon_image(),
                title="Duck My Music",
                menu=self._create_menu()
            )
            
            self._running = True
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()
            logger.info("System tray started")
            
        except ImportError:
            logger.warning("pystray not available, running without system tray")
        except Exception as e:
            logger.error(f"Failed to start system tray: {e}")
    
    def stop(self):
        """Stop the system tray icon."""
        self._running = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        logger.info("System tray stopped")
    
    def notify(self, title: str, message: str):
        """Show a notification from the tray icon."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception as e:
                logger.debug(f"Could not show notification: {e}")
