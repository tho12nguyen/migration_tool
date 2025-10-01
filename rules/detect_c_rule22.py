import re
# Mapping table for rule 22
code_map = {
    "-407": "23502",
    "-204": "42P01",
    "-539": "42704",
    "-601": "42P07",
    "-612": "42701",
    "-624": "42P16",
    "-803": "23505",
    "-911": "40P01",
    "SQL_REP_RECORD": "WCOM_SQLSTATE_NOT_UNUQUE",
    "WCOM_SQLCODE_NOT_UNUQUE":"WCOM_SQLSTATE_NOT_UNUQUE"
}

def find_matching_paren(s: str, open_idx: int) -> int:
    """Find matching ')' for '(' at open_idx, ignoring quoted strings and escapes."""
    depth = 0
    in_double = False
    in_single = False
    esc = False
    for i in range(open_idx, len(s)):
        c = s[i]
        if esc:
            esc = False
            continue
        if c == '\\':
            esc = True
            continue
        if in_double:
            if c == '"':
                in_double = False
            continue
        if in_single:
            if c == "'":
                in_single = False
            continue
        if c == '"':
            in_double = True
            continue
        if c == "'":
            in_single = True
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1

def split_args(arg_text: str) -> list:
    """
    Split a comma-separated argument text into tokens, ignoring commas inside quotes
    or nested parentheses. Return tokens preserving original internal spacing.
    """
    tokens = []
    buf = []
    in_double = False
    in_single = False
    esc = False
    paren_level = 0
    for ch in arg_text:
        if esc:
            buf.append(ch)
            esc = False
            continue
        if ch == '\\':
            buf.append(ch)
            esc = True
            continue
        if in_double:
            buf.append(ch)
            if ch == '"':
                in_double = False
            continue
        if in_single:
            buf.append(ch)
            if ch == "'":
                in_single = False
            continue
        if ch == '"':
            buf.append(ch)
            in_double = True
            continue
        if ch == "'":
            buf.append(ch)
            in_single = True
            continue
        if ch == '(':
            buf.append(ch)
            paren_level += 1
            continue
        if ch == ')':
            buf.append(ch)
            if paren_level > 0:
                paren_level -= 1
            continue
        if ch == ',' and paren_level == 0:
            tokens.append(''.join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        tokens.append(''.join(buf))
    return tokens

def find_format_specifiers(fmt: str) -> list:
    """
    Return list of (start_idx, conv_idx, conv_char) for each conversion specifier in order.
    Skips "%%".
    """
    conv_chars = set('diouxXfFeEgGaAcspn')
    specs = []
    i = 0
    L = len(fmt)
    while i < L:
        if fmt[i] == '%':
            # skip %%
            if i + 1 < L and fmt[i+1] == '%':
                i += 2
                continue
            j = i + 1
            # advance until conversion char found (in conv_chars)
            while j < L and fmt[j] not in conv_chars:
                j += 1
            if j < L:
                specs.append((i, j, fmt[j]))
                i = j + 1
                continue
            else:
                i += 1
        else:
            i += 1
    return specs

def replace_log_output(line: str) -> str:
    """
    Replace SQLCODE with SQLSTATE_GET() (remove (int) if present),
    replace "SQLCODE" in format string -> "SQLSTATE", and change only the
    corresponding %d (matching the SQLCODE argument position) to %s.
    """
    if "SQLCODE" not in line:
        return line

    # quick fallback simple replace if format string not present
    # we'll attempt robust approach below; fallback to safe simple replacements if any step fails

    # 1) Find first double quote - the format string
    first_quote = line.find('"')
    if first_quote == -1:
        # no format string: just replace args/cast
        line = re.sub(r'\(int\)\s*SQLCODE', 'SQLSTATE_GET()', line)
        line = re.sub(r'([\s,(]\s*)SQLCODE(\s*[,)])', r'\1SQLSTATE_GET()\2', line)
        return line

    # 2) Find '(' that starts the function call (nearest '(' before the quote)
    open_paren = line.rfind('(', 0, first_quote)
    if open_paren == -1:
        # fallback
        line = re.sub(r'\(int\)\s*SQLCODE', 'SQLSTATE_GET()', line)
        line = re.sub(r'([\s,(]\s*)SQLCODE(\s*[,)])', r'\1SQLSTATE_GET()\2', line)
        return line

    # 3) find matching closing paren robustly
    close_paren = find_matching_paren(line, open_paren)
    if close_paren == -1:
        # give up to avoid corrupting line
        return line

    # 4) extract call body and split args safely
    call_body = line[open_paren+1:close_paren]
    args = split_args(call_body)

    # 5) find index of format string argument (first double-quoted token)
    fmt_idx = None
    for idx, tok in enumerate(args):
        tok_strip = tok.strip()
        if len(tok_strip) >= 2 and tok_strip[0] == '"' and tok_strip[-1] == '"':
            fmt_idx = idx
            break
    if fmt_idx is None:
        # no quoted format found ? fallback safe replacement
        line = re.sub(r'\(int\)\s*SQLCODE', 'SQLSTATE_GET()', line)
        line = re.sub(r'([\s,(]\s*)SQLCODE(\s*[,)])', r'\1SQLSTATE_GET()\2', line)
        return line

    # 6) extract and normalize format content
    orig_fmt_token = args[fmt_idx]
    # remove outer quotes (preserve internal content as-is)
    token_strip = orig_fmt_token.strip()
    if len(token_strip) >= 2 and token_strip[0] == '"' and token_strip[-1] == '"':
        fmt_content = token_strip[1:-1]
    else:
        fmt_content = token_strip

    # 7) replace textual "SQLCODE" inside the format string -> SQLSTATE
    if "SQLCODE" in fmt_content:
        fmt_content = fmt_content.replace("SQLCODE", "SQLSTATE")

    # 8) find SQLCODE positions among args and replace tokens to SQLSTATE_GET()
    sqlcode_positions = []
    for i, tok in enumerate(args):
        # check for (int)SQLCODE or SQLCODE
        if re.search(r'\(int\)\s*SQLCODE\b', tok):
            new_tok = re.sub(r'\(int\)\s*SQLCODE\b', 'SQLSTATE_GET()', tok)
            args[i] = new_tok
            sqlcode_positions.append(i)
        elif re.search(r'\bSQLCODE\b', tok):
            new_tok = re.sub(r'\bSQLCODE\b', 'SQLSTATE_GET()', tok)
            args[i] = new_tok
            sqlcode_positions.append(i)

    # 9) if we have SQLCODE args, map them to specifiers and change only those specifiers
    if sqlcode_positions:
        specs = find_format_specifiers(fmt_content)
        # treat integer conversion chars as candidates to replace to 's'
        int_convs = set('diouxX')
        # For each sqlcode_position, compute its spec index relative to format string
        # spec_index = arg_index - (fmt_idx + 1)
        for pos in sorted(sqlcode_positions):
            spec_index = pos - (fmt_idx + 1)
            if spec_index < 0 or spec_index >= len(specs):
                # no corresponding specifier found -> skip
                continue
            start, conv_idx, conv_char = specs[spec_index]
            if conv_char in int_convs:
                # replace that conversion character with 's' (keep flags/width)
                fmt_content = fmt_content[:conv_idx] + 's' + fmt_content[conv_idx+1:]
                # note: conv_idx position stays valid because length unchanged

        # after modifications, ensure any literal "SQLCODE" texts already changed above

    # 10) rebuild the format token preserving original surrounding whitespace
    # preserve leading/trailing whitespace around the original token
    m_left = re.match(r'^(\s*)', orig_fmt_token)
    m_right = re.match(r'.*?(\s*)$', orig_fmt_token)
    left_ws = m_left.group(1) if m_left else ''
    right_ws = m_right.group(1) if m_right else ''
    args[fmt_idx] = f'{left_ws}"{fmt_content}"{right_ws}'

    # 11) rebuild call body and whole line (preserve trailing part after close_paren)
    new_call_body = call_body
    for old, new in zip(split_args(call_body), args):
        if old != new:
            new_call_body = new_call_body.replace(old, new, 1)

    new_line = line[:open_paren+1] + new_call_body + line[close_paren:]
    return new_line

def is_in_comment_or_string(line: str, pos: int) -> bool:
    """
    Check if a match is inside a comment (//) or string ("...").
    """
    comment_pos = line.find("//")
    quote_pos = line.find('"')
    return (comment_pos != -1 and pos > comment_pos) or (quote_pos != -1 and pos > quote_pos)


def replace_defines(line: str) -> str:
    """
    Case 1: Replace #define SQLCODE with SQLSTATE
    """
    def repl(m):
        prefix, name, suffix, code, comment = m.groups()
        if code in code_map:
            return f'{prefix}{name}_SQLSTATE_{suffix}   "{code_map[code]}"{comment or ""}'
        return m.group(0)

    return re.sub(r'(#define\s+)(\w+)_SQLCODE_(\w+)\s+(-?\d+)(\s*//.*)?', repl, line)


def replace_conditions(line: str) -> str:
    """
    Case 2: Replace SQLCODE checks (numeric + macro) with SQLSTATE_CHECK
    """
    # Replace numeric codes
    def repl_num(m):
        op, code = m.groups()
        if is_in_comment_or_string(line, m.start()):
            return m.group(0)
        comment_str = '"' if code.strip().isnumeric() else ''
        if code in code_map:
            if op == "==":
                return f'SQLSTATE_CHECK({comment_str}{code_map[code]}{comment_str})'
            elif op == "!=":
                return f'!SQLSTATE_CHECK({comment_str}{code_map[code]}{comment_str})'
        return m.group(0)

    line = re.sub(r'SQLCODE\s*([!=]=)\s*(-?\d+)', repl_num, line)
    line = re.sub(r'\bSQLCODE\b\s*(==|!=)\s*(SQL_REP_RECORD|WCOM_SQLCODE_NOT_UNUQUE)', repl_num, line)

    return line

def replace_log_output_old(line: str) -> str:
    """
    Replace SQLCODE with SQLSTATE_GET() in function arguments (sprintf, fprintf, etc.)
    - Remove (int) cast if directly applied to SQLCODE
    - Replace SQLCODE text inside string literals with SQLSTATE
    - Replace matching %d -> %s if SQLCODE is replaced
    """

    # 1. Remove (int) cast if it's right before SQLCODE
    line = re.sub(r'\(int\)\s*SQLCODE', 'SQLSTATE_GET()', line)

    # 2. Handle argument replacement (SQLCODE ¨ SQLSTATE_GET())
    #    Track if any replacement happened to decide whether to adjust format specifiers
    def repl_arg(m):
        return f"{m.group(1)}SQLSTATE_GET(){m.group(2)}"

    new_line, n_repl = re.subn(r'([\s,(]\s*)SQLCODE(\s*[,)])', repl_arg, line)
    line = new_line

    # 3. Replace SQLCODE text inside string literals ¨ SQLSTATE
    def repl_string_literal(match):
        inner = match.group(1).replace("SQLCODE", "SQLSTATE")
        return f'"{inner}"'

    line = re.sub(r'"([^"]*SQLCODE[^"]*)"', repl_string_literal, line)

    # 4. If we replaced SQLCODE as argument ¨ also replace one %d with %s
    if n_repl > 0:
        line = re.sub(r'%d', '%s', line, count=1)

    return line

def transform_line_for_rule22(line: str) -> str:
    """
    Apply all transformations (define + conditions).
    """
    line = replace_defines(line)
    line = replace_conditions(line)
    line = replace_log_output(line)
    return line