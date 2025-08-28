
from pathlib import Path
import streamlit as st
from typing import List, Set
from config import OUTPUT_EVIDENCE_EXCEL_NAME
from logic.mapping import build_full_mapping, build_mappings, get_full_schema_table_and_column_names_from_sheets
from logic.text_processing import extract_full_keys, replace_by_mapping
from utils.excel_utils import filter_excel
from typing import Dict
import chardet
import pandas as pd
from config import FULL_EVIDENCE_INPUT_PATH
import xlwings as xw
from logic import detect_rules

@st.cache_data()
def get_encode_file(file_path: str | Path):
    common_encodings = ['cp932', 'euc_jp', 'shift_jis',  'utf-8', 'latin-1']
    file_path = Path(file_path)
    # Read file once as bytes
    raw = file_path.read_bytes()

    # Try common encodings
    encoding = None
    for enc in common_encodings:
        try:
            raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue

    # Fallback to chardet if needed
    if encoding is None:
        encoding = chardet.detect(raw).get("encoding") or "utf-8"
        try:
            raw.decode(encoding, errors="replace")
        except Exception:
            encoding = "utf-8"

    return raw, encoding

@st.cache_data()
def load_all_sheets() -> Dict[str, pd.DataFrame]:
    return pd.read_excel(FULL_EVIDENCE_INPUT_PATH, sheet_name=None)

@st.cache_data()
def extract_column_names_from_sheet() -> set:
    sheets = load_all_sheets()
    return get_full_schema_table_and_column_names_from_sheets(sheets)

@st.cache_data()
def get_full_type_df() -> pd.DataFrame:
    full_type_df = pd.DataFrame()
    for name, df in load_all_sheets().items():
        if name.startswith('type'):
            # print(f"Sheet: {name}: size: {len(df)} example:#n{df.head(2)}")
            full_type_df = pd.concat([full_type_df, df], ignore_index=True)
    full_type_df['table_name'] = full_type_df['table_name'].str.upper()
    full_type_df['column_name'] = full_type_df['column_name'].str.upper()
    return full_type_df


def replace_lines_in_file(app: xw.App, file_path: str, start_line: int, end_line: int, encoding: str, source_type: str):
    with open(file_path, 'r', encoding=encoding) as f:
        lines = f.readlines()

    before = lines[:start_line - 1]
    target = lines[start_line - 1:end_line]
    after = lines[end_line:]

    evidence_excel_path = str(Path(file_path).parent / OUTPUT_EVIDENCE_EXCEL_NAME)

    replaced_block = process_and_replace_lines(app, target, evidence_excel_path, source_type)
    if replaced_block:
        st.code(replaced_block)
        result_lines = before + [replaced_block + '\n'] + after
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(result_lines)

def process_and_replace_lines(app: xw.App,lines: List[str], evidence_excel_path: str,  source_type: str, extra_tables: List[str]=[]) -> str:
    block, unused_keys, filter_keys, mapping, new_col_name_to_table_and_data_type_dict = show_data_type(lines, extra_tables)

    # Export used keys to Excel
    if app:
        filter_excel(app, evidence_excel_path, filter_keys)
        filter_excel(
            app,
            excel_path=evidence_excel_path,
            filter_values=filter_keys
        )
    else:
        st.warning("Skipping evidence data export.")
    
    new_code, output_mul_mapping, output_rule2_mapping = replace_by_mapping(block, mapping, new_col_name_to_table_and_data_type_dict)

    detect_rules.check_final_rules(block, unused_keys, output_mul_mapping, output_rule2_mapping, source_type)

    return new_code

def show_data_type(lines, extra_tables, only_show=False):
    valid_columns = extract_column_names_from_sheet()
    sheets = load_all_sheets()
    schema_dict, table_dict, column_dict, key_dict = build_mappings(sheets)

    block = ''.join(lines)
    (used_keys, unused_keys) = extract_full_keys(block, valid_columns)
    if extra_tables:
        used_keys.extend(extra_tables)
    st.code(','.join(used_keys))

    filter_keys = set(used_keys)

    table_list = { table_name for  table_name in filter_keys if  table_name in table_dict }
    if table_list:
        st.write(f"Tables:")
        st.code(','.join(table_list))
    full_type_df = get_full_type_df()
    filtered_df  = full_type_df[full_type_df['table_name'].isin(filter_keys) & full_type_df['column_name'].isin(filter_keys)]

    mapping = build_full_mapping(used_keys, schema_dict, table_dict, column_dict, key_dict)

    new_col_name_to_table_and_data_type_dict : dict[str, list]= {}
    for _, row in filtered_df.iterrows():
        table_name = row["table_name"]
        col_name = row["column_name"]
        data_type = row['data_type']
        new_table_names: set = mapping.get(table_name, {})
        new_col_names: set = mapping.get(col_name, {})

        for new_tbl_name in new_table_names:
            for new_col_name in new_col_names:
                if new_col_name not in new_col_name_to_table_and_data_type_dict:
                    new_col_name_to_table_and_data_type_dict[new_col_name] = []
                items = new_col_name_to_table_and_data_type_dict.get(new_col_name)
                items.append((new_tbl_name, data_type))
    if only_show:
        filtered_df.loc[:, 'table_order'] = filtered_df['table_name'].apply(lambda x: used_keys.index(x))
        filtered_df.loc[:, 'column_order'] = filtered_df['column_name'].apply(lambda x: used_keys.index(x))
        filtered_df = filtered_df.sort_values(['column_order', 'table_order'])
        filtered_df = filtered_df.drop(columns=['column_order', 'table_order'])
        filtered_df['new_col_name'] = filtered_df['column_name'].apply(lambda x: mapping[x] if x in mapping else x)
        filtered_df['new_table_name'] = filtered_df['table_name'].apply(lambda x: mapping[x] if x in mapping else x)
        show_df = filtered_df[["table_name", "table_type", 'column_name', "new_col_name", "data_type", "is_nullable", "new_table_name"]]
        st.dataframe(show_df)
    return block,unused_keys,filter_keys,mapping, new_col_name_to_table_and_data_type_dict
