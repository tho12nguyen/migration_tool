import re
from typing import List
from logic import text_processing


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
            case 5:
                pattern = re.compile(rule["pattern_detect"], re.IGNORECASE | re.MULTILINE)
                if pattern.search(querySQL) and len(aliasSet) > 0:
                    matched_rules.append(rule)
            case 7:
                if rule["detect_value"] in aliasSet:
                    matched_rules.append(rule)
            case _:
                pattern = re.compile(rule["pattern_detect"], re.IGNORECASE | re.MULTILINE)
                if pattern.search(querySQL):
                    matched_rules.append(rule)
    return matched_rules, query_text, aliasSet