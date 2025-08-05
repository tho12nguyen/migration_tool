import streamlit as st
from config import *
from logic.handler import extract_column_names_from_sheet, get_encode_file, get_full_type_df, replace_lines_in_file
from logic.text_processing import extract_sql_info
import pandas as pd
import re
import os
import shutil
from utils import common_util
import xlwings as xw
from utils.file_utils import get_target_files

st.set_page_config(page_title="Code Checker", layout="wide")


# CONFIGS
HTML_FILE_NAME, EXCEL_FILE_NAME = common_util.get_first_htm_and_xlsx(TEMPLATE_FOLDER_PATH)
TEMPLATE_HTML_PATH = f'{TEMPLATE_FOLDER_PATH}/{HTML_FILE_NAME}'
TEMPLATE_EXCEL_PATH = f'{TEMPLATE_FOLDER_PATH}/{EXCEL_FILE_NAME}'

# COMMON FUNCTIONS


# === UI INPUT ===
tab1, tab2, tab3 = st.tabs(["Init daily items", "Process items", "Tools"])

with tab1:
    ITEM_SUB_FOLDER_PATH = st.selectbox(
        "ITEM SUB_FOLDER PATH",
        options=SUB_ITEM_FOLDERS,
        index=0, 
        key="item_root_path_tab1"
    )
    st.write("Selected sub-folder:", ITEM_SUB_FOLDER_PATH)

    DAILY_FOLDER_STR = st.text_input(
        "Daily folder", 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab1"
    )

    FULL_ITEM_ROOT_PATH = f'{ROOT_OUTPUT_PATH}/{ITEM_SUB_FOLDER_PATH}'
    FULL_DAILY_FOLDER_PATH = f"{FULL_ITEM_ROOT_PATH}/{DAILY_FOLDER_STR}" if DAILY_FOLDER_STR else None

    txt_items = st.text_area("Input list (tab-separated: NO, FILE_PATH, FILE_NAME, START_LINE):", height=300, key="input_list_tab1")

    btn_col1, = st.columns(1)
    btn_init = btn_col1.button("Create daily items")

    if btn_init:
        if not DAILY_FOLDER_STR:
            st.warning(" Please input daily folder name")
        elif not txt_items.strip():
            st.warning(" Please input item list")
        else:
            raw_lines = txt_items.strip().splitlines()
            items = []
            errors = []
            for idx, line in enumerate(raw_lines, start=1):
                parts = re.split(r'[\t]+', line.strip())
                if len(parts) != 4:
                    errors.append(f"Line {idx} is invalid: {line}")
                    continue
                items.append(parts)

            if errors:
                st.error("Some lines are invalid:")
                st.code("\n".join(errors))
            else:
                item_map = {a: (b, c, d) for a, b, c, d in items}
                created_items = []

                for item_id in item_map.keys():
                    (src_label, full_file_name, _) = item_map.get(item_id)
                    des_folder_name = f"{FULL_DAILY_FOLDER_PATH}/No.{item_id}"
                    os.makedirs(des_folder_name, exist_ok=True)

                    # Extract file info
                    try:
                        file_type = full_file_name.split('.')[-1]
                        file_name = full_file_name.rsplit('.', 1)[0]

                        src_path = ROOT_APP_PATH + "/" +''.join((src_label, full_file_name))[1:]  # remove leading character
                        des_path = f'{des_folder_name}/{full_file_name}'
                        des_path_after = f'{des_folder_name}/{file_name}_after.{file_type}'
                        des_excel_path = f'{des_folder_name}/{EXCEL_FILE_NAME}'
                        des_html_path = f'{des_folder_name}/{HTML_FILE_NAME}'

                        # Copy template files
                        shutil.copy(src_path, des_path)
                        shutil.copy(src_path, des_path_after)
                        shutil.copy(TEMPLATE_EXCEL_PATH, des_excel_path)
                        shutil.copy(TEMPLATE_HTML_PATH, des_html_path)

                        created_items.append({
                            "No": item_id,
                            "Filename": full_file_name,
                            "Src": src_path[-50:],
                            "Dest": des_path
                        })

                    except Exception as e:
                        st.error(f"Failed to create item No.{item_id}: {e}")

                if created_items:
                    st.success(f"Created {len(created_items)} items successfully!")
                    st.dataframe(pd.DataFrame(created_items))


