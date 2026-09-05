import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
import data_access as da

st.title("Provider–specialty forecasts")
st.caption("Predictions shown here were produced before their held-out target month.")
frame = da.predictions()
months = sorted(frame.target_month.unique())
month = st.selectbox("Target month", months, index=len(months) - 1)
specialties = sorted(frame.treatment_function_name.dropna().unique().tolist())
specialty = st.selectbox("Specialty", ["All"] + specialties)
shown = frame[frame.target_month.eq(month)].copy()
if specialty != "All":
    shown = shown[shown.treatment_function_name.eq(specialty)]
shown = shown.sort_values("Random Forest", ascending=False).head(50)
fig = px.bar(
    shown.head(20).sort_values("Random Forest"), x="Random Forest", y="provider_name",
    orientation="h", hover_data=["treatment_function_name", "target_breach_52w_rate"],
)
fig.update_layout(xaxis_tickformat=".1%", xaxis_title="Forecast 52-week breach rate", yaxis_title="")
st.plotly_chart(fig, use_container_width=True)
table = shown[["provider_name", "treatment_function_name", "Random Forest", "target_breach_52w_rate"]]
table = table.rename(columns={"Random Forest": "forecast", "target_breach_52w_rate": "observed"})
st.dataframe(table.style.format({"forecast": "{:.2%}", "observed": "{:.2%}"}), use_container_width=True, hide_index=True)
