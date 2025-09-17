from typing import List
import streamlit as st
from config import *
from logic import handler
import pandas as pd
import re
import os
import shutil
from rules import detect_c_rules
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
    "Tools for source C",
    "Fix UNIX format"
]

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8= st.tabs(tab_titles)

with tab1:
    SOURCE_TYPE = st.radio("Source Type", SOURCE_TYPE_OPTIONS, horizontal=True, key="source_type_tab1")
    sub_excel_file_name_to_sheet_type_map = FILE_EXCEL_NAME_TO_SHEET_TYPE_MAP_BY_SOURCE_TYPE.get(SOURCE_TYPE, {})
    selected_excel_file_name = st.selectbox(
        "Select excel file name",
        options=list(sub_excel_file_name_to_sheet_type_map.keys()),
        index=None, 
        key="excel_file_name_tab1"
    )
    selected_sheet_name = st.selectbox(
        "Select sheet name",
        options=SUB_ITEM_FOLDER_OPTIONS,
        index=None, 
        key="item_root_path_tab1"
    )

    DAILY_FOLDER_STR = st.text_input(
        "Daily folder", 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab1",
        value=common_util.get_current_date_str()
    )

    txt_items = st.text_area("Input list (tab-separated: NO, FILE_PATH, FILE_NAME, START_LINE):", height=300, key="input_list_tab1")

    btn_col1, = st.columns(1)
    btn_init = btn_col1.button("Create daily items")
    if btn_init:
        if not selected_excel_file_name:
            st.warning(" Please select excel file name")
        elif not selected_sheet_name:
            st.warning(" Please select sheet name")
        elif not DAILY_FOLDER_STR:
            st.warning(" Please input daily folder name")
        elif not txt_items.strip():
            st.warning(" Please input item list")
        else:
            source_configs = get_configs_by_source_type(SOURCE_TYPE)
            FULL_ITEM_ROOT_PATH = f'{source_configs.ROOT_OUTPUT_PATH}/{selected_excel_file_name}/{selected_sheet_name}'
            FULL_DAILY_FOLDER_PATH = f"{FULL_ITEM_ROOT_PATH}/{DAILY_FOLDER_STR}" if DAILY_FOLDER_STR else None

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

                        src_path = source_configs.ROOT_APP_PATH + "/" +''.join((src_label, full_file_name))[1:]  # remove leading character
                        des_path = f'{des_folder_name}/{full_file_name}'
                        des_path_after = f'{des_folder_name}/{file_name}_after.{file_type}'
                        des_excel_path = f'{des_folder_name}/{EXCEL_FILE_NAME}'
                        des_html_path = f'{des_folder_name}/{HTML_FILE_NAME}'
                        des_evidence_path = f'{des_folder_name}/{OUTPUT_EVIDENCE_EXCEL_NAME}'

                        # Copy template files
                        shutil.copy(src_path, des_path)
                        shutil.copy(src_path, des_path_after)
                        os.chmod(des_path_after, 0o666)
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


