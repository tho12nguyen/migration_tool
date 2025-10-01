# -*- coding: euc_jp -*-

from pathlib import Path
import streamlit as st
from typing import List, Tuple
from config import OUTPUT_EVIDENCE_EXCEL_NAME
from logic.mapping import build_full_mapping, build_mappings, get_full_schema_table_and_column_names_from_sheets
from logic.text_processing import extract_full_keys, replace_by_mapping
from utils import charset_util
from utils.excel_utils import filter_excel
from typing import Dict

import pandas as pd
from config import FULL_EVIDENCE_INPUT_PATH
import xlwings as xw
from rules import detect_rules

@st.cache_data()
def get_encoded_file(file_path: str | Path, return_content: bool = False):
    file_path = Path(file_path)
    raw = file_path.read_bytes()

    encoding = charset_util.detect_encode(raw)
    detect_encoding = charset_util.detect_encode_use_lib(raw)

    if encoding is None:
        st.warning(f"Failed to decode {file_path.name} with common encodings. Using chardet to detect encoding.")
        encoding = detect_encoding
    elif charset_util.is_same_encodings(encoding, detect_encoding) is False:
        st.code(file_path)
        st.warning(
            f"Detected encoding `{detect_encoding.upper()}` differs from the expected encoding `{encoding.upper()}`. "
            f"Using: {encoding.upper()}.\n"
              "Please ensure that the Change file and Destination file use the same encoding before merging."
        )

    try:
        content = raw.decode(encoding)
    except Exception:
            encoding =  charset_util.DEFAULT_ENCODING
            content = raw.decode(encoding)

    return (encoding, content) if return_content else encoding

@st.cache_data()
def load_all_sheets() -> Dict[str, pd.DataFrame]:
    return pd.read_excel(FULL_EVIDENCE_INPUT_PATH, sheet_name=None)

@st.cache_data()
def extract_column_names_from_sheet() -> set:
    sheets = load_all_sheets()
    return get_full_schema_table_and_column_names_from_sheets(sheets)

@st.cache_data()
def get_full_type_df(system_types:List[int]) -> pd.DataFrame:
    full_type_df = pd.DataFrame()
    for name, df in load_all_sheets().items():
        for system_type in system_types:
            if name.startswith(f'type{system_type}'):
                # print(f"Sheet: {name}: size: {len(df)} example:#n{df.head(2)}")
                full_type_df = pd.concat([full_type_df, df], ignore_index=True)
    full_type_df['table_name'] = full_type_df['table_name'].str.upper()
    full_type_df['column_name'] = full_type_df['column_name'].str.upper()
    return full_type_df


def replace_lines_in_file(
    app: xw.App, 
    file_path: str, 
    codeBlockLines: List[Tuple[int, int]], 
    encoding: str, 
    source_type: str, 
    active_rule_set: set,
    system_types: List[int],
    extra_tables: List[str] = []
):
    # Step 1: Read all lines
    with open(file_path, 'r', encoding=encoding, newline="") as f:
        lines = f.readlines()
    evidence_excel_path = str(Path(file_path).parent / OUTPUT_EVIDENCE_EXCEL_NAME)

    if not codeBlockLines:
        return

    # Step 1: collect all line indices to replace (in order)
    sorted_blocks = sorted(codeBlockLines, key=lambda x: x[0])
    lines_to_replace_idx = []
    for start, end in sorted_blocks:
        lines_to_replace_idx.extend(range(start - 1, end))  # 0-based indices

    # Step 2: get all lines to replace in order
    target_lines = [lines[i] for i in lines_to_replace_idx]

    # Step 3: process the merged block
    replaced_lines = process_and_replace_lines(app, target_lines, lines_to_replace_idx, evidence_excel_path, source_type, active_rule_set, system_types, extra_tables, encoding=encoding)
    if replaced_lines:
        output_code = ''
        for idx, line in enumerate(replaced_lines):
             output_code += f'Line {lines_to_replace_idx[idx] + 1}: {line if line.endswith("\n") else line + "\n"}'
        st.code(output_code)

        # Replace the lines in the original list
        for i in range(len(lines_to_replace_idx)):
            idx = lines_to_replace_idx[i]
            lines[idx] = replaced_lines[i]

        # Write back to file
        with open(file_path, 'w', encoding=encoding, newline="") as f:
            f.writelines(lines)

def process_and_replace_lines(app: xw.App,lines: List[str], line_indexes: List[int], evidence_excel_path: str,  source_type: str, active_rule_set: set, system_types: List[int], extra_tables: List[str]=[], encoding='shift_jis') -> List[str]:
    unused_keys, filter_keys, mapping, new_col_name_to_table_and_data_type_dict, column_set = show_data_type(lines, system_types, extra_tables, encoding=encoding, only_show=False)

    # Export used keys to Excel
    if app:
        filter_excel(
            app,
            excel_path=evidence_excel_path,
            filter_values=filter_keys,
            system_types=system_types
        )
    else:
        st.warning("Skipping evidence data export.")
    
    new_lines, output_mul_mapping, output_rule2_mapping = replace_by_mapping(lines, line_indexes, mapping, new_col_name_to_table_and_data_type_dict, column_set)

    detect_rules.detect_and_apply_rules(new_lines,  source_type, active_rule_set, unused_keys, output_mul_mapping, output_rule2_mapping)

    return new_lines

def show_data_type(lines: List[str],  system_types: List[int], extra_tables, only_show=False, encoding='shift_jis') -> Tuple[List[str], set, dict, dict]:
    valid_columns = extract_column_names_from_sheet()
    sheets = load_all_sheets()
    schema_dict, table_dict, column_dict, key_dict = build_mappings(sheets)

    block = ''.join(lines)
    (used_keys, unused_keys) = extract_full_keys(block, valid_columns, encoding)
    if '金庫' in  used_keys:
        used_keys.append("金庫@@@@")
    if extra_tables:
        used_keys.extend(extra_tables)
    st.code(','.join(used_keys))

    filter_keys = set(used_keys)

    table_list = { table_name for  table_name in filter_keys if  table_name in table_dict }
    if table_list:
        st.write(f"Tables:")
        st.code(','.join(table_list))
    full_type_df = get_full_type_df(system_types)
    filtered_df  = full_type_df[full_type_df['table_name'].isin(filter_keys) & full_type_df['column_name'].isin(filter_keys)]

    mapping, column_set = build_full_mapping(used_keys, schema_dict, table_dict, column_dict, key_dict)

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
    return unused_keys,filter_keys,mapping, new_col_name_to_table_and_data_type_dict, column_set
