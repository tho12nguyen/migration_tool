import re
from typing import List, Tuple
from logic import text_processing
from rules import common_detect_rules


# Mapping table for rule 22
code_map = {
    "-407": "23502",
    "-204": "42P01",
    "-539": "42704",
    "-601": "42P07",
    "-612": "42701",
    "-624": "42P16",
    "-803": "23505",
    "-911": "40P01",
}

def detect_rules(lines: List[str], rules, active_rule_set: set):
    raw_query = ''.join(lines)
    querySQL = text_processing.extract_sql_fragments(raw_query)
    query_text = text_processing.extract_query_text(querySQL)
    aliasSet = text_processing.find_aliases(query_text)

    matched_rules = []
    for rule in rules:
        rule_no = rule["rule_no"]
        # Skip rule_no not in the list
        if active_rule_set and rule_no not in active_rule_set:
            continue
        match rule_no:
            case 4:
                pattern = re.compile(rule["pattern_detect"], re.IGNORECASE | re.MULTILINE)
                if pattern.search(querySQL) and len(aliasSet) > 0:
                    matched_rules.append(rule)
            case 6:
                if rule["detect_value"] in aliasSet:
                    matched_rules.append(rule)
            case 8:
                matched_rule = detect_rule8(querySQL, rule)
                if matched_rule:
                    matched_rules.extend(matched_rule)
            case _:
                pattern = re.compile(rule["pattern_detect"], re.IGNORECASE | re.MULTILINE)
                if pattern.search(querySQL):
                    matched_rules.append(rule)
    return matched_rules, query_text, aliasSet

def detect_rule8(querySQL: str, rule: dict) -> List[dict]:
    matched_rules = []
    detect_value: dict = rule['detect_value']
    table_mapping: dict = detect_value.get("tables", {})
    column_mapping: dict = detect_value.get("columns", {})
    exist_table = False
    for table_key, table_value in table_mapping.items():
        if re.search(rf'\b{table_key}\b', querySQL, flags=re.IGNORECASE):
            exist_table = True
            clone_rule = rule.copy()
            clone_rule['detect_value'] = table_key
            clone_rule['pattern_detect'] = rf'\b{table_key}\b'
            clone_rule['replace_value'] = table_value
            matched_rules.append(clone_rule)

    if not exist_table:
        return matched_rules
    
    for column_key, column_value in column_mapping.items():
       if re.search(rf'\b{column_key}\b', querySQL, flags=re.IGNORECASE):
            clone_rule = rule.copy()
            clone_rule['detect_value'] = column_key
            clone_rule['pattern_detect'] = rf'\b{column_key}\b'
            clone_rule['replace_value'] = column_value
            matched_rules.append(clone_rule)
    return matched_rules


def detect_and_apply_rules(query: str, source_type: str, active_rule_set: set) -> Tuple[str, List[dict]]:
    """
    Apply regex-based replacement rules to the input query.
    """
    if 22 in active_rule_set:
        query = transform_line_for_rule22(query)

    rules = common_detect_rules.load_all_rules(source_type)
    matched_rules = []
    for rule in rules:
        rule_no = rule["rule_no"]
        if active_rule_set and rule_no not in active_rule_set:
            continue
        pattern = rule["pattern_detect"]
        replace = rule["replace_value"]
        
        if re.search(pattern, query, flags=re.IGNORECASE):
            matched_rules.append(rule)
            query = re.sub(pattern, replace, query, flags=re.IGNORECASE)
            if rule_no == 20:
                while re.search(pattern, query, flags=re.IGNORECASE):
                    query = re.sub(pattern, replace, query, flags=re.IGNORECASE)    
    return query, matched_rules


def is_in_comment_or_string_for_rule22(line: str, pos: int) -> bool:
    """
    Check if a match is inside a comment (//) or string ("...").
    """
    comment_pos = line.find("//")
    quote_pos = line.find('"')
    return (comment_pos != -1 and pos > comment_pos) or (quote_pos != -1 and pos > quote_pos)


def replace_defines_for_rule22(line: str) -> str:
    """
    Case 1: Replace #define SQLCODE with SQLSTATE
    """
    def repl(m):
        prefix, name, suffix, code, comment = m.groups()
        if code in code_map:
            return f'{prefix}{name}_SQLSTATE_{suffix}   "{code_map[code]}"{comment or ""}'
        return m.group(0)

    return re.sub(r'(#define\s+)(\w+)_SQLCODE_(\w+)\s+(-?\d+)(\s*//.*)?', repl, line)


def replace_conditions_for_rule22(line: str) -> str:
    """
    Case 2: Replace SQLCODE checks (numeric + macro) with SQLSTATE_CHECK
    """
    # Replace numeric codes
    def repl_num(m):
        op, code = m.groups()
        if is_in_comment_or_string_for_rule22(line, m.start()):
            return m.group(0)
        if code in code_map:
            if op == "==":
                return f'SQLSTATE_CHECK("{code_map[code]}")'
            elif op == "!=":
                return f'!SQLSTATE_CHECK("{code_map[code]}")'
        return m.group(0)

    line = re.sub(r'SQLCODE\s*([!=]=)\s*(-?\d+)', repl_num, line)

    # Replace macro codes
    def repl_macro_for_rule22(m):
        op, macro = m.groups()
        if is_in_comment_or_string_for_rule22(line, m.start()):
            return m.group(0)
        if "_SQLCODE_" in macro:
            sqlstate_macro = macro.replace("_SQLCODE_", "_SQLSTATE_")
            if op == "==":
                return f'SQLSTATE_CHECK({sqlstate_macro})'
            elif op == "!=":
                return f'!SQLSTATE_CHECK({sqlstate_macro})'
        return m.group(0)

    line = re.sub(r'SQLCODE\s*([!=]=)\s*(\w+_SQLCODE_\w+)', repl_macro_for_rule22, line)

    return line


# Allowed log-output functions
log_funcs = [
    "sprintf", "fprintf",
    "FKCI_LogPrnt", "DBGOUT01", "FCIB_LogPrnt",
    "FJG_kz_LogPrint", "FJG_LogPrint",
    "FWGF_LogPrnt", "FWGI_LogPrn",
    "FWMH_LogPrnt", "FWSR_logprint",
    "DBG_MSG"
]

log_func_pattern = r"(?:{})".format("|".join(log_funcs))


def replace_log_output_for_rule22(line: str) -> str:
    """
    Replace SQLCODE with SQLSTATE_GET() in function arguments (sprintf, fprintf, etc.)
    and remove (int) cast if directly applied to SQLCODE.
    """

    # 1. Remove (int) cast if it's right before SQLCODE
    line = re.sub(r'\(int\)\s*SQLCODE', 'SQLSTATE_GET()', line)

    # 2. Replace plain SQLCODE when used as argument (inside (), , , etc.)
    line = re.sub(r'([,(]\s*)SQLCODE(\s*[,)])', r'\1SQLSTATE_GET()\2', line)

    return line


def transform_line_for_rule22(line: str) -> str:
    """
    Apply all transformations (define + conditions).
    """
    line = replace_defines_for_rule22(line)
    line = replace_conditions_for_rule22(line)
    line = replace_log_output_for_rule22(line)
    return line