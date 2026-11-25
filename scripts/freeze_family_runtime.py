"""Record isolated library versions and critical architecture implementation hashes."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
runtime = ROOT / '.cache/family-runtime'
sys.path.insert(0, str(runtime))
import torch
import transformers
packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions(path=[str(runtime)])}
paths = ['transformers/models/lfm2/modeling_lfm2.py', 'transformers/models/lfm2/configuration_lfm2.py',
    'transformers/models/granitemoehybrid/modeling_granitemoehybrid.py',
    'transformers/models/granitemoehybrid/configuration_granitemoehybrid.py',
    'transformers/generation/utils.py', 'transformers/cache_utils.py', 'transformers/masking_utils.py']
value = {'python': sys.version.split()[0], 'torch': torch.__version__, 'transformers': transformers.__version__,
    'packages': packages, 'critical_files': {p: hashlib.sha256((runtime / p).read_bytes()).hexdigest() for p in paths}}
target = ROOT / 'family-runtime-lock.json'
if target.exists():
    assert json.loads(target.read_text()) == value
else:
    target.write_text(json.dumps(value, indent=2) + '\n')
(ROOT / 'requirements-family-lock.txt').write_text('\n'.join(f'{k}=={v}' for k, v in sorted(packages.items())) + '\n')
print(json.dumps({'torch': value['torch'], 'transformers': value['transformers'], 'isolated_packages': len(packages)}))
