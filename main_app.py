from typing import List
import streamlit as st
from config import *
from logic import handler
import pandas as pd
import re
import os
import shutil
from utils import common_util
import xlwings as xw
from utils import file_utils
from logic import merge_source
from tools import validate_rule_tool


st.set_page_config(page_title="Code Checker", layout="wide")

# === UI INPUT ===
tab_titles = [
    "Initialize Daily Items",
    "Auto Replace Tool",
    "Delete Unused Files",
    "Merge Source Files",
    "Check rule 2 XO",
    "Manual Replace Tool",
]

tab1, tab2, tab3, tab4, tab5, tab6= st.tabs(tab_titles)

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
        key="daily_folder_tab1",
        value=common_util.get_current_date_str()
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
                        des_evidence_path = f'{des_folder_name}/{OUTPUT_EVIDENCE_EXCEL_NAME}'

                        # Copy template files
                        shutil.copy(src_path, des_path)
                        shutil.copy(src_path, des_path_after)
                        shutil.copy(TEMPLATE_EXCEL_PATH, des_excel_path)
                        shutil.copy(TEMPLATE_HTML_PATH, des_html_path)
                        shutil.copy(FULL_EVIDENCE_INPUT_PATH, des_evidence_path)

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
                    daily_files = file_utils.get_target_files(FULL_DAILY_FOLDER_PATH)
                    if not daily_files:
                        st.warning("?No files found in the target folder. Did you create items?")
                    else:
                        no_to_path = {
                            re.search(r'No\.(\d+)', f).group(1): f
                            for f in daily_files if re.search(r'No\.(\d+)', f)
                        }

                        item_data.sort(key=lambda x: int(x[0]))
                        try:
                            app = xw.App(visible=False)
                            for item_no, start_line, end_line in item_data:
                                st.markdown(f"### Start process for No.{item_no}")

                                selected_file = no_to_path.get(item_no)
                                if not selected_file:
                                    st.warning(f"File for No.{item_no} not found. Skipping.")
                                    continue

                                st.code(f"File: {selected_file}")
                                try:
                                    byte_data, encoding = handler.get_encode_file(selected_file)
                                    if not encoding:
                                        st.error(f"Encoding could not be detected for {selected_file}")
                                        continue

                                    handler.replace_lines_in_file(app, selected_file, start_line, end_line, encoding)
                                    st.success(f"Finished No.{item_no}: Lines {start_line}-{end_line}, Encoding: {encoding}")
                                except Exception as e:
                                    st.error(f"Error processing No.{item_no}: {e}")
                        finally:
                            if 'app' in locals():
                                app.quit()
                                del app

