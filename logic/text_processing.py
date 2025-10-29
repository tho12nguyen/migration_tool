import re
from typing import List, Tuple

def extract_japanese_alphanum(text: str) -> List[str]:
    return re.findall(r'[\u3040-\u30ff\u4e00-\u9fff\w:]+', text, re.UNICODE)


def remove_comments(text: str) -> str:
    # Remove all block comments: /*...*/, /***...***/, <!--...-->
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)       # Handles /* ... */
    text = re.sub(r'/\*\*\*.*?\*\*\*/', '', text, flags=re.DOTALL) # Handles /*** ... ***/
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)      # Handles <!-- ... -->

    # Remove single-line comments starting with //
    text = re.sub(r'//.*', '', text)

    # Normalize whitespace and preserve line breaks
    output_lines = []
    for line in text.splitlines():
        if line.strip():  # Skip empty lines
            output_lines.append(line)
    return '\n'.join(output_lines)


def remove_system_out_print(text: str) -> str:
    # Match System.out.print / println / printf with multi-line support
    pattern = r'System\.out\.(print|println|printf)\s*\((?:[^)(]*|\([^)(]*\))*?\)\s*;'
    return re.sub(pattern, '', text, flags=re.DOTALL)

def has_sql_condition(sql_line: str) -> bool:
    """
    Detect if a SQL line contains common condition operators.
    Covers comparison, range, null checks, pattern matching, set membership.
    """
    condition_patterns = [
        r"\s*=\s*",          # equals
        r"\s*!=\s*",         # not equal (ANSI)
        r"<>",               # not equal (SQL standard)
        r"\s*>=\s*",         # greater or equal
        r"\s*<=\s*",         # less or equal
        r"\s*>\s*",          # greater
        r"\s*<\s*",          # less
        r"\bIN\b",           # IN (...)
        r"\bNOT\s+IN\b",     # NOT IN (...)
        r"\bLIKE\b",         # LIKE
        r"\bNOT\s+LIKE\b",   # NOT LIKE
        r"\bBETWEEN\b",      # BETWEEN
        r"\bIS\s+NULL\b",    # IS NULL
        r"\bIS\s+NOT\s+NULL\b",  # IS NOT NULL
        r"\bEXISTS\b",       # EXISTS
        r"\bANY\b",          # = ANY(...)
        r"\bALL\b",          # = ALL(...)
        r"\bCASE\b",         # CASE ... WHEN ... THEN ... END
        r"\bWHEN\b"          # CASE A.COLUMN WHEN THEN ... END
    ]

    pattern = "|".join(condition_patterns)
    return re.search(pattern, sql_line, re.IGNORECASE) is not None

def extract_full_keys(text: str, valid_columns: set, encoding: str) -> Tuple[List[str], List[str]]:
    used_keys = []
    unused_keys = []
    text = remove_comments(text)
    text = remove_system_out_print(text)
    for line in text.splitlines():
        for word in extract_japanese_alphanum(line):
            word_upper = word.upper()
            if word_upper in valid_columns:
                if  word_upper not in used_keys:
                    used_keys.append(word_upper)
            else:
                if len(word_upper.encode("utf-8")) != len(word_upper.encode(encoding)) and word_upper not in unused_keys:
                    unused_keys.append(word_upper)
    return (used_keys, unused_keys)

def replace_by_mapping(lines: List[str],  line_indexes: List[int], mapping: dict, new_col_name_to_table_and_data_type_dict: dict[str, Tuple], column_set: set) -> Tuple[List[str], List[str]]:
    output_lines = []
    output_mul_mapping = []
    output_rule2_mapping = []

    num_block_code_flag = 0
    pre_word = ''
    insert_flag = False
    for idx, line in enumerate(lines):
        table_and_data_types = []
        col_data_type_set = set()
        original_line = line.strip()
        # Skip block comment lines
        if (original_line.startswith("/*") or original_line.startswith("<!--")):
            num_block_code_flag += 1

        if num_block_code_flag > 0:
            if (original_line.endswith("*/") or original_line.endswith("-->")):
                num_block_code_flag -= 1
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
        if '//' in line:
            code_part, comment_part = re.split(r'//', line, maxsplit=1)
            comment_part = '//' + comment_part  # keep the //
        # Then check for /* ... */ comments
        elif '/*' in line and '*/' in line:
            code_part, comment_part = re.split(r'/\*', line, maxsplit=1)
            comment_part = '/*' + comment_part  # keep the opening /*
        else:
            code_part, comment_part = line, ''
        raw_line = code_part
        # Replace by mapping
        for word in extract_japanese_alphanum(code_part):
            if pre_word == 'INSERT' and word.upper() == 'INTO':
                insert_flag = True
            
            if pre_word  != "INSERT" and word.upper() == "INSERT":
                pre_word = word.upper()
            
            if word.upper() in mapping:
                replacements = mapping[word.upper()]
                if len(replacements) > 0:
                    new_word = list(replacements)[0]
                    if new_word in new_col_name_to_table_and_data_type_dict:
                        if new_word not in col_data_type_set:
                            table_and_data_types.append((new_word, new_col_name_to_table_and_data_type_dict[new_word]))
                            col_data_type_set.add(new_word)
                    else:
                        # Not found in dictionary, mark as Not Found
                        if new_word not in col_data_type_set and new_word in column_set:
                            table_and_data_types.append((new_word,[ ("", "Not Found")]))
                            col_data_type_set.add(new_word)
                if len(replacements) > 1:
                    output_mul_mapping.append(f'{word} -> {list(replacements)}')
                replacement = next(iter(replacements)) if len(replacements) == 1 else "\n".join(replacements)
                if replacement.lower() != word.lower():
                    raw_line = re.sub(rf'\b{re.escape(word)}\b', replacement, raw_line, flags=re.IGNORECASE)
            
            if insert_flag and word.upper() == 'VALUES':
                insert_flag = False
        # Reattach comment
        final_line = f"{raw_line}{comment_part}" if comment_part else raw_line
        if len(table_and_data_types) > 0 and (insert_flag or has_sql_condition(raw_line)):
            output_rule2_mapping.append(((line_indexes[idx], final_line), table_and_data_types))
        output_lines.append(final_line)
    return output_lines, output_mul_mapping, output_rule2_mapping

