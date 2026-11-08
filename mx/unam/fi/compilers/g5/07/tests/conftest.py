import sys
from pathlib import Path

# Make `src/main` importable as `lexer` without installing the package.
SRC_MAIN = Path(__file__).resolve().parents[1] / "src" / "main"
if str(SRC_MAIN) not in sys.path:
    sys.path.insert(0, str(SRC_MAIN))
