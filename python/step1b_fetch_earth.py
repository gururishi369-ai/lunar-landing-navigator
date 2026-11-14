# python/step1b_fetch_earth.py
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt

# --- Site parameters (same as Phase 1) ---
SITE_NAME   = "Shackleton Rim"
SITE_LON    = -171.87
SITE_LAT    = -89.7668
SITE_ALT_KM = 0
START_TIME  = "2026-11-14"
STOP_TIME   = "2026-11-15"
STEP_SIZE   = "1 h"

url = "https://ssd.jpl.nasa.gov/api/horizons.api"
params = {
    "format":       "text",
    "COMMAND":      "'399'",  # <-- THE ONLY CRITICAL CHANGE: 399 = Earth
    "CENTER":       "'coord'",
    "COORD_TYPE":   "'PLANETOCENTRIC'",
    "SITE_COORD":   f"'{SITE_LON},{SITE_LAT},{SITE_ALT_KM}'",
    "EPHEM_TYPE":   "'OBSERVER'",
    "QUANTITIES":   "'4'",
    "START_TIME":   f"'{START_TIME}'",
    "STOP_TIME":    f"'{STOP_TIME}'",
    "STEP_SIZE":    f"'{STEP_SIZE}'",
    "CAL_FORMAT":   "'CAL'",
    "TIME_DIGITS":  "'MINUTES'",
    "ANG_FORMAT":   "'DEG'",
    "CSV_FORMAT":   "'YES'",
}

# ... (The rest of the data fetching, parsing, and saving logic is identical to step1_fetch_sun.py)
# ... (Just change the output filename to ephemeris_shackleton_earth_24h.csv)