def extract_sql_fragments(text: str) -> str:
    """
    Extract SQL-like fragments from mixed XML/Java/SQL files.
    """
    text = remove_comments(text)
    text = remove_system_out_print(text)
    return text

def extract_query_text(raw_sql: str) -> str:
    """
    Extracts SQL text from:
    - Plain SQL
    - MyBatis XML <insert>, <update>, <select>
    - Java .append("...") style (with concatenations)
    - Inline string concatenations
    - Full string assignments
    """
    text = raw_sql

    # 1. MyBatis XML inner SQL
    if re.search(r"<(insert|update|delete|select)", text, re.IGNORECASE):
        inner = re.findall(r">(.*)<", text, re.DOTALL)
        if inner:
            text = "\n".join(inner)

    # 2. Java .append(...) (captures multiple string parts, even with +)
    java_parts = re.findall(r'\.append\(\s*(".*?")\s*\)', text, re.DOTALL)
    if java_parts:
        joined = []
        for part in java_parts:
            # extract quoted substrings from inside append (may have + concatenations)
            strings = re.findall(r'"([^"]*)"', part)
            joined.extend(strings)
        text = " ".join(joined)

    # 3. Inline concatenated strings like "..." + "..."
    concat_parts = re.findall(r'"([^"]*)"\s*\+', text)
    if concat_parts:
        text = " ".join(concat_parts)

    # 4. String assignment like: String sql = "....";
    assign_match = re.findall(r'=\s*"([^"]*)"', text)
    if assign_match:
        text = " ".join(assign_match)

    # 5. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def find_aliases(sql: str):
    """
    Detect table and column aliases in SQL.
    - Table aliases: FROM / JOIN <table> [AS] <alias>
    - Column aliases: expr AS alias OR expr alias
    """
    tables = set()
    table_aliases = set()
    column_aliases = set()

    sql_clean = " ".join(sql.split())

    # Identifier regex: words + Japanese full-width characters
    IDENT = r'[\w\u4E00-\u9FA5\u3040-\u309F\u30A0-\u30FF\uFF10-\uFF5A]+'

    # --- Table names with optional alias ---
    table_pattern = re.compile(
        rf'\b(?:FROM|JOIN)\s+((?:"[^"]+"|{IDENT})(?:\.(?:"[^"]+"|{IDENT}))*)'
        rf'(?:\s+(?:AS\s+)?({IDENT}))?(?=\s|,|$)',
        re.IGNORECASE
    )
    for match in table_pattern.finditer(sql_clean):
        tables.add(match.group(1))
        if match.group(2):
            table_aliases.add(match.group(2))

    # --- Column aliases with AS ---
    col_as_pattern = re.compile(
        rf'(?:\w+\s*\([^\)]*\)|{IDENT})\s+AS\s+({IDENT})(?=,|\s+FROM|\s+WHERE|\s+GROUP|\s+ORDER|\s*$)',
        re.IGNORECASE
    )
    for match in col_as_pattern.finditer(sql_clean):
        column_aliases.add(match.group(1))

    # --- Column aliases without AS ---
    col_no_as_pattern = re.compile(
        rf'(?:\w+\s*\([^\)]*\)|{IDENT})\s+({IDENT})(?=,|\s+FROM|\s+WHERE|\s+GROUP|\s+ORDER|\s*$)',
        re.IGNORECASE
    )
    for match in col_no_as_pattern.finditer(sql_clean):
        name = match.group(1)
        if name not in tables and name not in table_aliases:
            column_aliases.add(name)

    result = table_aliases | column_aliases

    return sorted(result)