with tab2:
    ITEM_SUB_FOLDER_PATH2 = st.text_input(
        "ITEM_SUB_FOLDER_PATH", 
        value=ITEM_SUB_FOLDER_PATH, 
        placeholder='Example: Select/Insert/Update', 
        key="item_root_path_tab2"
    )

    DAILY_FOLDER_STR2 = st.text_input(
        "Daily folder", 
        value=DAILY_FOLDER_STR, 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab2"
    )

    FULL_ITEM_ROOT_PATH2 = f'{ROOT_OUTPUT_PATH}/{ITEM_SUB_FOLDER_PATH2}'
    FULL_DAILY_FOLDER_PATH = f"{FULL_ITEM_ROOT_PATH2}/{DAILY_FOLDER_STR2}" if DAILY_FOLDER_STR2 else None

    txt_items2 = st.text_area(
        "Input list (tab-separated: NO, FILE_PATH, FILE_NAME, START_LINE, END_LINE):", 
        height=300, 
        value=txt_items, 
        key="input_list_tab2"
    )

    btn_process = st.button("Process & Replace")

    if btn_process:
        if not DAILY_FOLDER_STR2:
            st.warning("Please input daily folder name.")
        elif not txt_items2.strip():
            st.warning("Please input item list.")
        else:
            raw_lines = txt_items2.strip().splitlines()
            item_data = []
            errors = []

            # Parse and validate lines
            for idx, raw_line in enumerate(raw_lines, start=1):
                line = raw_line.strip().replace('\t', ',')
                parts = re.split(r'[,]+', line)
                if len(parts) != 5:
                    errors.append(f"Line {idx} invalid: {raw_line}")
                    continue
                try:
                    item_no = parts[0]
                    start_line = int(parts[3])
                    end_line = int(parts[4])
                    item_data.append((item_no, start_line, end_line))
                except ValueError:
                    errors.append(f"Line {idx} has non-integer line numbers: {raw_line}")

            if errors:
                st.error("Some lines are invalid:")
                st.code("\n".join(errors))
            else:
                if not FULL_DAILY_FOLDER_PATH:
                    st.warning("Folder path not resolved")
                else:
                    daily_files = get_target_files(FULL_DAILY_FOLDER_PATH)
                    if not daily_files:
                        st.warning("?No files found in the target folder. Did you create items?")
                    else:
                        no_to_path = {
                            re.search(r'No\.(\d+)', f).group(1): f
                            for f in daily_files if re.search(r'No\.(\d+)', f)
                        }

                        item_data.sort(key=lambda x: int(x[0]))
                        try:
                            app = xw.App(visible=True)
                            for item_no, start_line, end_line in item_data:
                                st.markdown(f"### Start process for No.{item_no}")

                                selected_file = no_to_path.get(item_no)
                                if not selected_file:
                                    st.warning(f"File for No.{item_no} not found. Skipping.")
                                    continue

                                st.code(f"File: {selected_file}")
                                try:
                                    byte_data, encoding = get_encode_file(selected_file)
                                    if not encoding:
                                        st.error(f"Encoding could not be detected for {selected_file}")
                                        continue

                                    replace_lines_in_file(app, selected_file, start_line, end_line, encoding)
                                    st.success(f"Finished No.{item_no}: Lines {start_line}-{end_line}, Encoding: {encoding}")
                                except Exception as e:
                                    st.error(f"Error processing No.{item_no}: {e}")
                        finally:
                            if 'app' in locals():
                                app.quit()
                                del app


# === TOOLS ===
with tab3:
    # Input field for pasted code
    code_input = st.text_area("Paste your code here (Java / SQL / XML):", height=300, key="code_input_tab3")

    # Button to trigger analysis
    if st.button("Export Data Types"):
        if not code_input.strip():
            st.warning("Please input code first.")
        else:
            # Step 1: Extract valid column names from Excel
            valid_columns = extract_column_names_from_sheet()

            # Step 2: Extract used keys (columns/tables) from input code
            used_keys = extract_sql_info(code_input, valid_columns)

            if not used_keys:
                st.warning("No matching columns or tables found in your code.")
            else:
                st.success(f"Found {len(used_keys)} used keys.")
                st.code(', '.join(used_keys), language='text')
                # st.code(f'columns = {used_keys}', language='python')

                # Step 3: Load the full type mapping sheet
                full_type_df = get_full_type_df()

                # Step 4: Filter by used keys
                filter_keys = set(used_keys)
                filtered_df = full_type_df[
                    full_type_df['table_name'].isin(filter_keys) & 
                    full_type_df['column_name'].isin(filter_keys)
                ].copy()

                # Step 5: Add sorting based on usage order
                filtered_df.loc[:, 'table_order'] = filtered_df['table_name'].apply(lambda x: used_keys.index(x))
                filtered_df.loc[:, 'column_order'] = filtered_df['column_name'].apply(lambda x: used_keys.index(x))
                # filtered_df['table_order'] = filtered_df['table_name'].apply(lambda x: used_keys.index(x) if x in used_keys else -1)
                # filtered_df['column_order'] = filtered_df['column_name'].apply(lambda x: used_keys.index(x) if x in used_keys else -1)

                # Step 6: Sort and display
                filtered_df = filtered_df.sort_values(by=['table_order', 'column_order'])
                filtered_df.drop(columns=['table_order', 'column_order'], inplace=True)

                st.markdown("### Matched Table/Column Types")
                st.dataframe(filtered_df, use_container_width=True)