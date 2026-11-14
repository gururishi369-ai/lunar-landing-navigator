import streamlit as st
import pandas as pd

st.set_page_config(page_title="Lunar Landing Navigator", layout="wide")

st.title("🌙 Lunar Landing Site Navigator")
st.write("Phase 0 checkpoint — the website skeleton is alive.")

# Load the sample data
df = pd.read_csv("sample_data.csv")

st.subheader("Sample Data Preview")
st.dataframe(df)

st.subheader("Sun Elevation (sample)")
st.line_chart(df, x="timestamp_utc", y="sun_elevation_deg")