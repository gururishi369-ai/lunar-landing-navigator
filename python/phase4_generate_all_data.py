"""
Phase 4 — Multi-site data generation for Sun, Earth, and Power.
Output: python/all_sites_7day.csv
"""

import os
import requests
import pandas as pd
import numpy as np
import time

# --- 1. Define Sites (Validated Coordinates) ---
SITES = [
    {
        "site_id": "shackleton_rim",
        "site_name": "Shackleton Rim",
        "latitude": -89.7668,
        "longitude": -171.8700,
    },
    {
        "site_id": "connecting_ridge_c1",
        "site_name": "Connecting Ridge (C1)",
        "latitude": -89.406,
        "longitude": -136.2,
    },
    {
        "site_id": "malapert_massif",
        "site_name": "Malapert Massif",
        "latitude": -85.9,
        "longitude": -2.9,
    },
    {
        "site_id": "de_gerlache_rim",
        "site_name": "de Gerlache Rim",
        "latitude": -88.5,
        "longitude": -87.5,
    },
]

# --- 2. Time Range: 7 days for a meaningful comparison ---
START_TIME = "2026-11-14"
STOP_TIME  = "2026-11-21"
STEP_SIZE  = "1 h"

# --- 3. Power Model Parameters ---
AREA_M2 = 10.0
CELL_EFF = 0.30
SYS_EFF = 0.85
IRRADIANCE_W_M2 = 1361.0
P_PEAK = IRRADIANCE_W_M2 * AREA_M2 * CELL_EFF * SYS_EFF
LOAD_W = 100.0
BATTERY_WH = 5000.0
SOC_INIT = 0.80
SOC_FLOOR = 0.20
DT_HOURS = 1.0

# --- 4. Function to fetch ephemeris for a single target ---
def fetch_ephemeris(target_id, site):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    params = {
        "format": "text",
        "COMMAND": f"'{target_id}'",
        "CENTER": "'coord@301'",          # FIXED: Moon body ID
        "COORD_TYPE": "'GEODETIC'",       # FIXED: Valid coordinate type
        "SITE_COORD": f"'{site['longitude']},{site['latitude']},0'",
        "EPHEM_TYPE": "'OBSERVER'",
        "QUANTITIES": "'4'",  # Azimuth & Elevation
        "START_TIME": f"'{START_TIME}'",
        "STOP_TIME": f"'{STOP_TIME}'",
        "STEP_SIZE": f"'{STEP_SIZE}'",
        "CAL_FORMAT": "'CAL'",
        "TIME_DIGITS": "'MINUTES'",
        "ANG_FORMAT": "'DEG'",
        "CSV_FORMAT": "'YES'",
    }
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        text = response.text
        soe = text.find("$$SOE")
        eoe = text.find("$$EOE")
        if soe == -1 or eoe == -1:
            return None
        csv_block = text[soe + 5 : eoe].strip()
        
        # FIXED: Robust parser that ignores the '*' flag and trailing commas
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
            rows.append({"datetime_utc": parts[0], "az_deg": az, "el_deg": el})
            
        df = pd.DataFrame(rows)
        df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])
        return df
    except Exception as e:
        print(f"Error fetching {target_id} for {site['site_name']}: {e}")
        return None

# --- 5. Main Generation Loop ---
print("Starting multi-site data generation...")
all_site_dfs = []

for i, site in enumerate(SITES):
    print(f"Processing {site['site_name']} ({i+1}/{len(SITES)})...")
    
    # Fetch Sun and Earth data
    sun_df = fetch_ephemeris("10", site)
    earth_df = fetch_ephemeris("399", site)
    
    if sun_df is None or earth_df is None:
        print(f"  -> SKIPPING {site['site_name']} due to API error.")
        continue
    
    # Merge on datetime
    merged = pd.merge(
        sun_df.rename(columns={"az_deg": "sun_azimuth_deg", "el_deg": "sun_elevation_deg"}),
        earth_df.rename(columns={"az_deg": "earth_azimuth_deg", "el_deg": "earth_elevation_deg"}),
        on="datetime_utc",
        how="inner"
    )
    
    # Add site info
    merged["site_id"] = site["site_id"]
    merged["site_name"] = site["site_name"]
    merged["latitude"] = site["latitude"]
    merged["longitude"] = site["longitude"]
    
    # Power Model
    powers_w = []
    socs_wh = []
    soc_wh = SOC_INIT * BATTERY_WH
    for _, row in merged.iterrows():
        el = row["sun_elevation_deg"]
        power = P_PEAK * np.cos(np.radians(el)) if el > 0 else 0.0
        powers_w.append(power)
        socs_wh.append(soc_wh)
        soc_wh = max(0.0, min(BATTERY_WH, soc_wh + (power - LOAD_W) * DT_HOURS))
    
    merged["solar_power_w"] = powers_w
    merged["battery_soc"] = np.array(socs_wh) / BATTERY_WH
    
    min_soc = merged["battery_soc"].min()
    merged["power_verdict"] = "POWER_POSITIVE" if min_soc >= SOC_FLOOR else "POWER_NEGATIVE"
    merged["earth_visible_geom"] = (merged["earth_elevation_deg"] > 0).astype(int)
    
    all_site_dfs.append(merged)
    print(f"  -> Success. {len(merged)} rows.")
    time.sleep(1)  # Be polite to the API

# --- 6. Combine and Save ---
if all_site_dfs:
    final_df = pd.concat(all_site_dfs, ignore_index=True)
    # Reorder columns to match schema
    final_df = final_df[[
        "site_id", "site_name", "latitude", "longitude", "datetime_utc",
        "sun_azimuth_deg", "sun_elevation_deg",
        "earth_azimuth_deg", "earth_elevation_deg",
        "solar_power_w", "battery_soc", "power_verdict", "earth_visible_geom"
    ]]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "all_sites_7day.csv")
    final_df.to_csv(out_path, index=False)
    print(f"\n✅ SUCCESS: Saved {len(final_df)} rows for {len(all_site_dfs)} sites to {out_path}")
    
    # Print a quick summary
    print("\n--- Summary by Site ---")
    for site_id, group in final_df.groupby("site_id"):
        name = group["site_name"].iloc[0]
        earth_vis_pct = group["earth_visible_geom"].mean() * 100
        min_soc = group["battery_soc"].min() * 100
        verdict = group["power_verdict"].iloc[0]
        print(f"{name}: Earth Visible {earth_vis_pct:.1f}% | Min SOC {min_soc:.1f}% | {verdict}")
else:
    print("No data generated. Check API connectivity.")