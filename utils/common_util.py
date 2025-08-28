from pathlib import Path
from datetime import datetime
from typing import List


def get_current_date_str() -> str:
    return datetime.now().strftime("%Y_%m_%d")

def get_first_htm_and_xlsx(folder_path: str):
    folder = Path(folder_path)

    htm_file = next((f.name for f in folder.glob("*.htm")), None)
    xlsx_file = next((f.name for f in folder.glob("*.xlsx")), None)

    return htm_file, xlsx_file


def convert_and_upper_str_to_list(input_text: str, sp=",") -> List[str]:
    if not input_text:
        return []
    
    result = input_text.split(sp)
    return [item.strip().upper() for item in result]


def get_index_from_list(options: List[str], selected_option: str) -> int:
    try:
        return options.index(selected_option)
    except ValueError:
        return 0

def parse_int(value: str, default: int = -1) -> int:
    """
    Safely parse a string into an integer.
    Returns `default` if parsing fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def get_files_by_no_and_name(daily_files: list[str], numb: int, file_name: str) -> list[str]:
    name_only = Path(file_name).stem
    target = f"No.{numb}"
    result = []

    for f in daily_files:
        p = Path(f)
        if target in p.parts and name_only in p.stem:
            result.append(str(f)) 
    return result