import hashlib
import json
from pathlib import Path
import torch
import transformers


def verify():
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / 'family-runtime-lock.json').read_text())
    assert lock['torch'] == torch.__version__ and lock['transformers'] == transformers.__version__
    runtime = Path(transformers.__file__).resolve().parent.parent
    for path, digest in lock['critical_files'].items():
        assert hashlib.sha256((runtime / path).read_bytes()).hexdigest() == digest, path
    return lock