# Merge source
with tab4:
    ITEM_SUB_FOLDER_PATH4 = st.text_input(
        "ITEM_SUB_FOLDER_PATH", 
        value=ITEM_SUB_FOLDER_PATH2, 
        placeholder='Example: Select/Insert/Update', 
        key="item_root_path_tab4"
    )

    DAILY_FOLDER_STR4 = st.text_input(
        "Daily folder", 
        value=DAILY_FOLDER_STR2, 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab4"
    )

    FULL_ITEM_ROOT_PATH4 = f'{ROOT_OUTPUT_PATH}/{ITEM_SUB_FOLDER_PATH4}'
    FULL_DAILY_FOLDER_PATH4 = f"{FULL_ITEM_ROOT_PATH4}/{DAILY_FOLDER_STR4}" if DAILY_FOLDER_STR4 else None

    txt_items4 = st.text_area(
        "Input list (tab-separated: NO, FILE_PATH, FILE_NAME, ...):", 
        height=300, 
        value=txt_items, 
        key="input_list_tab4"
    )

    btn_merge = st.button("Merge sources")

    if btn_merge:
        if not SVN_ROOT_PATH:
            st.warning("Please set SVN_ROOT_PATH in config")
        elif not FULL_DAILY_FOLDER_PATH4:
            st.warning("Please input daily folder name.")
        elif not txt_items4.strip():
            st.warning("Please input item list.")
        else:
            raw_lines = txt_items4.strip().splitlines()
            item_data = []
            errors = []

            # Parse and validate lines
            for idx, raw_line in enumerate(raw_lines, start=1):
                # line = raw_line.strip().replace('\t', ',')
                parts = re.split(r'[\t]+', raw_line)
                if len(parts) < 3:
                    errors.append(f"Line {idx} invalid: {raw_line}")
                    continue
                try:
                    item_no = parts[0]
                    file_path = parts[1]
                    file_name = parts[2]
                    item_data.append((item_no, file_path, file_name))
                except ValueError:
                    errors.append(f"Line {idx} has non-integer line numbers: {raw_line}")

            if errors:
                st.error("Some lines are invalid:")
                st.code("\n".join(errors))
            else:
                if not FULL_DAILY_FOLDER_PATH4:
                    st.warning("Folder path not resolved")
                else:
                    daily_files = file_utils.get_target_files(FULL_DAILY_FOLDER_PATH4)
                    if not daily_files:
                        st.warning("?No files found in the target folder. Did you create items?")
                    else:
                        no_to_paths = {}
                        for f in daily_files:
                            no = None
                            if re.search(r'No\.(\d+)', f):
                                no = re.search(r'No\.(\d+)', f).group(1)
                            if no:
                                if no not in no_to_paths:
                                    no_to_paths[no] = []
                                paths: List = no_to_paths.get(no)
                                paths.append(f)
                                no_to_paths[no] = paths

                        item_data.sort(key=lambda x: int(x[0]))

                        count = 0
                        for item_no, file_path, file_name in item_data:
                            st.markdown(f"### Start merge source for No.{item_no}")
                            change_path_files = no_to_paths.get(item_no, None)
                            if not change_path_files:
                                st.warning(f"File for No.{item_no} not found. Skipping.")
                                continue
                            
                            after_file_name = file_name.split('.')[0] + '_after.' + file_name.split('.')[1]
                            for change_path_file in change_path_files:
                                try:
                                    if not change_path_file.endswith(after_file_name):
                                        st.error(f"IGNORE MERGE SOURCE FOR: {change_path_file}")
                                    else:
                                        original_path_file = str(Path(change_path_file).parent / file_name)
                                        dest_file_path = (f"{SVN_ROOT_PATH}{file_path + file_name}").replace('/','\\')
                                        st.write(f"Original file: {original_path_file}")
                                        st.write(f"Change file: {change_path_file}")
                                        st.write(f"Destination file: {dest_file_path}")
                                        _, encoding = handler.get_encode_file(original_path_file)
                                        if not encoding:
                                            st.error(f"{encoding}: Encoding could not be detected for {original_path_file}")
                                            continue
                                        change_code = merge_source.merge_source_file(original_path_file, change_path_file, dest_file_path, encoding)
                                        st.code(f"Change code:{encoding}\n {change_code}")
                                        count += 1
                                        st.success(f"Merge source for No.{item_no} completed successfully")
                                except Exception as e:
                                    st.error(f"Error processing No.{item_no}: {e}")
                        
                        st.success(f"Total merged files: {count}")

