"""
Phase 4 — Multi-site comparison dashboard.
Reads python/all_sites_7day.csv
"""

import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Lunar Landing Site Navigator",
    page_icon="🌙",
    layout="wide",
)

st.title("🌙 Lunar Landing Site Navigator")
st.caption(
    "Space Apps 2026 — Multi-site comparison for lunar south-pole missions. "
    "Sun and Earth positions from JPL Horizons. Power model: vertical tracking array + battery."
)

# --- 1. Load Data ---
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

# --- 2. Site Selector ---
st.sidebar.header("Configuration")
site_names = df["site_name"].unique().tolist()
selected_site = st.sidebar.selectbox("Select a Landing Site", site_names)

site_df = df[df["site_name"] == selected_site].copy()

# --- 3. Header Metrics for Selected Site ---
st.subheader(f"📍 {selected_site} — Mission Overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Mean Solar Power", f"{site_df['solar_power_w'].mean():.0f} W")
c2.metric("Min Battery SOC", f"{site_df['battery_soc'].min()*100:.1f}%")
earth_vis_pct = site_df["earth_visible_geom"].mean() * 100
c3.metric("Earth Visibility", f"{earth_vis_pct:.1f}%")
verdict = site_df["power_verdict"].iloc[0]
c4.metric("Power Verdict", verdict.replace("_", " "))

st.divider()

# --- 4. Polar Plot for Selected Site ---
st.subheader(f"☀️ {selected_site} — Sun and Earth Paths")
st.caption("Horizon at 0°, zenith at 90°. The Sun (gold) and Earth (blue) hug the horizon at the pole.")

fig_polar = go.Figure()
# Horizon ring
fig_polar.add_trace(go.Scatterpolar(r=[90]*73, theta=list(range(0, 361, 5)), mode="lines", line=dict(color="red", width=2, dash="dash"), name="Horizon"))

# Sun path
sun_r = 90 - site_df["sun_elevation_deg"]
fig_polar.add_trace(go.Scatterpolar(r=sun_r, theta=site_df["sun_azimuth_deg"], mode="lines+markers", line=dict(color="gold", width=2), marker=dict(size=4), name="Sun Path", text=site_df["sun_elevation_deg"], hovertemplate="Az: %{theta:.1f}°<br>El: %{text:.2f}°<extra></extra>"))

# Earth path
earth_r = 90 - site_df["earth_elevation_deg"]
fig_polar.add_trace(go.Scatterpolar(r=earth_r, theta=site_df["earth_azimuth_deg"], mode="lines+markers", line=dict(color="deepskyblue", width=2, dash="dot"), marker=dict(size=4, symbol="diamond"), name="Earth Path", text=site_df["earth_elevation_deg"], hovertemplate="Az: %{theta:.1f}°<br>El: %{text:.2f}°<extra></extra>"))

fig_polar.update_layout(polar=dict(radialaxis=dict(range=[70, 91], tickvals=[70, 80, 85, 88, 89, 90], ticktext=["20°","10°","5°","2°","1°","0°"], angle=90), angularaxis=dict(rotation=90, direction="clockwise")), showlegend=True, height=500, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig_polar, use_container_width=True)
st.info(f"This site has **{earth_vis_pct:.1f}%** geometric Earth visibility over the 7-day window. This is critical for direct-to-Earth communication.")

st.divider()

# --- 5. Power & Battery Chart ---
st.subheader(f"⚡ {selected_site} — Power and Battery")
fig_power = go.Figure()
fig_power.add_trace(go.Scatter(x=site_df["datetime_utc"], y=site_df["solar_power_w"], mode="lines", name="Solar Power (W)", line=dict(color="gold", width=2)))
fig_power.add_trace(go.Scatter(x=site_df["datetime_utc"], y=site_df["battery_soc"]*100, mode="lines", name="Battery SOC (%)", yaxis="y2", line=dict(color="seagreen", width=2, dash="dot")))
fig_power.update_layout(xaxis=dict(title="UTC Time"), yaxis=dict(title="Solar Power (W)", side="left"), yaxis2=dict(title="Battery SOC (%)", overlaying="y", side="right", range=[0,110]), legend=dict(x=0.02, y=0.98), height=400, hovermode="x unified")
st.plotly_chart(fig_power, use_container_width=True)

st.divider()

# --- 6. Multi-Site Comparison Table ---
st.subheader("📊 Site Comparison — Key Metrics (7-Day Average)")
comparison_data = []
for name, group in df.groupby("site_name"):
    comparison_data.append({
        "Site": name,
        "Mean Solar Power (W)": f"{group['solar_power_w'].mean():.0f}",
        "Min Battery SOC (%)": f"{group['battery_soc'].min()*100:.1f}",
        "Earth Visibility (%)": f"{group['earth_visible_geom'].mean()*100:.1f}",
        "Power Verdict": group["power_verdict"].iloc[0].replace("_", " "),
    })
st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

# --- 7. Limitations ---
with st.expander("⚠️ Limitations & Assumptions"):
    st.markdown("""
    - **Geometric visibility only** — terrain shadowing (mountains, crater rims) is **not yet included**.
    - **Power model** is a simplified energy balance: tracking vertical array + constant load + battery.
    - **Ephemeris source:** JPL Horizons API.
    - **Benchmark:** Connecting Ridge (C1) is a published benchmark site with ~85.7% integral illumination. Your results will be compared against this.
    """)