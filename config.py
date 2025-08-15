from pathlib import Path
import os
from dotenv import load_dotenv

from utils import common_util

load_dotenv()

SUB_ITEM_FOLDERS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']

SHEET_CONFIG_MAP = {
    "schema": {"number_header_rows": 3, "filter_columns": ["D"], "num_cols": 8, "num_rows": 15},
    "table": {"number_header_rows": 3, "filter_columns": ["E"], "num_cols": 9, "num_rows": 700},
    "column": {"number_header_rows": 3, "filter_columns": ["E", "F"], "num_cols": 10, "num_rows": 11_000},
    "type1": {"number_header_rows": 1, "filter_columns": ["A", "C"], "num_cols": 8, "num_rows": 1200},
    "type2": {"number_header_rows": 1, "filter_columns": ["A", "C"], "num_cols": 8, "num_rows": 3500},
    "type3": {"number_header_rows": 1, "filter_columns": ["A", "C"], "num_cols": 8, "num_rows": 300},
}
EVIDENCE_EXCEL_SHEETS = ["schema", "table", 'column', 'type1', 'type2', 'type3']
ENCODE_LIST = ['cp932', 'shift_jis']

# CONFIG PATH
OUTPUT_EVIDENCE_EXCEL_NAME = "evidence.xlsx"
RESOURCE_ROOT_PATH = os.getenv("RESOURCE_ROOT_PATH")
FULL_EVIDENCE_INPUT_PATH = RESOURCE_ROOT_PATH + "/resources/evidence.xlsx" 
ROOT_APP_PATH = os.getenv("ROOT_APP_PATH")
ROOT_OUTPUT_PATH = os.getenv("ROOT_OUTPUT_PATH")
SVN_ROOT_PATH = os.getenv("SVN_ROOT_PATH").replace('/','\\')


TEMPLATE_FOLDER_PATH = f'{RESOURCE_ROOT_PATH}/resources/template'
HTML_FILE_NAME, EXCEL_FILE_NAME = common_util.get_first_htm_and_xlsx(TEMPLATE_FOLDER_PATH)
TEMPLATE_HTML_PATH = f'{TEMPLATE_FOLDER_PATH}/{HTML_FILE_NAME}'
TEMPLATE_EXCEL_PATH = f'{TEMPLATE_FOLDER_PATH}/{EXCEL_FILE_NAME}'