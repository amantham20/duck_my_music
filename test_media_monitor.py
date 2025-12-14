"""
Test script to verify media state monitoring works correctly.
This demonstrates how the new logic distinguishes between paused and stopped media.
"""

import time
from media_state_monitor import MediaStateMonitor

def test_media_monitor():
    """Test the media state monitor."""
    print("=" * 60)
    print("Testing Media State Monitor")
    print("=" * 60)
    
    monitor = MediaStateMonitor()
    
    print(f"\nMonitor available: {monitor._available}")
    
    if not monitor._available:
        print("WARNING: Media monitor not available (winsdk not installed)")
        print("Install with: pip install winsdk")
        return
    
    test_apps = ["chrome.exe", "msedge.exe", "firefox.exe"]
    
    print(f"\nMonitoring apps: {', '.join(test_apps)}")
    print("\nInstructions:")
    print("1. Play a video in your browser")
    print("2. Pause the video")
    print("3. Close the tab/stop the video")
    print("\nPress Ctrl+C to stop monitoring\n")
    
    try:
        while True:
            states = monitor.get_all_media_states()
            
            print("\n" + "-" * 60)
            print(f"Time: {time.strftime('%H:%M:%S')}")
            
            if states:
                print("\nActive Media Sessions:")
                for app_name, state in states.items():
                    status = "▶ PLAYING" if state.is_playing else "⏸ PAUSED"
                    title = f" - {state.title}" if state.title else ""
                    print(f"  {app_name}: {status}{title}")
            else:
                print("\nNo active media sessions")
            
            # Test the key methods
            has_session = monitor.has_active_media_session(test_apps)
            is_playing = monitor.is_media_playing(test_apps)
            is_paused = monitor.is_media_paused(test_apps)
            
            print(f"\nStatus for monitored apps:")
            print(f"  Has active session: {has_session}")
            print(f"  Is playing: {is_playing}")
            print(f"  Is paused: {is_paused}")
            
            if has_session:
                if is_playing:
                    print("\n✓ Music should be DUCKED (media playing)")
                elif is_paused:
                    print("\n✓ Music should stay DUCKED (media paused, not stopped)")
            else:
                print("\n✓ Music should be RESTORED (no media session)")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nTest stopped by user")

if __name__ == "__main__":
    test_media_monitor()
