import re
from typing import List, Tuple
from logic import text_processing
from rules import detect_c_rule28
from rules import common_detect_rules
from rules import detect_c_rule22


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
        query = detect_c_rule22.transform_line_for_rule22(query)


    rules = common_detect_rules.load_all_rules(source_type)
    matched_rules = []
    if 28 in active_rule_set:
        rule28 = [rules[i] for i in range(len(rules)) if rules[i]["rule_no"] == 28]
        query = detect_c_rule28.transform_line_for_rule28(query, rule28)
    for rule in rules:
        rule_no = rule["rule_no"]
        if active_rule_set and rule_no not in active_rule_set:
            continue
        if "pattern_detect" not in rule or "replace_value" not in rule:
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