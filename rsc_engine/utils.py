"""Utility helpers used throughout the engine."""
from rsc_engine import constants as C

def iso_to_screen(ix: int, iy: int):
    """Convert isometric map (tile) coordinates to 2D screen pixel coordinates."""
    sx = (ix - iy) * (C.TILE_WIDTH // 2)
    sy = (ix + iy) * (C.TILE_HEIGHT // 2)
    return sx, sy

def screen_to_iso(sx: int, sy: int):
    """Convert 2D screen pixel coordinates back to iso tile indices."""
    ix = (sx // (C.TILE_WIDTH // 2) + sy // (C.TILE_HEIGHT // 2)) // 2
    iy = (sy // (C.TILE_HEIGHT // 2) - (sx // (C.TILE_WIDTH // 2))) // 2
    return ix, iy
