import re
from typing import List

options_map = {
    "OF DEL": "DELIMITER ','",
    "OF WSF": "DELIMITER E'\\t'",
    "MODIFIED BY nochardel": "FORMAT text",
    "MODIFIED BY chardel\\\"\\\"": "",
    "MODIFIED BY codepage=943": "ENCODING 'SJIS'",
    "MODIFIED BY codepage=932": "ENCODING 'SJIS'",
    "MODIFIED BY codepage=1208": "ENCODING 'UTF8'",
    "MODIFIED BY codepage=954": "ENCODING 'EUC_JP'",
    "MODIFIED BY codepage=20932": "ENCODING 'EUC_JIS_2004'",
    "MODIFIED BY codepage=50220": "ENCODING 'ISO-2022-JP'"
}


def normalize_select(sql: str) -> str:
    """Flatten multi-line SELECT into one line (remove line breaks)."""
    return re.sub(r"\s+", " ", sql.strip())


def convert_options(db2_cmd: str) -> list[str]:
    """Extract MODIFIED BY options and map them to PostgreSQL equivalents."""
    pg_opts = []
    for db2_opt, pg_opt in options_map.items():
        if re.search(db2_opt, db2_cmd, flags=re.IGNORECASE):
            if pg_opt:
                pg_opts.append(pg_opt)

    if not any(opt.startswith("FORMAT") for opt in pg_opts):
        pg_opts.insert(0, "FORMAT csv")

    return pg_opts


def format_log_redirection(existing_redir: str) -> str:
    if not existing_redir:
        return ""

    pattern = re.compile(r"\s*(\S+)(.*)", flags=re.IGNORECASE)
    m = pattern.search(existing_redir.strip())
    if not m:
        return existing_redir.strip()  # return unchanged if no match

    logfile, rest = m.groups()
    logfile = logfile.strip("\"'")

    return f'> "{logfile}"{rest}'


def transform_line_for_rule28(command: str, rules: List[dict]) -> str:
    for r in rules:
        if "pattern_detect" not in r:
            continue
        m = re.search(r["pattern_detect"], command, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            continue

        template = r.get("replace_template")

        # ==== EXPORT ====
        if template == "psql_block":
            outputfile, of_type, select_sql, logfile = m.groups()
            pg_opts = ", ".join(convert_options(command))
            select_sql = normalize_select(select_sql)
            redir = format_log_redirection(logfile)
            return (
                f'PGPASSWORD="${{ECOM_DB_PASSWD}}" psql -U "${{ECOM_DB_USERID}}" '
                f'-d "${{ECOM_DB_NAME}}" {redir} <<EOF\n'
                f'\\copy ({select_sql}) TO \'{outputfile}\' WITH ({pg_opts});\n'
                f'EOF\n'
            )

        elif template == "psql_var_block":
            varname, outputfile, of_type, select_sql, logfile = m.groups()
            pg_opts = ", ".join(convert_options(command))
            select_sql = normalize_select(select_sql)
            redir = format_log_redirection(logfile)
            return (
                f'{varname}=$(PGPASSWORD="${{ECOM_DB_PASSWD}}" psql -U "${{ECOM_DB_USERID}}" '
                f'-d "${{ECOM_DB_NAME}}" {redir} <<EOF\n'
                f'\\copy ({select_sql}) TO \'{outputfile}\' WITH ({pg_opts});\n'
                f'EOF\n'
                f')\n'
            )

        # ==== IMPORT INSERT INTO ====
        elif template == "psql_block_import":
            infile, table, logfile = m.groups()
            pg_opts = "FORMAT csv, DELIMITER ','"
            redir = format_log_redirection(logfile)
            return (
                f'PGPASSWORD="${{ECOM_DB_PASSWD}}" psql -U "${{ECOM_DB_USERID}}" '
                f'-d "${{ECOM_DB_NAME}}" {redir} <<EOF\n'
                f'\\copy {table} FROM \'{infile}\' WITH ({pg_opts});\n'
                f'EOF\n'
            )

        elif template == "psql_var_block_import":
            varname, infile, table = m.groups()
            pg_opts = "FORMAT csv, DELIMITER ','"
            return (
                f'{varname}=$(PGPASSWORD="${{ECOM_DB_PASSWD}}" psql -U "${{ECOM_DB_USERID}}" '
                f'-d "${{ECOM_DB_NAME}}" <<EOF\n'
                f'\\copy {table} FROM \'{infile}\' WITH ({pg_opts});\n'
                f'EOF\n'
                f')\n'
            )

        # ==== IMPORT REPLACE INTO ====
        elif template == "psql_block_import_replace":
            infile, table, logfile = m.groups()
            pg_opts = "FORMAT csv, DELIMITER ',', ENCODING 'EUC_JP'"
            redir = format_log_redirection(logfile)
            return (
                f'PGPASSWORD="${{ECOM_DB_PASSWD}}" psql -U "${{ECOM_DB_USERID}}" '
                f'-d "${{ECOM_DB_NAME}}" {redir} <<EOF\n'
                f'TRUNCATE TABLE {table};\n'
                f'\\copy {table} FROM \'{infile}\' WITH ({pg_opts});\n'
                f'EOF\n'
            )

        elif template == "psql_var_block_import_replace":
            varname, infile, table = m.groups()
            pg_opts = "FORMAT csv, DELIMITER ',', ENCODING 'EUC_JP'"
            return (
                f'{varname}=$(PGPASSWORD="${{ECOM_DB_PASSWD}}" psql -U "${{ECOM_DB_USERID}}" '
                f'-d "${{ECOM_DB_NAME}}" <<EOF\n'
                f'TRUNCATE TABLE {table};\n'
                f'\\copy {table} FROM \'{infile}\' WITH ({pg_opts});\n'
                f'EOF\n'
                f')\n'
            )

    return command
