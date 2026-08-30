import csv
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Survey Dashboard", layout="wide")


@st.cache_data
def load_data(filepath):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    return df


df = load_data("data.csv")


def parse_multiselect_cell(val):
    if pd.isna(val) or not str(val).strip():
        return []
    reader = csv.reader(io.StringIO(str(val)), skipinitialspace=True)
    try:
        items = list(reader)[0]
        return [item.strip() for item in items if item.strip()]
    except IndexError:
        return []


def extract_unique_options(series):
    unique_options = set()
    for entry in series.dropna():
        items = parse_multiselect_cell(entry)
        unique_options.update(items)
    return sorted(list(unique_options))


st.sidebar.header("Filter Responses")

AUDIENCE_COL = "Primary Audience"
TOOLS_COL = "Tools Included"

scale_cols = [
    col
    for col in df.columns
    if df[col].dropna().isin([0, 1, 2, 3, 0.0, 1.0, 2.0, 3.0]).all()
    and not df[col].dropna().empty
]
SCALE_COL = scale_cols[0] if scale_cols else None

if AUDIENCE_COL in df.columns:
    aud_options = extract_unique_options(df[AUDIENCE_COL])
    selected_audience = st.sidebar.multiselect(
        AUDIENCE_COL, options=aud_options
    )
else:
    selected_audience = []

if TOOLS_COL in df.columns:
    tools_options = extract_unique_options(df[TOOLS_COL])
    selected_tools = st.sidebar.multiselect(TOOLS_COL, options=tools_options)
else:
    selected_tools = []

if SCALE_COL:
    min_val = int(df[SCALE_COL].min())
    max_val = int(df[SCALE_COL].max())
    selected_scale = st.sidebar.slider(
        f"{SCALE_COL} (Scale)",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
    )
else:
    selected_scale = None

filtered_df = df.copy()


def filter_multiselect(dataframe, column_name, selected_values):
    if not selected_values or column_name not in dataframe.columns:
        return dataframe

    def matches(val):
        row_items = parse_multiselect_cell(val)
        return any(item in row_items for item in selected_values)

    return dataframe[dataframe[column_name].apply(matches)]


filtered_df = filter_multiselect(filtered_df, AUDIENCE_COL, selected_audience)
filtered_df = filter_multiselect(filtered_df, TOOLS_COL, selected_tools)

if SCALE_COL and selected_scale:
    filtered_df = filtered_df[
        filtered_df[SCALE_COL].between(selected_scale[0], selected_scale[1])
    ]

st.title("Interactive Survey Dashboard")

col1, col2 = st.columns(2)
col1.metric("Total Entries", len(df))
col2.metric("Filtered Entries", len(filtered_df))

st.divider()

if TOOLS_COL in filtered_df.columns:
    st.subheader("Tools Included Breakdown")
    all_tools_in_filtered = []
    for entry in filtered_df[TOOLS_COL]:
        all_tools_in_filtered.extend(parse_multiselect_cell(entry))

    if all_tools_in_filtered:
        tools_counts = pd.Series(all_tools_in_filtered).value_counts()
        st.bar_chart(tools_counts)

st.subheader("Filtered Data")
st.dataframe(filtered_df, use_container_width=True)
