"""
Phase 2 — Lunar solar power + battery model
Input:  python/ephemeris_shackleton_sun_24h.csv  (from Phase 1)
Output: python/power_shackleton_24h.csv
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. Power system parameters ---
AREA_M2          = 10.0      # solar array area (m^2)
CELL_EFF         = 0.30      # cell efficiency
SYS_EFF          = 0.85      # system efficiency (wiring, MPPT, packing)
IRRADIANCE_W_M2  = 1361.0    # solar constant at 1 AU
P_PEAK           = IRRADIANCE_W_M2 * AREA_M2 * CELL_EFF * SYS_EFF  # ~3470 W

LOAD_W           = 100.0     # constant load (W)
BATTERY_WH       = 5000.0    # 5 kWh battery
SOC_INIT         = 0.80      # initial state of charge
SOC_FLOOR        = 0.20      # below this, mission flagged as POWER_NEGATIVE
DT_HOURS         = 1.0       # timestep from Phase 1 output

# --- 2. Load Phase 1 data ---
script_dir = os.path.dirname(os.path.abspath(__file__))
in_path    = os.path.join(script_dir, "ephemeris_shackleton_sun_24h.csv")
df = pd.read_csv(in_path)
print(f"Loaded {len(df)} rows from Phase 1.")

# --- 3. Run the power model ---
# Tracking vertical array: panel rotates in azimuth to face the Sun.
# For a vertical panel facing the Sun, the incidence angle = Sun elevation.
# P = P_peak * cos(elevation)   when Sun is above horizon, else 0.

powers_w  = []
socs_wh   = []
soc_wh    = SOC_INIT * BATTERY_WH

for i, row in df.iterrows():
    el = row["sun_elevation_deg"]

    if el > 0:
        power = P_PEAK * np.cos(np.radians(el))
    else:
        power = 0.0

    powers_w.append(power)
    socs_wh.append(soc_wh)          # record SOC at start of interval

    # integrate SOC forward
    net = power - LOAD_W
    soc_wh += net * DT_HOURS
    soc_wh = max(0.0, min(BATTERY_WH, soc_wh))

# --- 4. Attach to dataframe ---
df["solar_power_w"] = powers_w
df["battery_wh"]    = socs_wh
df["battery_soc"]   = np.array(socs_wh) / BATTERY_WH

min_soc = df["battery_soc"].min()
verdict = "POWER_POSITIVE" if min_soc >= SOC_FLOOR else "POWER_NEGATIVE"
df["power_verdict"] = verdict

# --- 5. Save output ---
out_path = os.path.join(script_dir, "power_shackleton_24h.csv")
df.to_csv(out_path, index=False)

# --- 6. Print summary ---
print("\n=== POWER MODEL SUMMARY ===")
print(f"P_peak (tracking vertical array): {P_PEAK:.1f} W")
print(f"Constant load:                    {LOAD_W:.1f} W")
print(f"Battery capacity:                 {BATTERY_WH:.0f} Wh ({BATTERY_WH/1000:.1f} kWh)")
print(f"Initial SOC:                      {SOC_INIT*100:.1f}%")
print(f"Peak solar power observed:        {df['solar_power_w'].max():.1f} W")
print(f"Min solar power observed:         {df['solar_power_w'].min():.1f} W")
print(f"Final SOC:                        {df['battery_soc'].iloc[-1]*100:.1f}%")
print(f"Minimum SOC during mission:       {min_soc*100:.1f}%")
print(f"VERDICT:                          {verdict}")
print(f"\nSaved to {out_path}")

# --- 7. Plots ---
fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

axes[0].plot(df["datetime_utc"], df["solar_power_w"], "-o",
             color="gold", linewidth=2, label="Solar power (W)")
axes[0].axhline(LOAD_W, color="red", linestyle="--",
                label=f"Constant load ({LOAD_W:.0f} W)")
axes[0].set_ylabel("Power (W)")
axes[0].set_title("Shackleton Rim — Solar Power Generation")
axes[0].legend(loc="upper right")
axes[0].grid(True)
axes[0].set_ylim(-100, P_PEAK * 1.15)

axes[1].plot(df["datetime_utc"], df["battery_soc"]*100, "-o",
             color="green", linewidth=2, label="Battery SOC (%)")
axes[1].axhline(SOC_FLOOR*100, color="red", linestyle="--",
                label=f"SOC floor ({SOC_FLOOR*100:.0f}%)")
axes[1].axhline(100, color="gray", linestyle=":", label="Full")
axes[1].set_ylabel("Battery SOC (%)")
axes[1].set_xlabel("UTC Time")
axes[1].set_title(f"Battery State of Charge — Verdict: {verdict}")
axes[1].legend(loc="lower right")
axes[1].grid(True)
axes[1].set_ylim(-5, 105)

plt.xticks(rotation=45)
plt.tight_layout()
plot_path = os.path.join(script_dir, "step2_power_check.png")
plt.savefig(plot_path, dpi=110)
print(f"Plot saved to {plot_path}")
plt.show()