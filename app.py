import csv
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Survey Dashboard", layout="wide")


@st.cache_data
def load_data(filepath):
    return pd.read_csv(filepath)


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

aud_options = extract_unique_options(df["Primary Audience"])
selected_audience = st.sidebar.multiselect(
    "Primary Audience", options=aud_options
)

tools_options = extract_unique_options(df["Tools Included"])
selected_tools = st.sidebar.multiselect("Tools Included", options=tools_options)

SCALE_COL = "Scale_Column"
selected_scale = st.sidebar.slider(
    f"{SCALE_COL} (0-3)", min_value=0, max_value=3, value=(0, 3)
)

filtered_df = df.copy()


def filter_multiselect(dataframe, column_name, selected_values):
    if not selected_values:
        return dataframe

    def matches(val):
        row_items = parse_multiselect_cell(val)
        return any(item in row_items for item in selected_values)

    return dataframe[dataframe[column_name].apply(matches)]


filtered_df = filter_multiselect(
    filtered_df, "Primary Audience", selected_audience
)
filtered_df = filter_multiselect(filtered_df, "Tools Included", selected_tools)

if SCALE_COL in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df[SCALE_COL].between(selected_scale[0], selected_scale[1])
    ]

st.title("Interactive Survey Dashboard")

col1, col2 = st.columns(2)
col1.metric("Total Entries", len(df))
col2.metric("Filtered Entries", len(filtered_df))

st.divider()

st.subheader("Tools Included Breakdown")
all_tools_in_filtered = []
for entry in filtered_df["Tools Included"]:
    all_tools_in_filtered.extend(parse_multiselect_cell(entry))

if all_tools_in_filtered:
    tools_counts = pd.Series(all_tools_in_filtered).value_counts()
    st.bar_chart(tools_counts)

st.subheader("Filtered Data")
st.dataframe(filtered_df, use_container_width=True)
