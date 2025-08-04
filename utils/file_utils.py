

# === FILE FINDER ===
from pathlib import Path
from typing import List


def get_target_files(root_path: str) -> List[str]:
    root = Path(root_path)
    suffixes = ['_after.sql', '_after.xml', '_after.java']
    return [str(p.resolve()) for p in root.rglob('*') if p.is_file() and any(p.name.lower().endswith(suf) for suf in suffixes)]