from pathlib import Path
from datetime import datetime


def get_current_date_str() -> str:
    return datetime.now().strftime("%Y_%m_%d")

def get_first_htm_and_xlsx(folder_path: str):
    folder = Path(folder_path)

    htm_file = next((f.name for f in folder.glob("*.htm")), None)
    xlsx_file = next((f.name for f in folder.glob("*.xlsx")), None)

    return htm_file, xlsx_file