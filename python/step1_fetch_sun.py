"""
Phase 1 — Fetch Sun Alt/Az for Shackleton Rim from JPL Horizons
Output: python/ephemeris_shackleton_sun_24h.csv
"""

import os
import requests
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. Site and time parameters ---
SITE_NAME   = "Shackleton Rim"
SITE_LON    = -171.87      # east-positive longitude (degrees)
SITE_LAT    = -89.7668     # north-positive latitude  (negative = south)
SITE_ALT_KM = 0            # height above mean lunar sphere
START_TIME  = "2026-11-14"
STOP_TIME   = "2026-11-15"
STEP_SIZE   = "1 h"

# --- 2. Build the JPL Horizons API request ---
url = "https://ssd.jpl.nasa.gov/api/horizons.api"
params = {
    "format":       "text",
    "COMMAND":      "'10'",                       # 10 = Sun
    "CENTER":       "'coord@301'",                # coordinates on body 301 = Moon
    "COORD_TYPE":   "'GEODETIC'",                 # only GEODETIC / CYLINDRICAL are valid
    "SITE_COORD":   f"'{SITE_LON},{SITE_LAT},{SITE_ALT_KM}'",
    "EPHEM_TYPE":   "'OBSERVER'",
    "QUANTITIES":   "'4'",                        # 4 = Azimuth + Elevation
    "START_TIME":   f"'{START_TIME}'",
    "STOP_TIME":    f"'{STOP_TIME}'",
    "STEP_SIZE":    f"'{STEP_SIZE}'",
    "CAL_FORMAT":   "'CAL'",
    "TIME_DIGITS":  "'MINUTES'",
    "ANG_FORMAT":   "'DEG'",
    "CSV_FORMAT":   "'YES'",
    "OBJ_DATA":     "'NO'",                       # trims header noise
}

print("Querying JPL Horizons for", SITE_NAME, "...")
response = requests.get(url, params=params, timeout=60)
response.raise_for_status()
text = response.text

# --- 3. Extract CSV block between $$SOE and $$EOE ---
soe = text.find("$$SOE")
eoe = text.find("$$EOE")
if soe == -1 or eoe == -1:
    print("ERROR: Could not find data markers.")
    print("First 3000 characters of response:")
    print(text[:3000])
    raise SystemExit(1)

csv_block = text[soe + 5 : eoe].strip()

# --- 4. Parse each row ---
# Horizons returns e.g.:
#   2026-Nov-14 00:00,*, , 298.481697, 1.667824,
# The '*' is a solar-presence flag, and there's a trailing comma.
# Keep only non-empty fields, then take the last two as az/el.
rows = []
for line in csv_block.split("\n"):
    line = line.strip()
    if not line:
        continue
    parts = [p.strip() for p in line.split(",") if p.strip()]
    if len(parts) < 3:
        continue
    try:
        az = float(parts[-2])
        el = float(parts[-1])
    except ValueError:
        continue
    rows.append({
        "datetime_utc":      parts[0],
        "sun_azimuth_deg":   az,
        "sun_elevation_deg": el,
    })

df = pd.DataFrame(rows)
df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])
print(f"Parsed {len(df)} rows.")

if df.empty:
    raise SystemExit("ERROR: parsed 0 rows. Horizons output format may have changed.")

# --- 5. Save CSV next to this script ---
script_dir = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(script_dir, "ephemeris_shackleton_sun_24h.csv")
df.to_csv(out_path, index=False)
print(f"Saved to {out_path}")

# --- 6. Print quick verification numbers ---
print("\nFirst 3 rows:")
print(df.head(3).to_string())
print("\nLast 3 rows:")
print(df.tail(3).to_string())
print(f"\nElevation range: {df['sun_elevation_deg'].min():.2f}°  to  {df['sun_elevation_deg'].max():.2f}°")
print(f"Azimuth range:   {df['sun_azimuth_deg'].min():.2f}°  to  {df['sun_azimuth_deg'].max():.2f}°")

# --- 7. Draw a sanity-check plot ---
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

axes[0].plot(df["datetime_utc"], df["sun_elevation_deg"], "-o", color="gold")
axes[0].axhline(0, color="red", linestyle="--", label="Horizon (0°)")
axes[0].set_ylabel("Sun Elevation (°)")
axes[0].set_title(f"{SITE_NAME} — Sun Elevation (geometric)")
axes[0].grid(True)
axes[0].legend()

axes[1].plot(df["datetime_utc"], df["sun_azimuth_deg"], "-o", color="orange")
axes[1].set_ylabel("Sun Azimuth (°)")
axes[1].set_title(f"{SITE_NAME} — Sun Azimuth")
axes[1].grid(True)

fig.autofmt_xdate(rotation=45)
plt.tight_layout()

plot_path = os.path.join(script_dir, "step1_sanity_check.png")
plt.savefig(plot_path, dpi=100)
print(f"\nPlot saved to {plot_path}")
plt.show()