# === DELETE UNUSED FILES ===
with tab3:
    ITEM_SUB_FOLDER_PATH5 = st.text_input(
        "ITEM_SUB_FOLDER_PATH", 
        value=ITEM_SUB_FOLDER_PATH2, 
        placeholder='Example: Select/Insert/Update', 
        key="item_root_path_tab5"
    )

    DAILY_FOLDER_STR5 = st.text_input(
        "Daily folder", 
        value=DAILY_FOLDER_STR2, 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab5"
    )

    FULL_ITEM_ROOT_PATH5 = f'{ROOT_OUTPUT_PATH}/{ITEM_SUB_FOLDER_PATH5}'
    FULL_DAILY_FOLDER_PATH5 = f"{FULL_ITEM_ROOT_PATH5}/{DAILY_FOLDER_STR5}" if DAILY_FOLDER_STR5 else None

    txt_file_suffixes = st.text_input(
        "File suffixes:", 
        value=".bak, evidence.xlsx", 
        placeholder='Example: .bak, _v1.xlsx, ...',
        key="file_suffixes_tab5"
    )

    del_unused_btn = st.button("Delete unused files", key="del_unused_btn")
    unused_files = []
    if del_unused_btn:
        if not FULL_DAILY_FOLDER_PATH5:
            st.warning("Please input daily folder name.")
        elif not txt_file_suffixes.strip():
            st.warning("Please input file suffix list.")
        else:
            file_suffixes = set(suffix.strip() for suffix in txt_file_suffixes.split(',') if suffix.strip())
            if file_suffixes:
                st.write(f"File suffixes: {file_suffixes}")
                unused_files = file_utils.get_files_by_suffixes(FULL_DAILY_FOLDER_PATH5, file_suffixes)
                if not unused_files:
                    st.warning("No unused files found with the specified suffixes.")
                else:
                    st.write(unused_files)
                    st.write(f"Total files found: {len(unused_files)}")
                    errors = file_utils.del_files_by_paths(unused_files)
                    if errors:
                        st.error("Errors occurred while deleting files:")
                        st.code("\n".join(errors))
                    else:
                        st.success("All unused files deleted successfully!")

with tab5:

    full_excel_data_file_path = st.text_input(
        "Excel data file path", 
        placeholder='Example: C:/path/to/data.xlsx',
        key="excel_data_file_path_tab6"
    )


    folder = st.text_input("Folder path",
        placeholder='Example: C:/path/to/folder',
        key="folder_path_tab6"
    )
    btn_check_rule2 = st.button("Check rule 2 XO", key="btn_check_rule2_tab6")
    
    if btn_check_rule2:
        if not full_excel_data_file_path.strip():
            st.warning("Vui lòng nhập đường dẫn file Excel dữ liệu.")
        elif not folder.strip():
            st.warning("Vui lòng nhập đường dẫn thư mục cần duyệt.")
        else:
            excel_file = full_excel_data_file_path.strip()
            folder = folder.strip()
            excel_data = validate_rule_tool.read_excel_data(excel_file)
            cast_results, cast_logs = validate_rule_tool.scan_folder_for_cast(folder, excel_data)
            if cast_results:
                    for file_path, info in cast_results.items():
                        st.write(f'File: {file_path} | status (Excel): {info['status']}\n' )
                        for line in info["lines"]:
                            st.write(f"    {line}\n")
                        st.write("\n")
            else:
                st.write("Không phát hiện dòng nào chứa CAST với trạng thái x.\n")
            

with tab6:
    # Input field for pasted code
    code_input = st.text_area("Paste your code here (Java / SQL / XML):", height=300, key="code_input_tab3")

    txt_tables =st.text_input("Tables (comma-separated)")

    col1, col2, col3, col4 = st.columns(4)
    # Button to trigger analysis
    if col1.button("Check data type"):
        if not code_input.strip():
            st.warning("Please input code first.")
        else:
            extra_tables = common_util.convert_and_upper_str_to_list(txt_tables)
            handler.show_data_type(code_input, extra_tables)
        pass
    if col2.button("Export full Code"):
        if not code_input.strip():
            st.warning("Please input code first.")
        else:
            try:
                evidence_excel_path = Path(RESOURCE_ROOT_PATH) / OUTPUT_EVIDENCE_EXCEL_NAME
                shutil.copy(FULL_EVIDENCE_INPUT_PATH, evidence_excel_path)
                extra_tables = common_util.convert_and_upper_str_to_list(txt_tables)
                app = xw.App(visible=False)
                output_code = handler.process_and_replace_lines(app, code_input, evidence_excel_path, extra_tables)
                st.markdown("### Processed Code with Replacements")
                st.warning(f"Exported evidence to: {evidence_excel_path}")
                st.code(output_code)
            finally:
                if 'app' in locals():
                    app.quit()
                    del app