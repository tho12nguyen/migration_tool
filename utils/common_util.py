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