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
        return ""
    url_str = str(val).strip()
    if not url_str or url_str.lower() in ["nan", "none"]:
        return ""
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return f"https://{url_str}"
    return url_str


def clean_str(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s.lower() in ["nan", "none"] else s


TITLE_COL = "Title"
PARENT_ID_COL = "Parent ID"
IS_SUB_ITEM_COL = "Subitem?"
SUB_ITEM_NOTES_COL = "Subitem Notes"
LINK_COL = "Link"

cols = list(df.columns)
ORG_COL = cols[5] if len(cols) > 5 else "Organization"
YEAR_COL = cols[6] if len(cols) > 6 else "Year"
RESOURCE_TYPE_COL = cols[7] if len(cols) > 7 else "Resource Type"
SECTOR_COL = cols[8] if len(cols) > 8 else "Sector"
AUDIENCE_COL = cols[9] if len(cols) > 9 else "Audience"
TOPICS_COLS = cols[10:16] if len(cols) > 15 else []
EQUITY_COLS = cols[16:21] if len(cols) > 20 else []
TOOLS_COL = cols[21] if len(cols) > 21 else "Tools"

if IS_SUB_ITEM_COL in df.columns:
    df[IS_SUB_ITEM_COL] = (
        df[IS_SUB_ITEM_COL]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .apply(lambda x: "YES" if x in ["YES"] else "NO")
    )
else:
    df[IS_SUB_ITEM_COL] = "NO"

df["_GROUP_ID"] = df[TITLE_COL].where(df[IS_SUB_ITEM_COL] != "YES")
df["_GROUP_ID"] = df["_GROUP_ID"].ffill()

# Sanitize URLs
if LINK_COL in df.columns:
    df[LINK_COL] = df[LINK_COL].apply(sanitize_url)

st.sidebar.header("Filter Resources")

parents_only_df = df[df[IS_SUB_ITEM_COL] != "YES"]

title_search = st.sidebar.text_input("Search Title")

org_search = ""
if ORG_COL in df.columns:
    org_search = st.sidebar.text_input("Search by Organization")

resource_opts = (
    extract_unique_options(parents_only_df[RESOURCE_TYPE_COL])
    if RESOURCE_TYPE_COL in df.columns
    else []
)
selected_resource = st.sidebar.multiselect(
    RESOURCE_TYPE_COL, options=resource_opts
)

sector_opts = (
    extract_unique_options(parents_only_df[SECTOR_COL])
    if SECTOR_COL in df.columns
    else []
)
selected_sector = st.sidebar.multiselect(SECTOR_COL, options=sector_opts)

audience_opts = (
    extract_unique_options(parents_only_df[AUDIENCE_COL])
    if AUDIENCE_COL in df.columns
    else []
)
selected_audience = st.sidebar.multiselect(
    AUDIENCE_COL, options=audience_opts
)

tools_opts = (
    extract_unique_options(parents_only_df[TOOLS_COL])
    if TOOLS_COL in df.columns
    else []
)
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

if org_search and ORG_COL in df.columns:
    filtered_parents = filtered_parents[
        filtered_parents[ORG_COL]
        .astype(str)
        .str.contains(org_search, case=False, na=False)
    ]

for col in selected_topics:
    if col in filtered_parents.columns:
        numeric_series = pd.to_numeric(filtered_parents[col], errors="coerce")
        filtered_parents = filtered_parents[numeric_series >= 2]

for col in selected_equity:
    if col in filtered_parents.columns:
        numeric_series = pd.to_numeric(filtered_parents[col], errors="coerce")
        filtered_parents = filtered_parents[numeric_series >= 2]

matching_group_ids = filtered_parents["_GROUP_ID"].dropna().unique()

filtered_df = df[df["_GROUP_ID"].isin(matching_group_ids)].copy()

filtered_df = filtered_df.sort_values(
    by=["_GROUP_ID", IS_SUB_ITEM_COL], ascending=[True, True]
)

st.title("Governance Guidance Pack: Artificial Intelligence (AI) in Education")

st.caption(
    "Welcome! This guidance pack is intended for the use of education stakeholders, such as educators, LEAs, and policymakers.
    Below, you will find a list of guidance documents, frameworks, and other governance resources. 
    In each row, you can find items' basic information. In addition, GRAIL has also developed evaluations for each resource.
    For each column titled with a guidance topic, resources are scored (1-3) based on how deeply they cover that particular topic. Similarly, each column labelled with an underserved group evaluates how deeply the resource provides guidance for that underserved group specifically. Lastly, the final four columns evaluate each resource’s real-world usability, list the tools the resources offer, and provide notable information.
    The Filtration system on the left also allows you to access resources that fit your specific needs and preferences."
)

col1, col2 = st.columns(2)
col1.metric("Total Entries", len(df))
col2.metric("Filtered Entries", len(filtered_df))

st.divider()
st.subheader("Filtered Data")

display_df = filtered_df.copy()

def format_title_cell(row):
    is_sub = str(row.get(IS_SUB_ITEM_COL, "")).upper() == "YES"
    parent_title = clean_str(row.get(TITLE_COL, ""))
    sub_title = clean_str(row.get(PARENT_ID_COL, ""))

    if is_sub:
        display_text = sub_title if sub_title else parent_title
        return f"↳ {display_text}" if display_text else "↳ Sub-item"
    return parent_title


display_df[TITLE_COL] = display_df.apply(format_title_cell, axis=1)

multiselect_columns = [
    c
    for c in [RESOURCE_TYPE_COL, SECTOR_COL, AUDIENCE_COL, TOOLS_COL]
    if c in display_df.columns
]

for col in multiselect_columns:
    display_df[col] = display_df[col].apply(parse_multiselect_cell)

column_configs = {}

for col in multiselect_columns:
    column_configs[col] = st.column_config.ListColumn(col, width="medium")

if LINK_COL in display_df.columns:
    column_configs[LINK_COL] = st.column_config.LinkColumn(
        LINK_COL,
        display_text="Open Link",
        width="small",
    )

internal_cols = ["_GROUP_ID", PARENT_ID_COL]
visible_columns = [c for c in display_df.columns if c not in internal_cols]

display_df = display_df[visible_columns].fillna("")

st.dataframe(
    display_df,
    column_config=column_configs,
    use_container_width=True,
    hide_index=True,
)
