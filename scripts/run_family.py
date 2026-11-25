"""Enter the isolated pinned runtime without changing the historical Python environment."""
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
runtime = ROOT / '.cache/family-runtime'
assert runtime.is_dir(), 'Install requirements-family-lock.txt into .cache/family-runtime first'
sys.path[:0] = [str(runtime), str(ROOT), str(ROOT / 'worker')]
os.environ['NEURON_FAMILY'] = sys.argv[1]
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
module = sys.argv[2]
assert module in ('compare_weights', 'preflight', 'campaign', 'report', 'audit', 'tests', 'reviewer_preflight', 'freeze')
sys.argv = [module, *sys.argv[3:]]
runpy.run_module('familylab.' + module, run_name='__main__')
