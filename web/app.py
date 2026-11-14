"""
Phase 3 — Lunar Landing Site Navigator web app.
Reads real ephemeris + power data and renders:
  - Metric cards
  - Polar plot of Sun relative to horizon
  - Power generation + battery SOC chart
"""

import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# Page setup
# ============================================================
st.set_page_config(
    page_title="Lunar Landing Site Navigator",
    page_icon="🌙",
    layout="wide",
)

st.title("🌙 Lunar Landing Site Navigator")
st.caption(
    "Space Apps 2026 — Rapid site evaluation for lunar south-pole missions. "
    "Sun positions from JPL Horizons. Power model: vertical tracking array + battery."
)

# ============================================================
# Load data
# ============================================================
@st.cache_data
def load_data():
    candidates = [
        "web/data/power_shackleton_24h.csv",       # Streamlit Cloud (repo root)
        "data/power_shackleton_24h.csv",            # local run from inside web/
        "../python/power_shackleton_24h.csv",       # fallback
        "power_shackleton_24h.csv",                 # last resort
    ]
    for path in candidates:
        if os.path.exists(path):
            return pd.read_csv(path), path
    st.error(
        "Could not find power_shackleton_24h.csv. "
        "Make sure it exists in `web/data/`."
    )
    st.stop()

df, loaded_path = load_data()

# Make sure timestamp column is datetime for plotting
df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])

# ============================================================
# Derived metrics
# ============================================================
sun_min = df["sun_elevation_deg"].min()
sun_max = df["sun_elevation_deg"].max()
sun_mean = df["sun_elevation_deg"].mean()
verdict = df["power_verdict"].iloc[0]
min_soc = df["battery_soc"].min()
mean_power = df["solar_power_w"].mean()

# ============================================================
# Header metric cards
# ============================================================
st.subheader("Shackleton Rim — Mission Overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    label="Site",
    value="Shackleton Rim",
    delta=f"{sun_mean:.2f}° mean Sun elevation",
)
c2.metric(
    label="Sun Elevation Range",
    value=f"{sun_min:.2f}° → {sun_max:.2f}°",
    delta="Above horizon: entire 24h" if sun_min > 0 else "Sunset during window",
)
c3.metric(
    label="Mean Solar Power",
    value=f"{mean_power:.0f} W",
    delta=f"Battery min {min_soc*100:.0f}%",
)
c4.metric(
    label="Power Verdict",
    value=verdict.replace("_", " "),
    delta="✔ Mission viable" if verdict == "POWER_POSITIVE" else "✘ Battery drained",
)

st.divider()

# ============================================================
# Polar plot — Sun position relative to horizon
# ============================================================
st.subheader("☀️ Sun Position Relative to Horizon")
st.caption(
    "Azimuth = compass angle around the site (0°=N, 90°=E, 180°=S, 270°=W). "
    "Radius = elevation above horizon (outer dashed circle = horizon at 0°, center = zenith at 90°). "
    "The Sun hugs the horizon at the pole — this is the entire engineering challenge."
)

fig_polar = go.Figure()

# Horizon ring at r = 90 (which corresponds to elevation = 0)
theta_ring = list(range(0, 361, 5))
fig_polar.add_trace(
    go.Scatterpolar(
        r=[90] * len(theta_ring),
        theta=theta_ring,
        mode="lines",
        line=dict(color="red", width=2, dash="dash"),
        name="Horizon (0°)",
        hoverinfo="skip",
    )
)

# Sun path — r = 90 − elevation, so higher Sun = smaller r
sun_r = 90 - df["sun_elevation_deg"]
fig_polar.add_trace(
    go.Scatterpolar(
        r=sun_r,
        theta=df["sun_azimuth_deg"],
        mode="lines+markers",
        line=dict(color="gold", width=3),
        marker=dict(size=9, color="gold", line=dict(color="orange", width=1)),
        name="Sun path (24h)",
        hovertemplate=(
            "<b>%{customdata}</b><br>"
            "Azimuth: %{theta:.2f}°<br>"
            "Elevation: %{text:.3f}°<extra></extra>"
        ),
        customdata=df["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M"),
        text=df["sun_elevation_deg"],
    )
)

fig_polar.update_layout(
    polar=dict(
        radialaxis=dict(
            range=[80, 91],
            tickvals=[80, 85, 88, 89, 90],
            ticktext=["10°", "5°", "2°", "1°", "0°"],
            angle=90,
            tickangle=90,
        ),
        angularaxis=dict(
            rotation=90,
            direction="clockwise",
            thetaunit="degrees",
            tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
            ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
        ),
    ),
    showlegend=True,
    height=540,
    margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(fig_polar, use_container_width=True)

st.info(
    f"**Why this matters:** The Sun stays between **{sun_min:.2f}° and {sun_max:.2f}°** above the horizon "
    f"for the entire 24-hour window. A horizontal panel would collect almost nothing (cos 88° ≈ 0.03). "
    f"This is why polar missions use **vertical, tracking arrays** — exactly what the power model assumes."
)

st.divider()

# ============================================================
# Power chart
# ============================================================
st.subheader("⚡ Solar Power & Battery State of Charge")
st.caption(
    f"Tracking vertical array (10 m², 30% cell, 85% system). Peak power ≈ "
    f"{df['solar_power_w'].max():.0f} W. Load = 100 W. Battery = 5 kWh."
)

fig_power = go.Figure()

fig_power.add_trace(
    go.Scatter(
        x=df["datetime_utc"],
        y=df["solar_power_w"],
        mode="lines+markers",
        name="Solar power (W)",
        line=dict(color="gold", width=3),
        marker=dict(size=6),
    )
)
fig_power.add_trace(
    go.Scatter(
        x=df["datetime_utc"],
        y=df["battery_soc"] * 100,
        mode="lines",
        name="Battery SOC (%)",
        yaxis="y2",
        line=dict(color="seagreen", width=3, dash="dot"),
    )
)

fig_power.update_layout(
    xaxis=dict(title="UTC time"),
    yaxis=dict(title="Solar power (W)", side="left", range=[-100, df["solar_power_w"].max() * 1.2]),
    yaxis2=dict(title="Battery SOC (%)", overlaying="y", side="right", range=[0, 110]),
    legend=dict(x=0.02, y=0.98),
    height=420,
    hovermode="x unified",
)
st.plotly_chart(fig_power, use_container_width=True)

st.divider()

# ============================================================
# Raw data + limitations
# ============================================================
with st.expander("📊 View raw data"):
    st.dataframe(df, use_container_width=True)
    st.caption(f"Loaded from: `{loaded_path}` — {len(df)} rows")

with st.expander("⚠️ Limitations & assumptions"):
    st.markdown(
        """
        - **Geometric visibility only** — terrain shadowing (mountains, crater rims) is **not yet included**. Phase 4–5 will add this.
        - **Power model** is a simplified energy balance: tracking vertical array + constant load + battery. Not flight-qualified.
        - **Ephemeris source:** JPL Horizons API (`ssd.jpl.nasa.gov/api/horizons.api`), Sun as observed from `(-171.87°, -89.7668°)` on the Moon.
        - **No Earth data yet** — Earth visibility windows will be added in Phase 4 for the comm-link analysis.
        """
    )