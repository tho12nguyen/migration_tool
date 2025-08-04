from pathlib import Path

def get_first_htm_and_xlsx(folder_path: str):
    folder = Path(folder_path)

    htm_file = next((f.name for f in folder.glob("*.htm")), None)
    xlsx_file = next((f.name for f in folder.glob("*.xlsx")), None)

    return htm_file, xlsx_file