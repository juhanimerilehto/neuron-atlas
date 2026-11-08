"""Acquire a pinned, non-executable safetensors checkpoint in project-local cache."""
import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

root = Path(__file__).resolve().parents[1]
repo = 'HuggingFaceTB/SmolLM2-135M-Instruct'
info = HfApi().model_info(repo)
snapshot = snapshot_download(repo, revision=info.sha, cache_dir=str(root / '.cache' / 'hub'),
    allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', 'README.md'])
out = root / 'campaigns' / 'bracket-pilot-v1'
out.mkdir(parents=True, exist_ok=True)
manifest = {'repository': repo, 'revision': info.sha, 'snapshot': snapshot}
(out / 'model.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest), flush=True)
