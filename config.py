# -*- coding: euc_jp -*-

from pathlib import Path
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from utils import common_util

load_dotenv()


SUB_ITEM_FOLDER_OPTIONS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'MERGE']

SUB_ITEM_FOLDER_FOR_SOURCE_C_OPTIONS = ['NEXTVAL', 'SQLCA', "EXEC_SQL", "DB2_CONNECT", "SQLINT", "SQL_H", "SQLCODE"]

SHEET_CONFIG_MAP = {
    "schema": {"number_header_rows": 3, "filter_columns": ["D"], "num_cols": 8, "num_rows": 15},
    "table": {"number_header_rows": 3, "filter_columns": ["E"], "num_cols": 9, "num_rows": 700},
    "column": {"number_header_rows": 3, "filter_columns": ["E", "F"], "num_cols": 10, "num_rows": 11_000},
    "key": {"number_header_rows": 3, "filter_columns": [ "F"], "num_cols": 9, "num_rows": 100},
    "type1.1": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 2500},
    "type1.2": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 3500},
    "type2.1": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 1000},
    "type2.2": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 3500},
    "type2.3": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 300},
    "type3.1": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 500},
    "type3.2": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 100},
    "type3.3": {"number_header_rows": 1, "filter_columns": ["C", "E"], "num_cols": 10, "num_rows": 100}
}

EVIDENCE_EXCEL_SHEETS = ["schema", "table", 'column', 'key', 'type1.1' , 'type1.2',  'type2.1' , 'type2.2', 'type2.3', 'type3.1' , 'type3.2', 'type3.3']

# COMMON CONFIG PATH
OUTPUT_EVIDENCE_EXCEL_NAME = "evidence.xlsx"
RESOURCE_ROOT_PATH = os.getenv("RESOURCE_ROOT_PATH")
FULL_EVIDENCE_INPUT_PATH = RESOURCE_ROOT_PATH + "/resources/evidence.xlsx" 

TEMPLATE_FOLDER_PATH = f'{RESOURCE_ROOT_PATH}/resources/template'
HTML_FILE_NAME, EXCEL_FILE_NAME = common_util.get_first_htm_and_xlsx(TEMPLATE_FOLDER_PATH)
TEMPLATE_HTML_PATH = f'{TEMPLATE_FOLDER_PATH}/{HTML_FILE_NAME}'
TEMPLATE_EXCEL_PATH = f'{TEMPLATE_FOLDER_PATH}/{EXCEL_FILE_NAME}'

# JAVA CONFIG
RULES_ROOT_PATH = RESOURCE_ROOT_PATH + "/resources/rules/java_rules"
ROOT_APP_PATH = os.getenv("ROOT_APP_PATH")
ROOT_OUTPUT_PATH = os.getenv("ROOT_OUTPUT_PATH")
SVN_ROOT_PATH = os.getenv("SVN_ROOT_PATH").replace('/','\\')

# C CONFIG
C_RULES_ROOT_PATH = RESOURCE_ROOT_PATH + "/resources/rules/c_rules"
C_ROOT_APP_PATH = os.getenv("C_ROOT_APP_PATH")
C_ROOT_OUTPUT_PATH = os.getenv("C_ROOT_OUTPUT_PATH")
C_SVN_ROOT_PATH = os.getenv("C_SVN_ROOT_PATH").replace('/','\\')
# c# CONFIG


SOURCE_TYPE_OPTIONS = ['java', 'c']
FILE_EXCEL_NAME_TO_SHEET_TYPE_MAP_BY_SOURCE_TYPE = {
    "java" : {
        "webbk_ct": [1],
        "webbk_fb": [1],
        "webbk_JavaBatch": [1],
        "webbk": [1],
        "otpif": [3],
        "webfb_ct": [2],
        "webfb": [2],
        "webfb-polling": [2]
    },
    "c" : {
        "wbroot": [1],
        "fbroot": [2],
        "pdf_fax": [2],
        "zenroot":[2],
        "comroot": [1,2],
        "No.23,24": [1,2],
    }
}

@dataclass
class SouceConfig:
    RULES_ROOT_PATH: str
    ROOT_APP_PATH: str
    ROOT_OUTPUT_PATH: str
    SVN_ROOT_PATH: str
    SUFFIXES: list
    RULE_CONFIGS: dict[str, set]  # SHEET TYPE -> LIST RULE BY SHEET TYPE 

def get_configs_by_source_type(source_type: str) -> SouceConfig:
    match source_type.lower():
        case 'java':
            return SouceConfig(
                RULES_ROOT_PATH,
                ROOT_APP_PATH,
                ROOT_OUTPUT_PATH,
                SVN_ROOT_PATH,
                 ['_after.sql', '_after.xml', '_after.java'],
                 {}
            )
        case 'c':
            return SouceConfig(
                C_RULES_ROOT_PATH,
                C_ROOT_APP_PATH,
                C_ROOT_OUTPUT_PATH,
                C_SVN_ROOT_PATH,
                 ['_after.sqc', '_after.h', '_after.sh', '_after.c', '_after.txt', '_after.conf', '_after.ini'],
                 {
                    "SELECT": [1,2,3,5,6,7,8,9,10,11,12,13,14,15,17,29,30],
                    "UPDATE": [1,2, 4,5,6,7,8,9,10,12,13,15,29,30],
                    "INSERT": [1,2,5,6,7,8,9,10,12,13,15,29,30],
                    "DELETE": [1,2,5,6,7,8,9,10,12,13,15,29,30],
                    "MERGE": [1,2, 4,5,6,7,8,9,10,12,13,15,29,30],
                    "SQLCODE": [22],
                    'NEXTVAL': [3],
                    "SQLCA": [16, 19, 26],
                    "EXEC_SQL": [18, 25],
                    "DB2_CONNECT": [18],
                    "No.20": [20],
                    "SQLINT": [21],
                    "SQL_H": [27],
                    "db2SQL": [28, 29, 30],
                 },
            )
        case _:
            raise ValueError(f"value source_type: {source_type}, source_type must be either 'java' or 'c'")