"""Language utilities from legacy - DRY Implementation"""
import re
from typing import Tuple, Any

# Import from config - single source of truth
from web.Exam.Daily_Exam.config.settings import LanguageConfig

# ------------------------------------------------------------------  HELPERS
LANG_EXT = LanguageConfig.EXTENSIONS

# normalize_newlines removed - use normalize_text from formatters.py instead

def language_to_ext(lang: str) -> Tuple[str, str]:
    """Convert language to (normalized_lang, extension) - optimized"""
    lang_l = lang.lower()
    if lang_l not in LANG_EXT:
        raise ValueError(f"Unsupported language '{lang}'")
    return lang_l, LANG_EXT[lang_l]