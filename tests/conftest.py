"""The package lives in src/ (hatch layout) and is not installed into the shared
Datacore venv, so `from datacortex...` failed at collection when the tests ran
from the module folder. Put src/ on the path, as an installed package would."""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
