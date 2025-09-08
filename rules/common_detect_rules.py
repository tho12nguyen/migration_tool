import json
from typing import List
from config import RULES_ROOT_PATH, C_RULES_ROOT_PATH
from pathlib import Path
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

def get_type_mapping(data_type: str, query: str, default_value: str="") -> str:
    if '?' in query:
        type_mapping = {
            # 'character varying': 'CAST(? AS VARCHAR)',
            'smallint': 'CAST(? AS SMALLINT)',
            'bigint': 'CAST(? AS BIGINT)',
            'timestamp without time zone': 'CAST(? AS TIMESTAMP)',
            # 'text': 'CAST(? AS TEXT)',
            'double precision': 'CAST(? AS DOUBLE PRECISION)',
            # 'character': 'CAST(? AS VARCHAR)',
            'integer': 'CAST(? AS INTEGER)',
            'numeric': 'CAST(? AS NUMERIC)'
        }
        return type_mapping.get(data_type.lower(), default_value)
    return default_value

def show_result_on_ui(matched_rules: List[dict], unused_keys: List[str]=[], output_mul_mapping: List=[], output_rule2_mapping: List=[]) -> None:
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
            item_html = f"""<div style="padding:6px; margin:4px 0; border-radius:6px;background:#f8f9fa; border-left:4px solid #EAB308;">
                    <span style="color:#EAB308; font-weight:bold;">Line {line_index + 1}:</span>
                    <code style="color:#d6336c;">{data_line.strip()}</code>
            """
            for data_by_col in data_by_line[1]:
                for (table_name, data_type) in data_by_col[1]:
                    suggesstion = get_type_mapping(data_type, data_line, default_value="")
                    if suggesstion:
                        suggesstion = f" | <b>{suggesstion}</b>"
                    item_html += f"""<div style="padding-left:20px; margin:2px 5px;">
                        <b>{data_by_col[0]}</b> -> <code>{data_type}</code>  
                            (table: {table_name}) {suggesstion}
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