"""Versioned prompts for LLM extraction.

Every prompt carries a version. Any change to a prompt (even whitespace)
requires a version bump and re-running the golden F1-gate.

Files live next to this __init__ as plain text; `load(name)` reads them.
"""

from pathlib import Path

_HERE = Path(__file__).resolve().parent


def load(name: str) -> tuple[str, str]:
    """Return (version, prompt_text) for the given prompt name.

    File naming: `<group>_v<N>.md`. Latest version is the one this function
    returns — version is parsed from the filename.
    """
    candidates = sorted(_HERE.glob(f"{name}_v*.md"))
    if not candidates:
        raise FileNotFoundError(f"No prompt file found for {name!r}")
    latest = candidates[-1]
    version = latest.stem.rsplit("_v", 1)[1]
    return version, latest.read_text(encoding="utf-8")
