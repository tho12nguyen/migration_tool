
from charset_normalizer import from_bytes

common_encodings = [
        'cp932',            # Windows Japanese (Shift_JIS variant, most common on Windows)
        'shift-jis',        # Standard Shift_JIS (ISO form)
        'euc-jp',           # EUC-JP (Unix/Linux Japanese files)
        'shift_jisx0213',   # Extended Shift_JIS (rare/modern Kanji)

        'iso2022_jp',       # JIS encoding (used in emails, older systems)
        'iso2022_jp_1',     # Variant of ISO-2022-JP
        'iso2022_jp_2',     # Supports extended characters
        'iso2022_jp_3',     # Rare, Japanese emails
        'iso2022_jp_ext',   # Extension for ISO-2022-JP

        'utf-8',            # Modern Unicode (safe, recommended)
        'utf-8-sig',        # UTF-8 with BOM (Excel, Notepad)
        'utf-16',           # Unicode 16-bit
        'utf-32',           # Unicode 32-bit

        'ascii'             # Only if plain English text
    ]

ENCODING_ALIASES = {
    'euc_jis_2004': 'euc-jp',
    'euc_jisx0213': 'euc-jp',
    'shift_jisx0213': 'shift_jisx0213',
    'ms932': 'cp932',
    'cp932': 'cp932',
    'shift_jis': 'shift-jis',
    'sjis': 'shift-jis',
    'utf_8': 'utf-8',
    'utf_8_sig': 'utf-8-sig',
    'utf_16': 'utf-16',
    'utf_32': 'utf-32',
    'us_ascii': 'ascii',
    'ascii': 'ascii'
}

def normalize_encoding(enc: str) -> str:
    """Normalize encoding names to match common_encodings list."""
    if not enc:
        return "utf-8"
    return ENCODING_ALIASES.get(enc.lower(), enc.lower())

def detect_encode_use_lib(content_bytes: bytes) -> str:
    """
    Detect file encoding from bytes using charset_normalizer.
    Prioritize encodings in common_encodings list.
    """
    results = from_bytes(content_bytes)

    if not results:
        return "utf-8"  # fallback if nothing detected

    # Sort by best match (higher coherence = better)
    results = sorted(results, key=lambda r: r.fingerprint or 0, reverse=True)

    # Try to return the first match from common_encodings
    for r in results:
        enc = normalize_encoding(r.encoding)
        if enc in [c.lower() for c in common_encodings]:
            return enc

    # If no common encoding match, return best guess
    return normalize_encoding(results[0].encoding)

def detect_encode(content_bytes: bytes) -> str:
    encoding = None
    # Try common encodings first
    for enc in common_encodings:
        try:
            _ = content_bytes.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            pass

    return encoding