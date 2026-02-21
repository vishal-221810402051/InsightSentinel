from __future__ import annotations

import os
import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="InsightSentinel AI", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.title("InsightSentinel AI")
st.caption("Phase 3 — Dataset Explorer UI")

# ==========================
# Backend Health
# ==========================
with st.expander("Backend Health Check"):
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        st.success(r.json())
    except Exception as e:
        st.error("Backend not reachable")
        st.code(str(e))

# ==========================
# CSV Upload Section
# ==========================
st.header("Upload CSV Dataset")

with st.form("upload_form"):
    dataset_name = st.text_input("Dataset Name")
    description = st.text_area("Description")
    uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])
    submitted = st.form_submit_button("Upload")

    if submitted:
        if not dataset_name or not uploaded_file:
            st.warning("Dataset name and file required")
        else:
            files = {
                "file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")
            }
            data = {
                "dataset_name": dataset_name,
                "description": description,
            }

            response = requests.post(
                f"{BACKEND_URL}/ingest/csv",
                files=files,
                data=data,
            )

            if response.status_code == 200:
                st.success("Upload successful")
                st.json(response.json())
            else:
                st.error("Upload failed")
                st.code(response.text)

st.divider()

# ==========================
# Dataset List
# ==========================
st.header("Available Datasets")

try:
    datasets = requests.get(f"{BACKEND_URL}/datasets").json()
except Exception:
    datasets = []

if not datasets:
    st.info("No datasets yet.")
else:
    for ds in datasets:
        with st.expander(f"{ds['name']} ({ds['row_count']} rows, {ds['column_count']} cols)"):
            st.write(f"Created: {ds['created_at']}")
            
            # Load full dataset detail
            detail = requests.get(f"{BACKEND_URL}/datasets/{ds['id']}").json()

            st.subheader("Column Profiling")
            df_columns = pd.DataFrame(detail["columns"])
            st.dataframe(df_columns, use_container_width=True)