# === AUTO REPLACE TOOL ===
with tab2:
    source_type_index = common_util.get_index_from_list(SOURCE_TYPE_OPTIONS, SOURCE_TYPE)
    SOURCE_TYPE2 = st.radio("Source Type", SOURCE_TYPE_OPTIONS, index=source_type_index, horizontal=True, key="source_type_tab2")
    sub_excel_file_name_to_sheet_type_map = FILE_EXCEL_NAME_TO_SHEET_TYPE_MAP_BY_SOURCE_TYPE.get(SOURCE_TYPE2, {})
    
    default_value_file_name = selected_excel_file_name
    if selected_excel_file_name == None:
        default_value_file_name = ''
    selected_excel_file_name2 = st.text_input(
        "Select excel file name",
        value=default_value_file_name, 
        key="excel_file_name_tab2"
    )
    default_value_sheet_name = selected_sheet_name
    if selected_sheet_name == None:
        default_value_sheet_name = ''
    selected_sheet_name2 = st.text_input(
        "Select sheet name", 
        value=default_value_sheet_name, 
        key="item_root_path_tab2"
    )

    DAILY_FOLDER_STR2 = st.text_input(
        "Daily folder", 
        value=DAILY_FOLDER_STR, 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab2"
    )

    txt_items2 = st.text_area(
        "Input list (tab-separated: NO, FILE_PATH, FILE_NAME, START_LINE, END_LINE):", 
        height=300, 
        value=txt_items, 
        key="input_list_tab2"
    )

    btn_process = st.button("Process & Replace")

    if btn_process:
        if sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name2, None) is None:
            st.warning("Please select valid excel file name")
        if not DAILY_FOLDER_STR2:
            st.warning("Please input daily folder name.")
        elif not txt_items2.strip():
            st.warning("Please input item list.")
        else:
            st.info("SOURCE CODE: " + SOURCE_TYPE2.upper())
            source_configs = get_configs_by_source_type(SOURCE_TYPE2)
            active_rule_set = set(source_configs.RULE_CONFIGS.get(selected_sheet_name2.upper(), []))

            FULL_ITEM_ROOT_PATH2 = f'{source_configs.ROOT_OUTPUT_PATH}/{selected_excel_file_name2}/{selected_sheet_name2}'
            FULL_DAILY_FOLDER_PATH = f"{FULL_ITEM_ROOT_PATH2}/{DAILY_FOLDER_STR2}" if DAILY_FOLDER_STR2 else None

            raw_lines = txt_items2.strip().splitlines()
            item_data = []
            errors = []
            # Parse and validate lines
            for idx, raw_line in enumerate(raw_lines, start=1):
                line = raw_line.strip().replace('\t', ',')
                parts = re.split(r'[,]+', line)
                if len(parts) < 5:
                    errors.append(f"Line {idx} invalid: {raw_line}")
                    continue
                try:
                    item_no = parts[0]
                    file_name = parts[2]
                    codeBlockLines = []
                    # parsing line ranges
                    i = 3
                    while i + 1 < len(parts):
                        start_line = common_util.parse_int(parts[i])
                        end_line =common_util.parse_int(parts[i + 1])
                        if start_line == -1 or end_line == -1:
                            break
                        if start_line > end_line:
                            errors.append(f"Line {idx} has invalid, start_line {start_line} > end_line {end_line}: {raw_line}")
                            break

                        codeBlockLines.append((start_line, end_line))
                        i += 2
                    if not codeBlockLines:
                        errors.append(f"Line {idx} has no valid line ranges: {raw_line}")
                        continue
                    extra_tables = []
                    for table_name in parts[i:]:
                        extra_tables.append(str(table_name))
                    item_data.append((item_no, file_name, codeBlockLines, extra_tables))
                except ValueError:
                    errors.append(f"Line {idx} has non-integer line numbers: {raw_line}")

            if errors:
                st.error("Some lines are invalid:")
                st.code("\n".join(errors))
            else:
                if not FULL_DAILY_FOLDER_PATH:
                    st.warning("Folder path not resolved")
                else:
                    daily_files = file_utils.get_target_files(FULL_DAILY_FOLDER_PATH, source_configs.SUFFIXES)
                    if not daily_files:
                        st.info("Folder path: " + FULL_DAILY_FOLDER_PATH)
                        st.warning("?No files found in the target folder. Did you create items?")
                    else:

                        item_data.sort(key=lambda x: int(x[0]))
                        try:
                            app = xw.App(visible=False)
                            for item_no, file_name, codeBlockLines, extra_tables in item_data:
                                st.markdown(f"### Start process for No.{item_no}")

                                selected_files = common_util.get_files_by_no_and_name(daily_files, item_no, file_name)
                                if not selected_files:
                                    st.warning(f"File for No.{item_no} not found. Skipping.")
                                    continue
                                if len(selected_files) > 1:
                                    st.warning(f"Multiple files found for No.{item_no}, using the first one: {selected_files}")
                                selected_file = selected_files[0]
                                st.code(f"File: {selected_file}")
                                if True:
                                    encoding = handler.get_encoded_file(selected_file)
                                    if not encoding:
                                        st.error(f"Encoding could not be detected for {selected_file}")
                                        continue
                                    system_types: List[int] = sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name2, [])
                                    handler.replace_lines_in_file(app, selected_file,codeBlockLines, encoding, SOURCE_TYPE2, active_rule_set, system_types, extra_tables)
                                    st.success(f"Finished No.{item_no}: Lines {start_line}-{end_line}, Encoding: {encoding}")
                                # except Exception as e:
                                #     st.error(f"Error processing No.{item_no}: {str(e)}")
                        finally:
                            if 'app' in locals():
                                app.quit()
                                del app


