
from pathlib import Path
import streamlit as st
from typing import List
from config import OUTPUT_EVIDENCE_EXCEL_NAME
from logic.mapping import build_full_mapping, build_mappings
from logic.text_processing import extract_sql_info, replace_by_mapping
from utils.excel_utils import filter_excel
from typing import Dict
import streamlit as st
import chardet
import pandas as pd
from config import FULL_EVIDENCE_INPUT_PATH
import xlwings as xw

@st.cache_data()

def get_encode_file(file_path):
    encodings = ['cp932', 'shift_jis', 'utf-8', 'euc_jp', 'latin-1']
    result_encodings = None
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                f.readlines()
                result_encodings = enc
                break
        except Exception:
            continue

    with open(file_path, "rb") as f:
        raw = f.read()
        if not result_encodings:
            result_encodings = chardet.detect(raw)["encoding"]
    return raw, result_encodings

@st.cache_data()
def load_all_sheets() -> Dict[str, pd.DataFrame]:
    return pd.read_excel(FULL_EVIDENCE_INPUT_PATH, sheet_name=None)

@st.cache_data()
def extract_column_names_from_sheet() -> set:
    df = load_all_sheets().get('column')
    return {row[i] for row in df.to_numpy() for i in range(2, 6) if row[i]}

@st.cache_data()
def get_full_type_df() -> pd.DataFrame:
    full_type_df = pd.DataFrame()
    for name, df in load_all_sheets().items():
        if name.startswith('type'):
            # print(f"Sheet: {name}: size: {len(df)} example:#n{df.head(2)}")
            full_type_df = pd.concat([full_type_df, df], ignore_index=True)
    return full_type_df

def replace_lines_in_file(app: xw.App, file_path: str, start_line: int, end_line: int, encoding: str):
    col_set = extract_column_names_from_sheet()
    sheets = load_all_sheets()
    schema_dict, table_dict, column_dict = build_mappings(sheets)

    with open(file_path, 'r', encoding=encoding) as f:
        lines = f.readlines()

    before = lines[:start_line - 1]
    target = lines[start_line - 1:end_line]
    after = lines[end_line:]

    replaced_block = process_and_replace_lines(app, target, col_set, schema_dict, table_dict, column_dict, file_path)
    st.code(replaced_block)
    result_lines = before + [replaced_block + '\n'] + after
    
    with open(file_path, 'w', encoding=encoding) as f:
        f.writelines(result_lines)

def process_and_replace_lines(app: xw.App,lines: List[str], valid_columns, schema_dict, table_dict, column_dict, souce_file_path: str) -> str:
    block = ''.join(lines)
    (used_keys, unused_keys) = extract_sql_info(block, valid_columns)
    if unused_keys:
        st.warning(unused_keys)
    st.code(','.join(used_keys))

    # Load Excel sheets
    filter_kes = set(used_keys)
    full_type_df = get_full_type_df()
    filtered_df  = full_type_df[full_type_df['table_name'].isin(filter_kes) & full_type_df['column_name'].isin(filter_kes)]

    filtered_df.loc[:, 'table_order'] = filtered_df['table_name'].apply(lambda x: used_keys.index(x))
    filtered_df.loc[:, 'column_order'] = filtered_df['column_name'].apply(lambda x: used_keys.index(x))
    filtered_df = filtered_df.sort_values(['column_order', 'table_order'])
    filtered_df = filtered_df.drop(columns=['column_order', 'table_order'])
    st.dataframe(filtered_df)

    # Export used keys to Excel
    excel_full_path = str(Path(souce_file_path).parent / OUTPUT_EVIDENCE_EXCEL_NAME)
    if app:
        filter_excel(app, excel_full_path, filter_kes)
        st.success(f"Evidence data exported to {OUTPUT_EVIDENCE_EXCEL_NAME} at {excel_full_path}")
        filter_excel(
            app,
            excel_path=excel_full_path,
            filter_values=filter_kes
        )
    else:
        st.warning("No Excel app instance provided, skipping evidence data export.")

    mapping = build_full_mapping(used_keys, schema_dict, table_dict, column_dict)
    return replace_by_mapping(block, mapping)