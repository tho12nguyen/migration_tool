
def build_mappings(sheets) -> tuple:
    schema_dict, table_dict, column_dict = {}, {}, {}
    for row in sheets['schema'].to_numpy()[1:]:
        schema_dict.setdefault(row[2], set()).add(row[4])
    for row in sheets['table'].to_numpy()[1:]:
        table_dict.setdefault(row[3], set()).add(row[6])
    for row in sheets['column'].to_numpy()[1:]:
        table, column, value = row[3], row[4], row[8]
        column_dict.setdefault(table, {}).setdefault(column, set()).add(value)
    return schema_dict, table_dict, column_dict

def build_full_mapping(used_keys, schema_dict, table_dict, column_dict):
    full_mapping = schema_dict.copy()
    for table in used_keys:
        if table in table_dict:
            full_mapping[table] = table_dict[table]
            full_mapping.update(column_dict.get(table, {}))
    return full_mapping


