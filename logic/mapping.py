from typing import Set
from pandas import DataFrame

def get_full_schema_table_and_column_names_from_sheets(sheets) -> Set[str]:
    df: DataFrame  = sheets.get('column')
    result_set =  {str(row[i]).upper() for row in df.to_numpy() for i in range(2, 6) if row[i]}
    for row in sheets['key'].to_numpy()[2:]:
        result_set.add(row[5].upper())
    return result_set

def build_mappings(sheets) -> tuple:
    schema_dict, table_dict, column_dict, key_dict = {}, {}, {}, {}
    for row in sheets['schema'].to_numpy()[2:]:
        schema_dict.setdefault(row[3], set()).add(row[5])
    for row in sheets['table'].to_numpy()[2:]:
        table_dict.setdefault(row[4], set()).add(row[7])
    for row in sheets['column'].to_numpy()[2:]:
        table, column, value = row[4], row[5], row[9]
        column_dict.setdefault(table, {}).setdefault(column, set()).add(value)
    for row in sheets['key'].to_numpy()[2:]:
        key_dict.setdefault(row[5], set()).add(row[8])
    return schema_dict, table_dict, column_dict, key_dict

def build_full_mapping(used_keys, schema_dict, table_dict, column_dict, key_dict) -> dict:
    full_mapping = schema_dict.copy()
    full_mapping.update(key_dict)
    
    for table in used_keys:
        if table in table_dict:
            full_mapping[table] = table_dict[table]
            column_dict_by_table = column_dict.get(table, {})
            for column, values in column_dict_by_table.items():
                if column not in full_mapping:
                    full_mapping[column] = set()
                full_mapping[column].update(values)
    return full_mapping


