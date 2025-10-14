from config import WINMERGE_PATH
import subprocess

def run_winmerge(left, right, report):
    """Run WinMerge to generate an HTML report for one file pair."""
    if WINMERGE_PATH:
        subprocess.run([
            WINMERGE_PATH,
            left,
            right,
            "/noninteractive",
            "/u",
            "/or", report
        ], check=True)
