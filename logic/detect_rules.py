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

def get_type_mapping(data_type: str) -> str:
    type_mapping = {
        'character varying': 'CAST(? AS VARCHAR)',
        'smallint': 'CAST(? AS SMALLINT)',
        'bigint': 'CAST(? AS BIGINT)',
        'timestamp without time zone': 'CAST(? AS TIMESTAMP)',
        'text': 'CAST(? AS TEXT)',
        'double precision': 'CAST(? AS DOUBLE PRECISION)',
        'character': 'CAST(? AS VARCHAR)',
        'integer': 'CAST(? AS INTEGER)',
        'numeric': 'CAST(? AS NUMERIC)'
    }
    return type_mapping.get(data_type.lower(), data_type)

def check_final_rules(code_input, unused_keys, output_mul_mapping, output_rule2_mapping):
    data =  detect_rules (code_input, load_all_rules())
    matched_rules = data[0]
    
    st.markdown("### Check rules")
    if len(matched_rules) == 0 and \
        len(unused_keys) == 0 and \
        len(output_mul_mapping) == 0 and \
        len(output_rule2_mapping) == 0:
        st.success("No rules matched")

    if unused_keys or output_mul_mapping:
        st.markdown("##### Rule 1:")
        if unused_keys:
            st.warning(','.join(unused_keys))
        if output_mul_mapping:
            for mapping in output_mul_mapping:
                st.warning(mapping)
    if output_rule2_mapping:
        st.markdown("##### Rule 2:")
        for data_by_line in output_rule2_mapping:
            st.warning(data_by_line[0])
            for data_by_col in data_by_line[1]:
                for (table_name, data_type) in data_by_col[1]:
                    st.markdown(
                        f"**{data_by_col[0]}**: **`{data_type}`** (table: {table_name}) ---> **{get_type_mapping(data_type)}**"
                    )


    # st.write(data[0])
    # st.write(f'final query: {data[1]}')
    # st.write(f'alias: {data[2]}')

    old_rule = None
    for rule in matched_rules:
        if old_rule != rule["rule_no"]:
            st.markdown(f"##### Rule {rule['rule_no']}:")
            old_rule = rule["rule_no"]
        st.warning(f"{rule['detect_value']} -> {rule['replace_value']}")

