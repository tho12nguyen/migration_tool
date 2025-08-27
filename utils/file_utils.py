

# === FILE FINDER ===
from pathlib import Path
from typing import List, Set

def get_target_files(root_path: str, suffixes: List[str]) -> List[str]:
    root = Path(root_path)
    return [str(p.resolve()) for p in root.rglob('*') if p.is_file() and any(p.name.lower().endswith(suf) for suf in suffixes)]


def get_files_by_suffixes(root_path: str,  suffixes: Set[str]) -> List[str]:
    suffixes = {suf.strip().lower() for suf in suffixes}
    root = Path(root_path)
    files = [str(p.resolve()) for p in root.rglob('*') if p.is_file() and p.name.lower().endswith(tuple(suffixes))]
    return files


def del_files_by_paths(file_paths: List[str]) ->  List[str]:
    errors = []
    for file_path in file_paths:
        try:
            Path(file_path).unlink()
            # os.remove(file_path)
        except Exception as e:
            errors.append(f"Error deleting file {file_path}: {e}")
    return errors
        