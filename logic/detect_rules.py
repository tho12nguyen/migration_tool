import json
import re
from typing import List, Tuple
from config import RULES_ROOT_PATH, C_RULES_ROOT_PATH
from pathlib import Path
from logic import text_processing
import streamlit as st

@st.cache_data()
def load_all_rules(source_type: str):
    rules = []
    if source_type.lower() == 'c':
        rules_path = Path(C_RULES_ROOT_PATH)
    elif source_type.lower() == 'java':
        rules_path = Path(RULES_ROOT_PATH)
    else:
        raise ValueError(f"value source_type: {source_type}, source_type must be either 'java' or 'c'")

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

def detect_rules(lines: List[str], rules, active_rule_set: set):
    raw_query = ''.join(lines)
    querySQL = text_processing.extract_sql_fragments(raw_query)
    query_text = text_processing.extract_query_text(querySQL)
    aliasSet = text_processing.find_aliases(query_text)

    results = []
    for rule in rules:
        rule_no = rule["rule_no"]

        # Skip rule_no not in the list
        if active_rule_set and rule_no not in active_rule_set:
            continue

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

def check_final_rules(lines: List[str], unused_keys, output_mul_mapping, output_rule2_mapping, source_type: str, active_rule_set: set):
    data =  detect_rules (lines, load_all_rules(source_type), active_rule_set)
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
            (line_index, data_line) = data_by_line[0]
            # st.warning(f"Line {line_index + 1}: {data_line}")
            # for data_by_col in data_by_line[1]:
            #     for (table_name, data_type) in data_by_col[1]:
            #         st.markdown(
            #             f"**{data_by_col[0]}**: **`{data_type}`** (table: {table_name})  |  **{get_type_mapping(data_type)}**"
            #         )

            item_html = f"""<div style="padding:6px; margin:4px 0; border-radius:6px;background:#f8f9fa; border-left:4px solid #EAB308;">
                    <span style="color:#EAB308; font-weight:bold;">Line {line_index + 1}:</span>
                    <code style="color:#d6336c;">{data_line.strip()}</code>
            """
            for data_by_col in data_by_line[1]:
                for (table_name, data_type) in data_by_col[1]:
                    item_html += f"""<div style="padding-left:20px; margin:2px 5px;">
                        <b>{data_by_col[0]}</b> -> <code>{data_type}</code>  
                            (table: {table_name}) | <b>{get_type_mapping(data_type)}</b>
                        </div>
                        """
            item_html += "</div>"
            st.markdown(item_html, unsafe_allow_html=True)

    old_rule = None
    for rule in matched_rules:
        if old_rule != rule["rule_no"]:
            st.markdown(f"##### Rule {rule['rule_no']}:")
            old_rule = rule["rule_no"]
        st.warning(f"{rule['detect_value']} -> {rule['replace_value']}")

def detect_and_apply_rules(query: str, rules: List[dict], active_rule_set: set) -> Tuple[str, List[dict]]:
    """
    Apply regex-based replacement rules to the input query.
    """
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