# === DELETE UNUSED FILES ===
with tab3:
    source_type_index = common_util.get_index_from_list(SOURCE_TYPE_OPTIONS, SOURCE_TYPE)
    SOURCE_TYPE3 = st.radio("Source Type", SOURCE_TYPE_OPTIONS, index=source_type_index, horizontal=True, key="source_type_tab3")
    sub_excel_file_name_to_sheet_type_map = FILE_EXCEL_NAME_TO_SHEET_TYPE_MAP_BY_SOURCE_TYPE.get(SOURCE_TYPE3, {})
    
    default_value_file_name = selected_excel_file_name2
    if selected_excel_file_name == None:
        default_value_file_name = ''
    selected_excel_file_name3 = st.text_input(
        "Select excel file name",
        value=default_value_file_name, 
        key="excel_file_name_tab3"
    )
    default_value_sheet_name = selected_sheet_name2
    if selected_sheet_name2 == None:
        default_value_sheet_name = ''

    selected_sheet_name3 = st.text_input(
        "selected_sheet_name", 
        value=default_value_sheet_name, 
        placeholder='Example: Select/Insert/Update', 
        key="item_root_path_tab5"
    )

    DAILY_FOLDER_STR3 = st.text_input(
        "Daily folder", 
        value=DAILY_FOLDER_STR2, 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab5"
    )

    txt_file_suffixes = st.text_input(
        "File suffixes:", 
        value=".bak, evidence.xlsx", 
        placeholder='Example: .bak, _v1.xlsx, ...',
        key="file_suffixes_tab5"
    )

    del_unused_btn = st.button("Delete unused files", key="del_unused_btn")
    unused_files = []
    if del_unused_btn:
        if sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name3, None) is None:
            st.warning("Please select valid excel file name")
        if not DAILY_FOLDER_STR3:
            st.warning("Please input daily folder name.")
        elif not txt_file_suffixes.strip():
            st.warning("Please input file suffix list.")
        else:
            st.info("source_type: " + SOURCE_TYPE3)
            source_configs = get_configs_by_source_type(SOURCE_TYPE3)
            FULL_ITEM_ROOT_PATH3 = f'{source_configs.ROOT_OUTPUT_PATH}/{selected_excel_file_name3}/{selected_sheet_name3}'
            FULL_DAILY_FOLDER_PATH3 = f"{FULL_ITEM_ROOT_PATH3}/{DAILY_FOLDER_STR3}" if DAILY_FOLDER_STR3 else None

            file_suffixes = set(suffix.strip() for suffix in txt_file_suffixes.split(',') if suffix.strip())
            if file_suffixes:
                st.write(f"File suffixes: {file_suffixes}")
                unused_files = file_utils.get_files_by_suffixes(FULL_DAILY_FOLDER_PATH3, file_suffixes)
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

