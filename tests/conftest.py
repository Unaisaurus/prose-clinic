import os
import sys
import tempfile
from pathlib import Path

# Never touch the real user_data folder while testing.
os.environ.setdefault("PROSE_CLINIC_DATA_DIR", tempfile.mkdtemp(prefix="prose-clinic-tests-"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SAMPLES = Path(__file__).resolve().parent / "samples"


def sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")
