import csv
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="User Dashboard", layout="wide")


@st.cache_data(ttl=0)
def load_data(filepath):
    df = pd.read_csv(filepath, header=1, engine="python")
    df.columns = df.columns.astype(str).str.strip()
    return df


df = load_data("data.csv")


def parse_multiselect_cell(val):
    if pd.isna(val) or str(val).strip().lower() in ["", "nan", "none"]:
        return []
    reader = csv.reader(
        io.StringIO(str(val)), skipinitialspace=True, lineterminator="\n"
    )
    try:
        items = list(reader)[0]
        return [
            item.strip().strip('"').strip("'")
            for item in items
            if item.strip()
        ]
    except IndexError:
        return []


def extract_unique_options(series):
    unique_options = set()
    for entry in series.dropna():
        items = parse_multiselect_cell(entry)
        unique_options.update(items)
    return sorted(list(unique_options))


def sanitize_url(val):
    if pd.isna(val):
        return None
    url_str = str(val).strip()
    if not url_str or url_str.lower() in ["nan", "none"]:
        return None
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return f"https://{url_str}"
    return url_str


cols = list(df.columns)

TITLE_COL = cols[0]
LINK_COL = cols[1]
ORG_COL = cols[2]
YEAR_COL = cols[3]
RESOURCE_TYPE_COL = cols[4]
SECTOR_COL = cols[5]
AUDIENCE_COL = cols[6]
TOPICS_COLS = cols[7:13]
EQUITY_COLS = cols[13:18]
TOOLS_COL = cols[18]

PARENT_ID_COL = "Parent ID"
IS_SUB_ITEM_COL = "Subitem?"
SUB_ITEM_NOTES_COL = "Subitem Notes"

if IS_SUB_ITEM_COL in df.columns:
    df[IS_SUB_ITEM_COL] = (
        df[IS_SUB_ITEM_COL]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .apply(lambda x: "YES" if x in ["YES", "Y", "TRUE", "1"] else "NO")
    )
else:
    df[IS_SUB_ITEM_COL] = "NO"

if PARENT_ID_COL in df.columns:
    df[PARENT_ID_COL] = df[PARENT_ID_COL].replace(
        r"^\s*$", None, regex=True
    )
    df[PARENT_ID_COL] = df[PARENT_ID_COL].fillna(df[TITLE_COL]).ffill()
else:
    df[PARENT_ID_COL] = df[TITLE_COL].ffill()

df[LINK_COL] = df[LINK_COL].apply(sanitize_url)

st.sidebar.header("Filter Resources")

parents_only_df = df[df[IS_SUB_ITEM_COL] != "YES"]

title_search = st.sidebar.text_input("Search Title")
org_search = st.sidebar.text_input("Search by Organization")

resource_opts = extract_unique_options(parents_only_df[RESOURCE_TYPE_COL])
selected_resource = st.sidebar.multiselect(
    RESOURCE_TYPE_COL, options=resource_opts
)

sector_opts = extract_unique_options(parents_only_df[SECTOR_COL])
selected_sector = st.sidebar.multiselect(SECTOR_COL, options=sector_opts)

audience_opts = extract_unique_options(parents_only_df[AUDIENCE_COL])
selected_audience = st.sidebar.multiselect(
    AUDIENCE_COL, options=audience_opts
)

tools_opts = extract_unique_options(parents_only_df[TOOLS_COL])
selected_tools = st.sidebar.multiselect(TOOLS_COL, options=tools_opts)

selected_topics = st.sidebar.multiselect(
    "Topics Covered (Score ≥ 2)", options=TOPICS_COLS
)

selected_equity = st.sidebar.multiselect(
    "Equitability (Score ≥ 2)", options=EQUITY_COLS
)

filtered_parents = parents_only_df.copy()


def filter_multiselect(dataframe, column_name, selected_values):
    if not selected_values or column_name not in dataframe.columns:
        return dataframe

    def matches(val):
        row_items = parse_multiselect_cell(val)
        return any(item in row_items for item in selected_values)

    return dataframe[dataframe[column_name].apply(matches)]


filtered_parents = filter_multiselect(
    filtered_parents, RESOURCE_TYPE_COL, selected_resource
)
filtered_parents = filter_multiselect(
    filtered_parents, SECTOR_COL, selected_sector
)
filtered_parents = filter_multiselect(
    filtered_parents, AUDIENCE_COL, selected_audience
)
filtered_parents = filter_multiselect(
    filtered_parents, TOOLS_COL, selected_tools
)

if title_search:
    filtered_parents = filtered_parents[
        filtered_parents[TITLE_COL]
        .astype(str)
        .str.contains(title_search, case=False, na=False)
    ]

if org_search:
    filtered_parents = filtered_parents[
        filtered_parents[ORG_COL]
        .astype(str)
        .str.contains(org_search, case=False, na=False)
    ]

for col in selected_topics:
    numeric_series = pd.to_numeric(filtered_parents[col], errors="coerce")
    filtered_parents = filtered_parents[numeric_series >= 2]

for col in selected_equity:
    numeric_series = pd.to_numeric(filtered_parents[col], errors="coerce")
    filtered_parents = filtered_parents[numeric_series >= 2]

matching_parent_ids = filtered_parents[PARENT_ID_COL].dropna().unique()

filtered_df = df[df[PARENT_ID_COL].isin(matching_parent_ids)].copy()

filtered_df = filtered_df.sort_values(
    by=[PARENT_ID_COL, IS_SUB_ITEM_COL], ascending=[True, True]
)

st.title("Governance Guidance Pack: Artificial Intelligence (AI) in Education")

col1, col2 = st.columns(2)
col1.metric("Total Entries", len(df))
col2.metric("Filtered Entries", len(filtered_df))

st.divider()
st.subheader("Filtered Data")

display_df = filtered_df.copy()


def format_title_cell(row):
    is_sub = str(row.get(IS_SUB_ITEM_COL, "")).upper() == "YES"

    raw_title = str(row.get(TITLE_COL, "")).strip()
    title = "" if raw_title.lower() in ["nan", "none", ""] else raw_title

    raw_notes = (
        str(row.get(SUB_ITEM_NOTES_COL, "")).strip()
        if SUB_ITEM_NOTES_COL in row
        else ""
    )
    notes = "" if raw_notes.lower() in ["nan", "none", ""] else raw_notes

    if is_sub:
        if title and notes:
            return f"↳ {title} ({notes})"
        elif notes:
            return f"↳ {notes}"
        elif title:
            return f"↳ {title}"
        else:
            return "↳ Sub-item"
    return title


display_df[TITLE_COL] = display_df.apply(format_title_cell, axis=1)

multiselect_columns = [RESOURCE_TYPE_COL, SECTOR_COL, AUDIENCE_COL, TOOLS_COL]

for col in multiselect_columns:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(parse_multiselect_cell)

column_configs = {}

for col in multiselect_columns:
    if col in display_df.columns:
        column_configs[col] = st.column_config.ListColumn(col, width="medium")

column_configs[LINK_COL] = st.column_config.LinkColumn(
    LINK_COL, display_text="Open Link", width="small"
)

internal_cols = [PARENT_ID_COL]
visible_columns = [c for c in display_df.columns if c not in internal_cols]

display_df = display_df[visible_columns].fillna("")

st.dataframe(
    display_df,
    column_config=column_configs,
    use_container_width=True,
    hide_index=True,
)
