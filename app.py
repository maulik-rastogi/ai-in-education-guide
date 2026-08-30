import csv
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Survey Dashboard", layout="wide")


@st.cache_data
def load_data(filepath):
    # header=1 tells Pandas to use Row 2 as the column headers
    df = pd.read_csv(filepath, header=1)
    df.columns = df.columns.astype(str).str.strip()
    return df


df = load_data("data.csv")


def parse_multiselect_cell(val):
    if pd.isna(val) or not str(val).strip():
        return []
    reader = csv.reader(io.StringIO(str(val)), skipinitialspace=True)
    try:
        items = list(reader)[0]
        cleaned_items = [
            item.strip().strip('"').strip("'") for item in items if item.strip()
        ]
        return cleaned_items
    except IndexError:
        return []


def extract_unique_options(series):
    unique_options = set()
    for entry in series.dropna():
        items = parse_multiselect_cell(entry)
        unique_options.update(items)
    return sorted(list(unique_options))


st.sidebar.header("Filter Responses")

columns_list = list(df.columns)

AUDIENCE_COL = st.sidebar.selectbox(
    "Select Primary Audience Column",
    options=columns_list,
    index=columns_list.index("Primary Audience")
    if "Primary Audience" in columns_list
    else 0,
)

TOOLS_COL = st.sidebar.selectbox(
    "Select Tools Included Column",
    options=columns_list,
    index=columns_list.index("Tools Included")
    if "Tools Included" in columns_list
    else (1 if len(columns_list) > 1 else 0),
)

scale_candidates = [
    col
    for col in df.columns
    if pd.to_numeric(df[col], errors="coerce")
    .dropna()
    .isin([0, 1, 2, 3, 0.0, 1.0, 2.0, 3.0])
    .all()
    and not df[col].dropna().empty
]

SCALE_COL = st.sidebar.selectbox(
    "Select Scale Column (0-3)",
    options=["None"] + scale_candidates,
    index=1 if len(scale_candidates) > 0 else 0,
)

aud_options = extract_unique_options(df[AUDIENCE_COL])
selected_audience = st.sidebar.multiselect(
    f"Filter {AUDIENCE_COL}", options=aud_options
)

tools_options = extract_unique_options(df[TOOLS_COL])
selected_tools = st.sidebar.multiselect(
    f"Filter {TOOLS_COL}", options=tools_options
)

if SCALE_COL != "None":
    numeric_scale = pd.to_numeric(df[SCALE_COL], errors="coerce").dropna()
    min_val = int(numeric_scale.min()) if not numeric_scale.empty else 0
    max_val = int(numeric_scale.max()) if not numeric_scale.empty else 3
    selected_scale = st.sidebar.slider(
        f"Filter {SCALE_COL}",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
    )
else:
    selected_scale = None

filtered_df = df.copy()


def filter_multiselect(dataframe, column_name, selected_values):
    if not selected_values:
        return dataframe

    def matches(val):
        row_items = parse_multiselect_cell(val)
        return any(item in row_items for item in selected_values)

    return dataframe[dataframe[column_name].apply(matches)]


filtered_df = filter_multiselect(filtered_df, AUDIENCE_COL, selected_audience)
filtered_df = filter_multiselect(filtered_df, TOOLS_COL, selected_tools)

if SCALE_COL != "None" and selected_scale:
    numeric_col = pd.to_numeric(filtered_df[SCALE_COL], errors="coerce")
    filtered_df = filtered_df[
        numeric_col.between(selected_scale[0], selected_scale[1])
    ]

st.title("Interactive Survey Dashboard")

col1, col2 = st.columns(2)
col1.metric("Total Entries", len(df))
col2.metric("Filtered Entries", len(filtered_df))

st.divider()

st.subheader("Tools Included Breakdown")
all_tools_in_filtered = []
for entry in filtered_df[TOOLS_COL]:
    all_tools_in_filtered.extend(parse_multiselect_cell(entry))

if all_tools_in_filtered:
    tools_counts = pd.Series(all_tools_in_filtered).value_counts()
    st.bar_chart(tools_counts)

st.subheader("Filtered Data")
st.dataframe(filtered_df, use_container_width=True)