# Merge source
with tab4:
    source_type_index = common_util.get_index_from_list(SOURCE_TYPE_OPTIONS, SOURCE_TYPE)
    SOURCE_TYPE4 = st.radio("Source Type", SOURCE_TYPE_OPTIONS, index=source_type_index, horizontal=True, key="source_type_tab4")
    sub_excel_file_name_to_sheet_type_map = FILE_EXCEL_NAME_TO_SHEET_TYPE_MAP_BY_SOURCE_TYPE.get(SOURCE_TYPE4, {})
    
    default_value_file_name = selected_excel_file_name2
    if selected_excel_file_name2 == None:
        default_value_file_name = ''
    selected_excel_file_name4 = st.text_input(
        "Select excel file name",
        value=default_value_file_name, 
        key="excel_file_name_tab4"
    )
    default_value_sheet_name = selected_sheet_name2
    if selected_sheet_name2 == None:
        default_value_sheet_name = ''

    selected_sheet_name4 = st.text_input(
        "selected_sheet_name", 
        value=default_value_sheet_name, 
        placeholder='Example: Select/Insert/Update', 
        key="item_root_path_tab4"
    )

    DAILY_FOLDER_STR4 = st.text_input(
        "Daily folder", 
        value=DAILY_FOLDER_STR2, 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab4"
    )


    txt_items4 = st.text_area(
        "Input list (tab-separated: NO, FILE_PATH, FILE_NAME, ...):", 
        height=300, 
        value=txt_items, 
        key="input_list_tab4"
    )

    btn_merge = st.button("Merge sources")

    if btn_merge:
        st.info("source_type: " + SOURCE_TYPE4)
        source_configs = get_configs_by_source_type(SOURCE_TYPE4)

        if not source_configs.SVN_ROOT_PATH:
            st.warning("Please set SVN_ROOT_PATH in config")
        elif sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name4, None) is None:
            st.warning("Please select valid excel file name")
        elif not DAILY_FOLDER_STR4:
            st.warning("Please input daily folder name.")
        elif not txt_items4.strip():
            st.warning("Please input item list.")
        else:
            FULL_ITEM_ROOT_PATH4 = f'{source_configs.ROOT_OUTPUT_PATH}/{selected_excel_file_name4}/{selected_sheet_name4}'
            FULL_DAILY_FOLDER_PATH4 = f"{FULL_ITEM_ROOT_PATH4}/{DAILY_FOLDER_STR4}" if DAILY_FOLDER_STR4 else None

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
                    daily_files = file_utils.get_target_files(FULL_DAILY_FOLDER_PATH4, source_configs.SUFFIXES)
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
                                        dest_file_path = (f"{source_configs.SVN_ROOT_PATH}{file_path + file_name}").replace('/','\\')
                                        st.write(f"Original file: {original_path_file}")
                                        st.write(f"Change file: {change_path_file}")
                                        st.write(f"Destination file: {dest_file_path}")
                                        encoding = handler.get_encoded_file(original_path_file)
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
                        st.write(f"File: {file_path} | status (Excel): {info['status']}\n" )
                        for line in info["lines"]:
                            st.write(f"    {line}\n")
                        st.write("\n")
            else:
                st.write("Không phát hiện dòng nào chứa CAST với trạng thái x.\n")
            

with tab6:
    # Input field for pasted code
    source_type = st.radio("Source Type", ('Java', 'C'), horizontal=True, key="source_type_tab6")
    sub_excel_file_name_to_sheet_type_map = FILE_EXCEL_NAME_TO_SHEET_TYPE_MAP_BY_SOURCE_TYPE.get(source_type.lower(), {})
    selected_excel_file_name = st.selectbox(
        "Select excel file name",
        options=list(sub_excel_file_name_to_sheet_type_map.keys()),
        index=None, 
        key="excel_file_name_tab6"
    )
    selected_sheet_name6 = st.selectbox(
        "Select sheet name",
        options=SUB_ITEM_FOLDER_OPTIONS,
        index=None, 
        key="item_root_path_tab6"
    )

    code_input = st.text_area("Paste your code here (Java / SQL / XML/...):", height=300, key="code_input_tab3")

    txt_tables =st.text_input("Tables (comma-separated)")

    col1, col2, col3, col4 = st.columns(4)
    source_configs = get_configs_by_source_type(source_type)
    system_types: List[int] = sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name, [])

    # Button to trigger analysis
    if col1.button("Check data type"):
        if sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name, None) is None:
            st.warning("Please select valid excel file name")
        if not code_input.strip():
            st.warning("Please input code first.")
        else:
            extra_tables = common_util.convert_and_upper_str_to_list(txt_tables)
            code_by_line = code_input.splitlines()
            lines = [line if line.startswith("\n") else f"{line}\n" for line in code_by_line]
            handler.show_data_type(lines, system_types, extra_tables, True)
        pass

    is_export_excel = col2.checkbox("Export evidence excel", value=False, key="export_excel_tab6")
    if col2.button("Export full Code"):
        if sub_excel_file_name_to_sheet_type_map.get(selected_excel_file_name, None) is None:
            st.warning("Please select valid excel file name")
        if not code_input.strip():
            st.warning("Please input code first.")
        else:
            try:
                evidence_excel_path = Path(RESOURCE_ROOT_PATH) / OUTPUT_EVIDENCE_EXCEL_NAME
                app = None
                if is_export_excel:
                    shutil.copy(FULL_EVIDENCE_INPUT_PATH, evidence_excel_path)
                    app = xw.App(visible=False)
                extra_tables = common_util.convert_and_upper_str_to_list(txt_tables)
                code_by_line = code_input.splitlines()
                lines = [line if line.startswith("\n") else f"{line}\n" for line in code_by_line]
                line_indexes = list(range(0, len(lines)))
                active_rule_set = set(source_configs.RULE_CONFIGS.get(selected_sheet_name6.upper(), []))
                new_lines = handler.process_and_replace_lines(app, lines, line_indexes, evidence_excel_path, source_type, active_rule_set,  system_types, extra_tables)
                st.markdown("### Processed Code with Replacements")
                if is_export_excel:
                    st.warning(f"Exported evidence to: {evidence_excel_path}")
                final_code = "".join(new_lines)
                st.code(final_code)
            finally:
                if 'app' in locals() and app:
                    app.quit()
                    del app
                
