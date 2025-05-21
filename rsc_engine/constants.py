# rsc_engine/constants.py
from pathlib import Path

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
TILE_WIDTH = 64
TILE_HEIGHT = 32
FPS = 60
DEV_SKIP_MENU_AND_CREATOR = True

# Stałe przeniesione z game.py
ASSETS = Path(__file__).resolve().parent / "assets" # Ta ścieżka będzie wskazywać na rsc_engine/assets
TARGET_CHAR_HEIGHT = int(TILE_HEIGHT * 2.2)
TARGET_SPLAT_ICON_WIDTH = 28
TARGET_SPLAT_ICON_HEIGHT = 28