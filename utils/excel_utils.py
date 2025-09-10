from typing import List
import pandas as pd
import xlwings as xw
from pathlib import Path
from config import SHEET_CONFIG_MAP

SHEET_NAME_DEFAULT = 'Sheet1'

def col_letter_to_index(letter):
    return ord(letter.upper()) - ord('A')

def load_all_sheets(excel_path):
    return pd.read_excel(excel_path, sheet_name=None)

def exist_default_sheet_name(sheets) -> bool:
    for sheet in sheets:
        sheet_name = sheet.name.lower()
        if SHEET_NAME_DEFAULT.lower() == sheet_name:
            return True
    return False

def filter_excel(app: xw.App, excel_path, filter_values,  system_types: List[int]):
    input_path = Path(excel_path).resolve()
    wb = app.books.open(str(input_path))
    try:
        if not exist_default_sheet_name(wb.sheets):
            wb.sheets.add(name=SHEET_NAME_DEFAULT)
        # sheets = wb.sheets if sheet_names is None else [wb.sheets[name] for name in sheet_names]
        for sheet in wb.sheets:
            sheet_name: str = sheet.name.lower()
            if sheet_name.startswith("type"):
                match = False
                for system_type in system_types:
                    if sheet_name.startswith(f"type{system_type}"):
                        match = True
                        break
                if not match:
                    sheet.delete()
                    continue
                
            if sheet_name not in SHEET_CONFIG_MAP and sheet_name != SHEET_NAME_DEFAULT.lower():
                sheet.delete()
                continue
            if sheet_name == SHEET_NAME_DEFAULT.lower():
                # Skip default sheet, it will be used for new data
                continue

            cfg = SHEET_CONFIG_MAP[sheet_name]

            # Read full range into pandas
            rng = sheet.range((1, 1), (cfg["num_rows"], cfg["num_cols"])).value
            df = pd.DataFrame(rng)

            # Separate headers and data
            headers = df.iloc[:cfg["number_header_rows"]]
            data = df.iloc[cfg["number_header_rows"]:]

            # Filter rows:
            filter_indices = [ord(c.upper()) - ord('A') for c in cfg["filter_columns"]]
            mask = pd.Series(True, index=data.index)  # Start with all True
            for idx in filter_indices:
                col_series = data[idx].astype(str).str.strip().str.upper()
                mask &= col_series.isin(filter_values)

            filtered_data = data[mask]

            if filtered_data.empty:
                # Delete the sheet if no rows match
                sheet.delete()
            else:
                out_df = pd.concat([headers, filtered_data], ignore_index=True)

                # Clear the relevant range BEFORE writing filtered data
                sheet.range((1, 1), (cfg["num_rows"], cfg["num_cols"])).clear_contents()

                # Write filtered data back to sheet starting at A1
                sheet.range("A1").value = out_df.values
        
        if len(wb.sheets) > 1:
            wb.sheets[SHEET_NAME_DEFAULT].delete()  # Remove the default sheet if it exists
        wb.save()
    finally:
        wb.close()


def filter_and_copy_evidence_data(app: xw.App, input_excel, output_excel, sheet_names=None, filter_values=set()):
    input_path = Path(input_excel).resolve()
    output_path = Path(output_excel).resolve()
    try:
        wb_in = app.books.open(str(input_path))
        if output_path.exists() and output_path.is_file():
            wb_out = app.books.open(str(output_path))
            if "Sheet1" not in  wb_out.sheets:
                wb_out.sheets.add(name="Sheet1")
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