"""Domain layer: entities, value objects, and ports (interfaces).

No infrastructure imports allowed here (no sqlite3, no yaml, no argparse, no
logging handlers). This is the hexagon's inside — adapters depend on it, never
the other way around.
"""
