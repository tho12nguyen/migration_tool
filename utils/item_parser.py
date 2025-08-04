import re

def parse_item_list(text_area_input):
    """Parses the item list from the text area input.

    Args:
        text_area_input: The raw text input from the Streamlit text area.

    Returns:
        A tuple containing a list of items and a list of errors.
    """
    items = []
    errors = []
    raw_lines = text_area_input.strip().splitlines()
    for idx, line in enumerate(raw_lines, start=1):
        parts = re.split(r'[\t]+', line.strip())
        if len(parts) < 4:
            errors.append(f"Line {idx} is invalid: {line}")
            continue
        items.append(parts)
    return items, errors