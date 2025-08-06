import re
from typing import List

def extract_japanese_alphanum(text: str) -> List[str]:
    return re.findall(r'[\u3040-\u30ff\u4e00-\u9fff\w:]+', text, re.UNICODE)

def remove_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    return text

def remove_system_out_print(text: str) -> str:
    # Match System.out.print / println / printf with multi-line support
    pattern = r'System\.out\.(print|println|printf)\s*\((?:[^)(]*|\([^)(]*\))*?\)\s*;'
    return re.sub(pattern, '', text, flags=re.DOTALL)


def extract_sql_info(text: str, valid_columns: set) -> List[str]:
    found = []
    text = remove_comments(text)
    text = remove_system_out_print(text)
    for line in text.splitlines():
        for word in extract_japanese_alphanum(line):
            word_upper = word.upper()
            if word_upper in valid_columns and word_upper not in found:
                found.append(word_upper)
    return found

def replace_by_mapping(query: str, mapping: dict) -> str:
    output_lines = []
    num_block_code_flag = 0
    for line in query.splitlines():
        original_line = line.strip()
        # Skip block comment lines
        if "/*" in original_line or "<!--" in original_line:
            num_block_code_flag += 1

        if "*/" in original_line or "-->" in original_line:
            num_block_code_flag -= 1

        if num_block_code_flag > 0:
            output_lines.append(line)
            continue  # skip processing lines inside block comments

        if num_block_code_flag > 0:
            if (original_line.endswith("*/") or original_line.endswith("-->")):
                num_block_code_flag -= 1
            output_lines.append(line)
            continue
        if (original_line.startswith("/*") or original_line.startswith("<!--")):
            num_block_code_flag += 1
            output_lines.append(line)
            continue
        if original_line.startswith("//"):
            output_lines.append(line)
            continue
        # Skip System.out.print-like lines
        if re.match(r'^\s*System\.out\.(print|println|printf)\s*\(', original_line):
            output_lines.append(line)
            continue

        # Split code and comment
        code_part, comment_part = re.split(r'//', line, maxsplit=1) if '//' in line else (line, '')
        raw_line = code_part
        # Replace by mapping
        for word in extract_japanese_alphanum(code_part):
            if word in mapping:
                replacements = mapping[word]
                replacement = next(iter(replacements)) if len(replacements) == 1 else str(list(replacements))
                if replacement.lower() != word.lower():
                    raw_line = re.sub(rf'\b{re.escape(word)}\b', replacement, raw_line)
        # Reattach comment
        final_line = f"{raw_line}//{comment_part}" if comment_part else raw_line
        output_lines.append(final_line)
    return "\n".join(output_lines)