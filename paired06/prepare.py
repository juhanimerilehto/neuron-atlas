"""Acquire the two explicitly selected checkpoints into the project cache."""
import hashlib
import json
import os
from pathlib import Path
import sys

from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'worker'))
from reference import write_json

CAMPAIGN = 'paired-qwen06-late-v1'
MODELS = {
    'original': 'Qwen/Qwen3-0.6B',
    'abliterated': 'huihui-ai/Huihui-Qwen3-0.6B-abliterated-v2',
}


def main():
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    out = ROOT / 'campaigns' / CAMPAIGN
    for name, repository in MODELS.items():
        path = out / name / 'model.json'
        previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        info = HfApi().model_info(repository, revision=previous['revision'] if previous else 'main')
        location = snapshot_download(repository, revision=info.sha, cache_dir=ROOT / '.cache' / 'paired06-hub',
                                     allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', 'README.md'])
        snapshot = Path(location)
        files = {}
        for source in sorted(snapshot.iterdir()):
            if not source.is_file():
                continue
            digest = hashlib.sha256()
            with source.open('rb') as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                    digest.update(block)
            files[source.name] = {'sha256': digest.hexdigest(), 'bytes': source.stat().st_size}
        config = json.loads((snapshot / 'config.json').read_text(encoding='utf-8'))
        value = {'repository': repository, 'revision': info.sha, 'snapshot': str(snapshot),
                 'config': config, 'files': files}
        if previous:
            assert value == previous, 'Pinned acquisition identity changed'
        else:
            write_json(path, value)
        print(json.dumps({'model': name, 'repository': repository, 'revision': info.sha,
                          'layers': config['num_hidden_layers'], 'mlp_width': config['intermediate_size'],
                          'bytes': sum(v['bytes'] for v in files.values())}), flush=True)


if __name__ == '__main__':
    main()
