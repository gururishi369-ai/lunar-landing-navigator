"""
Phase 5 — Interactive Multi-site Dashboard with Animations & Custom Theme
"""

import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# 1. Page setup
# ============================================================
st.set_page_config(
    page_title="Lunar Landing Site Navigator",
    page_icon=":material/rocket_launch:",
    layout="wide",
)

st.title(":material/public: Lunar Landing Site Navigator")
st.caption(
    "Space Apps 2026 — Rapid site evaluation for lunar south-pole missions. "
    "Sun and Earth positions from JPL Horizons. Power model: vertical tracking array + battery."
)

# ============================================================
# 2. Load Data
# ============================================================
@st.cache_data
def load_data():
    candidates = [
        "web/data/all_sites_7day.csv",
        "data/all_sites_7day.csv",
        "../python/all_sites_7day.csv",
    ]
    for path in candidates:
        if os.path.exists(path):
            return pd.read_csv(path), path
    st.error("Could not find all_sites_7day.csv. Run phase4_generate_all_data.py first.")
    st.stop()

df, loaded_path = load_data()
df["datetime_utc"] = pd.to_datetime(df["datetime_utc"])

# ============================================================
# 3. Sidebar Configuration
# ============================================================
st.sidebar.header(":material/settings: Configuration")
site_names = df["site_name"].unique().tolist()
selected_site = st.sidebar.selectbox("Select a Landing Site", site_names)

site_df = df[df["site_name"] == selected_site].copy()

# ============================================================
# 4. Header Metrics
# ============================================================
st.subheader(f":material/location_on: {selected_site} — Mission Overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Mean Solar Power", f"{site_df['solar_power_w'].mean():.0f} W", border=True)
c2.metric("Min Battery SOC", f"{site_df['battery_soc'].min()*100:.1f}%", border=True)

earth_vis_pct = site_df["earth_visible_geom"].mean() * 100
c3.metric("Earth Visibility", f"{earth_vis_pct:.1f}%", border=True)

verdict = site_df["power_verdict"].iloc[0]
c4.metric("Power Verdict", verdict.replace("_", " "), border=True)

st.space("medium")

# ============================================================
# 5. Interactive Polar Plot (Animation)
# ============================================================
st.subheader(f":material/explore: {selected_site} — Sun and Earth Paths Over Time")
st.caption("Use the slider to animate the Sun (gold) and Earth (blue) positions over the 7-day window.")

# Create unique timestamps for the slider
time_steps = site_df['datetime_utc'].dt.strftime('%Y-%m-%d %H:%M').unique()

# Let user pick a specific time to inspect
selected_time = st.select_slider(
    "Timeline (UTC)",
    options=time_steps,
    value=time_steps[0]
)

# Filter data for the selected time
frame_df = site_df[site_df['datetime_utc'].dt.strftime('%Y-%m-%d %H:%M') == selected_time]

fig_polar = go.Figure()

# Horizon ring (static)
fig_polar.add_trace(go.Scatterpolar(
    r=[90]*73, theta=list(range(0, 361, 5)),
    mode="lines", line=dict(color="red", width=2, dash="dash"),
    name="Horizon", hoverinfo="skip"
))

# Sun trace for selected time
if not frame_df.empty:
    fig_polar.add_trace(go.Scatterpolar(
        r=[90 - frame_df['sun_elevation_deg'].iloc[0]],
        theta=[frame_df['sun_azimuth_deg'].iloc[0]],
        mode="markers",
        marker=dict(size=18, color="gold", line=dict(color="orange", width=2), symbol="circle"),
        name="Sun",
        hovertemplate="<b>Sun</b><br>Azimuth: %{theta:.1f}°<br>Elevation: %{text:.2f}°<extra></extra>",
        text=[frame_df['sun_elevation_deg'].iloc[0]]
    ))

    # Earth trace for selected time
    fig_polar.add_trace(go.Scatterpolar(
        r=[90 - frame_df['earth_elevation_deg'].iloc[0]],
        theta=[frame_df['earth_azimuth_deg'].iloc[0]],
        mode="markers",
        marker=dict(size=14, color="deepskyblue", line=dict(color="blue", width=1), symbol="diamond"),
        name="Earth",
        hovertemplate="<b>Earth</b><br>Azimuth: %{theta:.1f}°<br>Elevation: %{text:.2f}°<extra></extra>",
        text=[frame_df['earth_elevation_deg'].iloc[0]]
    ))

fig_polar.update_layout(
    polar=dict(
        radialaxis=dict(range=[60, 91], tickvals=[60, 70, 80, 85, 88, 89, 90], ticktext=["30°", "20°", "10°", "5°", "2°", "1°", "0°"], angle=90),
        angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0,45,90,135,180,225,270,315], ticktext=["N","NE","E","SE","S","SW","W","NW"])
    ),
    showlegend=True,
    height=500,
    margin=dict(l=20, r=20, t=20, b=20),
)
st.plotly_chart(fig_polar, width="stretch")

st.info(f"This site has **{earth_vis_pct:.1f}%** geometric Earth visibility over the 7-day window. This is critical for direct-to-Earth communication.")

st.space("medium")

# ============================================================
# 6. Power & Battery Chart
# ============================================================
st.subheader(f":material/bolt: {selected_site} — Power and Battery")
fig_power = go.Figure()
fig_power.add_trace(go.Scatter(x=site_df["datetime_utc"], y=site_df["solar_power_w"], mode="lines", name="Solar Power (W)", line=dict(color="gold", width=3)))
fig_power.add_trace(go.Scatter(x=site_df["datetime_utc"], y=site_df["battery_soc"]*100, mode="lines", name="Battery SOC (%)", yaxis="y2", line=dict(color="seagreen", width=2, dash="dot")))

fig_power.update_layout(
    xaxis=dict(title="UTC Time"),
    yaxis=dict(title="Solar Power (W)", side="left"),
    yaxis2=dict(title="Battery SOC (%)", overlaying="y", side="right", range=[0,110]),
    legend=dict(x=0.02, y=0.98),
    height=400,
    hovermode="x unified",
)
st.plotly_chart(fig_power, width="stretch")

st.space("medium")

# ============================================================
# 7. Multi-Site Comparison Table
# ============================================================
st.subheader(":material/table_chart: Site Comparison — Key Metrics (7-Day Average)")
comparison_data = []
for name, group in df.groupby("site_name"):
    comparison_data.append({
        "Site": name,
        "Mean Solar Power (W)": f"{group['solar_power_w'].mean():.0f}",
        "Min Battery SOC (%)": f"{group['battery_soc'].min()*100:.1f}",
        "Earth Visibility (%)": f"{group['earth_visible_geom'].mean()*100:.1f}",
        "Power Verdict": group["power_verdict"].iloc[0].replace("_", " "),
    })
st.dataframe(pd.DataFrame(comparison_data), width="stretch", hide_index=True)

# ============================================================
# 8. Limitations
# ============================================================
with st.expander(":material/warning: Limitations & Assumptions"):
    st.markdown("""
    - **Geometric visibility only** — terrain shadowing (mountains, crater rims) is **not yet included**.
    - **Power model** is a simplified energy balance: tracking vertical array + constant load + battery.
    - **Ephemeris source:** JPL Horizons API.
    - **Benchmark:** Connecting Ridge (C1) is a published benchmark site with ~85.7% integral illumination. Your results will be compared against this.
    """)