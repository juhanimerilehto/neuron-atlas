"""Enter the pinned native runtime without changing previous campaign entry points."""
import os
import re
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.cache/family-runtime'), str(ROOT), str(ROOT / 'worker'), str(ROOT / 'engine')]
os.environ.update(NEURON_FAMILY='lfm', HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false')
module = sys.argv[1]
assert re.fullmatch(r'[a-z][a-z0-9_]*_v[1-9][0-9]*', module)
assert (ROOT / 'lfmfollow' / (module + '.py')).is_file()
sys.argv = [module, *sys.argv[2:]]
runpy.run_module('lfmfollow.' + module, run_name='__main__')
