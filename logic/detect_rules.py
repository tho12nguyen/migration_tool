import json
import re
from config import RULES_ROOT_PATH
from pathlib import Path
from logic import text_processing
import streamlit as st

@st.cache_data()
def load_all_rules():
    rules = []
    rules_path = Path(RULES_ROOT_PATH)

    for json_file in rules_path.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    rules.extend(data)  # each file may contain a list of rules
                elif isinstance(data, dict):
                    rules.append(data)  # or a single dict rule
            except json.JSONDecodeError as e:
                print(f"? Error parsing {json_file}: {e}")
    
    # sort by rule_no
    rules.sort( key= lambda r: r.get('rule_no', 0))
    return rules

def detect_rules(raw_query, rules):
    querySQL = text_processing.extract_sql_fragments(raw_query)
    query_text = text_processing.extract_query_text(querySQL)
    aliasSet = text_processing.find_aliases(query_text)

    results = []
    for rule in rules:
        rule_no = rule["rule_no"]
        match rule_no:
            case 5:
                pattern = re.compile(rule["pattern_detect"], re.IGNORECASE | re.MULTILINE)
                if pattern.search(querySQL) and len(aliasSet) > 0:
                    results.append({
                        "rule_no": rule["rule_no"],
                        "detect_value": rule["detect_value"],
                        "replace_value": rule["replace_value"]
                    })
            case 7:
                if rule["detect_value"] in aliasSet:
                    results.append({
                        "rule_no":  rule["rule_no"],
                        "detect_value": rule["detect_value"],
                        "replace_value": rule["replace_value"]
                    })
            case _:
                pattern = re.compile(rule["pattern_detect"], re.IGNORECASE | re.MULTILINE)
                if pattern.search(querySQL):
                    results.append({
                        "rule_no":  rule["rule_no"],
                        "detect_value": rule["detect_value"],
                        "replace_value": rule["replace_value"]
                    })
    return results, query_text, aliasSet


def check_final_rules(code_input, unused_keys):
    data =  detect_rules (code_input, load_all_rules())
    matched_rules = data[0]
    
    st.markdown("### Check rules")
    if len(matched_rules) == 0 and  len(unused_keys) == 0:
        st.success("No rules matched")

    if unused_keys:
        st.markdown("##### Rule 1:")
        st.warning(','.join(unused_keys))

    # st.write(data[0])
    # st.write(f'final query: {data[1]}')
    # st.write(f'alias: {data[2]}')

    old_rule = None
    for rule in matched_rules:
        if old_rule != rule["rule_no"]:
            st.markdown(f"##### Rule {rule['rule_no']}:")
            old_rule = rule["rule_no"]
        st.warning(f"{rule['detect_value']} -> {rule['replace_value']}")