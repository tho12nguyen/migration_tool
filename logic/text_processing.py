import re
from typing import List

def extract_japanese_alphanum(text: str) -> List[str]:
    return re.findall(r'[\u3040-\u30ff\u4e00-\u9fff\w:]+', text, re.UNICODE)

def remove_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    return text

def extract_sql_info(text: str, valid_columns: set) -> List[str]:
    found = []
    text = remove_comments(text)
    for line in text.splitlines():
        for word in extract_japanese_alphanum(line):
            if word in valid_columns and word not in found:
                found.append(word)
    return found

def replace_by_mapping(query: str, mapping: dict) -> str:
    output_lines = []
    for line in query.splitlines():
        original_line = line.strip()
        if original_line.startswith("//") or original_line.startswith("/*") or original_line.startswith("<!--"):
            output_lines.append(line)
            continue
        code_part, comment_part = re.split(r'//', line, maxsplit=1) if '//' in line else (line, '')
        raw_line = code_part
        for word in extract_japanese_alphanum(code_part):
            if word in mapping:
                replacements = mapping[word]
                replacement = next(iter(replacements)) if len(replacements) == 1 else str(list(replacements))
                if replacement.lower() != word.lower():
                    raw_line = re.sub(rf'\b{re.escape(word)}\b', replacement, raw_line)
        final_line = f"{raw_line}//{comment_part}" if comment_part else raw_line
        output_lines.append(final_line)
    return "\n".join(output_lines)