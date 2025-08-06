from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

SUB_ITEM_FOLDERS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']

SHEET_CONFIG_MAP = {
    "schema": {"number_header_rows": 1, "filter_columns": ["D"], "num_cols": 7},
    "table": {"number_header_rows": 1, "filter_columns": ["E"], "num_cols": 9},
    "column": {"number_header_rows": 1, "filter_columns": ["E", "F"], "num_cols": 10},
    "type1": {"number_header_rows": 1, "filter_columns": ["A", "C"], "num_cols": 8},
    "type2": {"number_header_rows": 1, "filter_columns": ["A", "C"], "num_cols": 8},
    "type3": {"number_header_rows": 1, "filter_columns": ["A", "C"], "num_cols": 8},
}
EVIDENCE_EXCEL_SHEETS = ["schema", "table", 'column', 'type1', 'type2', 'type3']
ENCODE_LIST = ['cp932', 'shift_jis']

# CONFIG PATH
OUTPUT_EVIDENCE_EXCEL_NAME = "evidence_v1.xlsx"
FULL_EVIDENCE_INPUT_PATH = os.getenv("FULL_EVIDENCE_INPUT_PATH")
EXCEL_MAPPING_PATH = os.getenv("EXCEL_MAPPING_PATH")
ROOT_APP_PATH = os.getenv("ROOT_APP_PATH")
ROOT_OUTPUT_PATH = os.getenv("ROOT_OUTPUT_PATH")
SVN_ROOT_PATH = os.getenv("SVN_ROOT_PATH").replace('/','\\')
TEMPLATE_FOLDER_PATH = f'{ROOT_OUTPUT_PATH}/template'