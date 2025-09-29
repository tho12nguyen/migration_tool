import difflib

from utils import file_utils


def merge_source_file(original_path: str, change_path: str, dest_path: str, encoding='shift_jis') -> str:
    """Merges changes from a change file into a destination file based on an original file
    Args:
        original_path (str): Path to the original file.
        change_path (str): Path to the file with changes.
        dest_path (str): Path to the destination file where changes will be applied
    """
    # Step 1: Load files
    with open(original_path, 'r', encoding=encoding, newline="") as f:
        original_lines = f.readlines()

    with open(change_path, 'r', encoding=encoding, newline="") as f:
        changed_lines = f.readlines()
    with open(dest_path, 'r', encoding=encoding, newline="") as f:
        dest_lines = f.readlines()
    
    original_eol_format = file_utils.detect_eol_str_by_content(''.join(original_lines))
    dest_eol_format = file_utils.detect_eol_str_by_content(''.join(dest_lines))
    if original_eol_format != dest_eol_format:
        raise ValueError(f"Original and destination files must have same EOL format.  EOL SOURCE: {original_eol_format}, EOL DEST: {dest_eol_format}")
    if (len(original_lines) != len(dest_lines)):
        raise ValueError("Original and destination files must have the same number of lines")

    # Step 2: Diff original vs changed
    diff = list(difflib.ndiff(original_lines, changed_lines))
    changed_line_indices = []
    new_lines_map = {}
    orig_line_num = 0
    changed_line_num = 0
    for line in diff:
        code = line[:2]
        content = line[2:]

        if code == '  ':
            orig_line_num += 1
            changed_line_num += 1
        elif code == '- ':
            orig_line_num += 1
        elif code == '+ ':
            changed_line_indices.append(changed_line_num)
            new_lines_map[changed_line_num] = content
            changed_line_num += 1
        elif code == '? ':
            # This line is a hint for a change, we can ignore it
            continue
        else:
            raise ValueError(f"Unexpected diff code: {code}")
    # Step 3: Check if dest matches original exactly
    for idx in changed_line_indices:
        if original_lines[idx] != dest_lines[idx] and changed_lines[idx] != dest_lines[idx]:
            raise ValueError(f"Line {idx+1} mismatch between original and destination:\n"
                             f"Original: {original_lines[idx]!r}\n"
                             f"Dest    : {dest_lines[idx]!r}")

    # Step 4: Apply to dest
    result = ''
    for idx in changed_line_indices:
        result = result + f'Line {idx + 1}: {new_lines_map[idx]}'
        if idx < len(dest_lines):
            dest_lines[idx] = new_lines_map[idx]
        else:
            # append line if it's beyond the end
            dest_lines.append(new_lines_map[idx])
    # Step 5: Save result
    with open(dest_path, 'w', encoding=encoding, newline="") as f:
        f.writelines(dest_lines)
    
    return result