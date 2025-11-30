"""
Duck My Music GUI - Silent Launcher (.pyw)
Double-click this file to run the GUI without a console window.
"""

import sys
import os

# Add the directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
os.chdir(script_dir)

if __name__ == "__main__":
    # Check for --minimized argument
    start_minimized = '--minimized' in sys.argv
    
    # Import here to avoid self-import when this is imported as module
    import duck_my_music_gui as gui_module
    
    app = gui_module.DuckMyMusicGUI(start_minimized=start_minimized)
    app.run()
