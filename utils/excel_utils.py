import pandas as pd
import xlwings as xw
from pathlib import Path
from config import SHEET_CONFIG_MAP

def col_letter_to_index(letter):
    return ord(letter.upper()) - ord('A')

def load_all_sheets(excel_path):
    return pd.read_excel(excel_path, sheet_name=None)

def filter_and_copy_evidence_data(app: xw.App, input_excel, output_excel, sheet_names=None, filter_values=set()):
    input_path = Path(input_excel).resolve()
    output_path = Path(output_excel).resolve()
    try:
        wb_in = app.books.open(str(input_path))
        if output_path.exists() and output_path.is_file():
            wb_out = app.books.open(str(output_path))
            temp_sheet = wb_out.sheets.add(name="Sheet1")
            for sht in wb_out.sheets:
                if sht.name != "Sheet1":
                    sht.delete()
        else:
            wb_out = app.books.add()
            wb_out.save(str(output_path))
        sheets = wb_in.sheets if sheet_names is None else [wb_in.sheets[name] for name in sheet_names]
        for sheet in sheets:
            sheet_name = sheet.name.lower()
            if sheet_name not in SHEET_CONFIG_MAP:
                continue
            config = SHEET_CONFIG_MAP[sheet_name]
            header_rows = config["number_header_rows"]
            filter_cols_letters = config["filter_columns"]
            num_cols = config["num_cols"]
            used_range = sheet.used_range
            all_data = used_range.value
            if not all_data or len(all_data) <= header_rows:
                continue
            data_rows = all_data[header_rows:]
            add_col_index = 0
            if not sheet_name.startswith("type"):
                add_col_index = -1
            filter_col_indices = [col_letter_to_index(c) + add_col_index for c in filter_cols_letters]
            match_rows = []
            for i, row in enumerate(data_rows):
                if not row:
                    continue
                if all(col_idx < len(row) and str(row[col_idx]).strip() in filter_values for col_idx in filter_col_indices):
                    match_rows.append(i)
            if not match_rows:
                continue
            dst_sheet_name = f"{sheet.name}"
            if dst_sheet_name in [s.name for s in wb_out.sheets]:
                wb_out.sheets[dst_sheet_name].delete()
            dst_sheet = wb_out.sheets.add(name=dst_sheet_name, before=wb_out.sheets[len(wb_out.sheets) - 1])
            src_header = sheet.range("A1").resize(header_rows, num_cols)
            dst_header = dst_sheet.range("A1")
            src_header.copy(dst_header)
            for dst_i, src_i in enumerate(match_rows, start=header_rows + 1):
                excel_row_num = src_i + header_rows + 1
                src_row = sheet.range(f"A{excel_row_num}").resize(1, num_cols)
                dst_row = dst_sheet.range(f"A{dst_i}")
                src_row.copy(dst_row)
            for col in range(1, num_cols + 1):
                dst_sheet.range((1, col)).column_width = sheet.range((1, col)).column_width
            for row in range(1, header_rows + len(match_rows) + 1):
                dst_sheet.range((row, 1)).row_height = sheet.range((row, 1)).row_height
        if len(wb_out.sheets) > 1:
            for sht in wb_out.sheets:
                if sht.name == "Sheet1":
                    sht.delete()
    finally:
        if wb_out:
            wb_out.save()
            wb_out.close()
        if wb_in:
            wb_in.close()