with tab7:
    SOURCE_TYPE7 = st.radio("Source Type", SOURCE_TYPE_OPTIONS ,  index= 1,horizontal=True, key="source_type_tab7", disabled=True)
    selected_sheet_name = st.selectbox(
        "Select sheet name",
        options=SUB_ITEM_FOLDER_FOR_SOURCE_C_OPTIONS,
        index=0, 
        key="item_root_path_tab7"
    )
    
    DAILY_FOLDER_STR = st.text_input(
        "Daily folder", 
        placeholder='Example: 2025_07_30', 
        key="daily_folder_tab7",
        value=common_util.get_current_date_str()
    )

    txt_items = st.text_area("Input list (tab-separated: NO, FILE_PATH, FILE_NAME, START_LINE):", height=300, key="input_list_tab7")

    btn_col1, = st.columns(1)
    btn_init = btn_col1.button("Run", key="btn_init_tab7")

    if btn_init:
        if not DAILY_FOLDER_STR:
            st.warning(" Please input daily folder name")
        elif not txt_items.strip():
            st.warning(" Please input item list")
        else:
            source_configs = get_configs_by_source_type(SOURCE_TYPE7)
            FULL_ITEM_ROOT_PATH = f'{source_configs.ROOT_OUTPUT_PATH}/{selected_sheet_name}'
            FULL_DAILY_FOLDER_PATH = f"{FULL_ITEM_ROOT_PATH}/{DAILY_FOLDER_STR}" if DAILY_FOLDER_STR else None

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
                item_map = {item_no: (src_label, full_file_name, start_line) for item_no, src_label, full_file_name, start_line in items}
                created_items = []

                for item_no in sorted(item_map.keys()):
                    src_label, full_file_name, start_line = item_map.get(item_no)
                    des_folder_name = f"{FULL_DAILY_FOLDER_PATH}/No.{item_no}"
                    os.makedirs(des_folder_name, exist_ok=True)

                    # Extract file info
                    try:
                        file_type = full_file_name.split('.')[-1]
                        file_name = full_file_name.rsplit('.', 1)[0]

                        src_path = source_configs.ROOT_APP_PATH + "/" +''.join((src_label, full_file_name))[1:]  # remove leading character
                        des_path = f'{des_folder_name}/{full_file_name}'
                        des_path_after = f'{des_folder_name}/{file_name}_after.{file_type}'
                        des_excel_path = f'{des_folder_name}/{EXCEL_FILE_NAME}'
                        des_html_path = f'{des_folder_name}/{HTML_FILE_NAME}'
                        des_evidence_path = f'{des_folder_name}/{OUTPUT_EVIDENCE_EXCEL_NAME}'

                        st.markdown(f"## Start process for No.{item_no}")
                        # Copy template files
                        if os.path.exists(des_path):
                            st.warning(f"File already exists, skipping copy: {des_path}")
                        else:
                            shutil.copy(src_path, des_path)

                        if os.path.exists(des_path_after):
                            os.remove(des_path_after)
                            st.warning(f"File already exists, removed old file: {des_path_after}")
    
                        shutil.copy(src_path, des_path_after)
                        os.chmod(des_path_after, 0o666)
                        # shutil.copy(TEMPLATE_EXCEL_PATH, des_excel_path)
                        shutil.copy(TEMPLATE_HTML_PATH, des_html_path)
                        # shutil.copy(FULL_EVIDENCE_INPUT_PATH, des_evidence_path)
                        
                        # Process it
                        st.code(f"File: {des_path_after}")
                        encoding = handler.get_encoded_file(des_path_after)
                        if not encoding:
                            st.error(f"Encoding could not be detected for {des_path_after}")
                            continue
                        lines = None
                        with open(des_path_after, 'r', encoding=encoding, newline="") as f:
                            lines = f.readlines()
                        if not lines:
                            st.error(f"No lines read from {des_path_after}")
                            continue
                        
                        line_index = common_util.parse_int(start_line)
                        if line_index == -1 or line_index < 1 or line_index > len(lines):
                            st.error(f"Invalid start line {start_line} for file with {len(lines)} lines.")
                            continue
                        query_line = lines[line_index - 1]
                        if not query_line:
                            st.error(f"No lines to process from line {start_line} onwards. value: {query_line}")
                            continue
                        
                        new_lines, matched_rules = detect_c_rules.detect_and_apply_rules(
                            query_line, 
                            SOURCE_TYPE7,
                            set(source_configs.RULE_CONFIGS.get(selected_sheet_name, []))
                        )

                        st.markdown("### Check rules")
                        if len(matched_rules) == 0 :
                            st.success("No rules matched")
                        old_rule = None
                        for rule in matched_rules:
                            if old_rule != rule["rule_no"]:
                                st.markdown(f"##### Rule {rule['rule_no']}:")
                                old_rule = rule["rule_no"]
                            st.warning(f"{rule['detect_value']} -> {rule['replace_value']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("##### Original line")
                            st.code(query_line)
                        with col2:
                            st.markdown("##### Processed line")
                            if new_lines:
                                st.code(new_lines)
                        
                        if query_line != new_lines:
                            lines[line_index - 1] = new_lines
                            with open(des_path_after, 'w', encoding=encoding, newline="") as f:
                                f.writelines(lines)

                        st.success(f"Finished No.{item_no}: Lines {start_line}, Encoding: {encoding}")
                    except Exception as e:
                        st.error(f"Failed to create item No.{item_no}: {e}")
                    
with tab8:
    SOURCE_TYPE8 = st.radio("Source Type", SOURCE_TYPE_OPTIONS ,  index= 1,horizontal=True, key="source_type_tab8")
    txt_items = st.text_area("Input list (tab-separated: NO, FILE_PATH, FILE_NAME, START_LINE):", height=300, key="input_list_tab8")

    btn_col1, = st.columns(1)
    btn_fix_unix_format = btn_col1.button("FIX", key="btn_init_tab8")
    if btn_fix_unix_format:
        if not txt_items.strip():
            st.warning(" Please input item list")
        else:
            source_configs = get_configs_by_source_type(SOURCE_TYPE7)

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
                item_map = {item_no: (src_label, full_file_name, start_line) for item_no, src_label, full_file_name, start_line in items}
                created_items = []

                for item_no in sorted(item_map.keys()):
                    src_label, full_file_name, start_line = item_map.get(item_no)
                    # Extract file info
                    try:
                        file_type = full_file_name.split('.')[-1]
                        file_name = full_file_name.rsplit('.', 1)[0]
                        
                        src_path = source_configs.ROOT_APP_PATH + "/" +''.join((src_label, full_file_name))[1:]
                        file_path = source_configs.SVN_ROOT_PATH + "/" +''.join((src_label, full_file_name))[1:]

                        st.markdown(f"## Start process for No.{item_no}")
                        st.write(str(src_path))
                        st.write(str(file_path))
                        encoding = handler.get_encoded_file(file_path)
                        if not encoding:
                            st.error(f"Encoding could not be detected for {des_path_after}")
                            continue

                        content = None
                        with open(file_path, "r", encoding=encoding, newline="") as f:
                            content = f.read()
                        if content:
                            st.code(f"Original content sample:\n{repr(content[:200])}")
                            content = content.replace("\r\n", "\n")
                            st.code(f"Processed content sample:\n{repr(content[:200])}")
                            with open(file_path, 'w', encoding=encoding, newline="\n") as f:
                                f.writelines(content)
                        else:
                            st.warning(f"No content read from {file_path}")
                            continue
                        st.success(f"Finished No.{item_no}: Lines {start_line}, Encoding: {encoding}")
                    except Exception as e:
                        st.error(f"Failed to create item No.{item_no}: {e}")
