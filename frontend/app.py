from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(page_title="InsightSentinel AI", layout="wide")

st.title("InsightSentinel AI — Running ✅")
st.caption("V1: Business Data Monitoring & Decision Engine (FastAPI + Postgres + Streamlit)")

backend_url = os.getenv("BACKEND_URL", "http://backend:8000")


def safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


def get_health() -> tuple[bool, Any]:
    try:
        r = requests.get(f"{backend_url}/health", timeout=3)
        r.raise_for_status()
        return True, safe_json(r)
    except Exception as e:
        return False, str(e)


def list_datasets() -> tuple[bool, Any]:
    try:
        r = requests.get(f"{backend_url}/datasets", timeout=10)
        r.raise_for_status()
        return True, safe_json(r)
    except Exception as e:
        return False, str(e)


def ingest_csv(file_bytes: bytes, filename: str, dataset_name: str, description: str | None) -> tuple[bool, Any]:
    try:
        files = {"file": (filename, file_bytes, "text/csv")}
        data = {"dataset_name": dataset_name, "description": description or ""}
        r = requests.post(f"{backend_url}/ingest/csv", files=files, data=data, timeout=60)
        if r.status_code >= 400:
            return False, safe_json(r)
        return True, safe_json(r)
    except Exception as e:
        return False, str(e)


with st.expander("Backend Connectivity (Phase 0)", expanded=True):
    st.write(f"Backend URL: `{backend_url}`")
    ok, payload = get_health()
    if ok:
        st.success(f"Backend health: {payload}")
    else:
        st.warning("Backend not reachable yet (this can be normal while containers start).")
        st.code(payload)

st.divider()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Phase 2 — CSV Ingestion")
    st.write("Upload a CSV, profile it (rows/columns/nulls/distincts), and persist metadata.")

    dataset_name = st.text_input("Dataset name", value="Demo CSV Dataset")
    description = st.text_area("Description (optional)", value="Phase 2 ingestion test", height=80)
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

    ingest_clicked = st.button("Ingest CSV", type="primary", use_container_width=True)

    if ingest_clicked:
        if not uploaded:
            st.error("Please upload a CSV file.")
        else:
            with st.spinner("Uploading + profiling..."):
                ok, result = ingest_csv(
                    file_bytes=uploaded.getvalue(),
                    filename=uploaded.name,
                    dataset_name=dataset_name.strip() or "Untitled Dataset",
                    description=description,
                )

            if ok:
                st.success("Ingestion completed ✅")
                st.json(result)
                # Trigger a refresh of the datasets list on the right
                st.session_state["refresh_datasets"] = True
            else:
                st.error("Ingestion failed ❌")
                st.json(result)

with col2:
    st.subheader("Datasets (Phase 1/2)")
    refresh = st.button("Refresh datasets", use_container_width=True) or st.session_state.get("refresh_datasets", False)
    if refresh:
        st.session_state["refresh_datasets"] = False

    ok, data = list_datasets()
    if ok:
        # If API returns a dict (unlikely), handle it; else assume list
        datasets = data if isinstance(data, list) else data.get("items", [])
        if not datasets:
            st.info("No datasets yet. Ingest a CSV to create the first one.")
        else:
            st.write(f"Total datasets: **{len(datasets)}**")
            st.dataframe(datasets, use_container_width=True)

            # Optional: quick drill-down for a dataset
            ids = [d.get("id") for d in datasets if isinstance(d, dict) and d.get("id")]
            if ids:
                selected_id = st.selectbox("Inspect dataset details", options=ids)
                if selected_id:
                    try:
                        r = requests.get(f"{backend_url}/datasets/{selected_id}", timeout=10)
                        if r.status_code >= 400:
                            st.error(safe_json(r))
                        else:
                            st.json(safe_json(r))
                    except Exception as e:
                        st.error(str(e))
    else:
        st.warning("Could not load datasets from backend.")
        st.code(data)

st.divider()
st.info("Next phases will add anomaly detection, alerting, and AI summaries.")