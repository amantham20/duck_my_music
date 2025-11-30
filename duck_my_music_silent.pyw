"""
Duck My Music - Windows .pyw launcher (no console window)
Double-click this file to run the application silently.
"""

import sys
import os

# Add the directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
os.chdir(script_dir)

# Import and run main
from duck_my_music import main

if __name__ == "__main__":
    main()
