from typing import List,Tuple

from rules import detect_c_rules
from rules import detect_java_rules
from rules import common_detect_rules

def detect_and_apply_rules(lines: List[str], source_type: str, active_rule_set: set, unused_keys: List=[], output_mul_mapping:List=[], output_rule2_mapping: List=[]) -> Tuple[str, List[dict], List[dict]]:
    rules = common_detect_rules.load_all_rules(source_type)
    match source_type.lower():
        case 'java':
            matched_rules, query_text, aliasSet =  detect_java_rules.detect_rules(lines, rules, active_rule_set)
        case 'c':
             matched_rules, query_text, aliasSet =  detect_c_rules.detect_rules(lines, rules, active_rule_set)  
        case _:
            raise ValueError(f"value source_type: {source_type}, source_type must be either 'java' or 'c'")

    common_detect_rules.show_result_on_ui(matched_rules, unused_keys, output_mul_mapping, output_rule2_mapping)
    return query_text, aliasSet, matched_rules