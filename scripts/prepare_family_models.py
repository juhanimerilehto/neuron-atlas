"""Acquire only the pinned authorized LFM/Granite files, retaining hashes and raw provenance."""
import hashlib
import json
from pathlib import Path
import sys

from huggingface_hub import HfApi, hf_hub_download, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from familylab.specs import SPECS


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    family = sys.argv[1]
    spec = SPECS[family]
    out = ROOT / 'campaigns' / spec['campaign']
    api = HfApi()
    selection = {}
    for name, (repo, revision) in spec['models'].items():
        target = out / name / 'model.json'
        if target.exists():
            prior = json.loads(target.read_text())
            assert (prior['repository'], prior['revision']) == (repo, revision)
            selection[name] = {k: prior[k] for k in ('repository', 'revision', 'raw_config', 'files')}
            continue
        metadata = api.model_info(repo, revision=revision, files_metadata=True)
        assert metadata.sha == revision
        snapshot = Path(snapshot_download(repo, revision=revision, cache_dir=ROOT / '.cache/family-hub',
            allow_patterns=['config.json', 'tokenizer*', 'special_tokens_map.json', 'chat_template*',
                'generation_config.json', 'README.md', 'LICENSE*', 'reproduce/*']))
        config = json.loads((snapshot / 'config.json').read_text())
        assert config['model_type'] == spec['model_type'] and config['num_hidden_layers'] == spec['layers']
        if family == 'granite':
            assert set(config['layer_types']) == {'attention'} and config.get('num_local_experts', 0) == 0
        weights = [p for p in metadata.siblings if p.rfilename.endswith('.safetensors')]
        assert len(weights) == 1 and weights[0].rfilename == 'model.safetensors'
        expected = weights[0]
        print(json.dumps({'family': family, 'model': name, 'stage': 'downloading_pinned_weights',
            'revision': revision, 'bytes': expected.size}), flush=True)
        path = Path(hf_hub_download(repo, expected.rfilename, revision=revision, cache_dir=ROOT / '.cache/family-hub'))
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert path.stat().st_size == expected.size and digest == expected.lfs.sha256
        files = {p.relative_to(snapshot).as_posix(): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
                 for p in snapshot.rglob('*') if p.is_file()}
        value = {'repository': repo, 'revision': revision, 'snapshot': str(snapshot), 'weight_path': str(path),
            'config': config, 'raw_config': config, 'files': files}
        save(target, value)
        selection[name] = {k: value[k] for k in ('repository', 'revision', 'raw_config', 'files')}
        print(json.dumps({'family': family, 'model': name, 'stage': 'acquired', 'sha256': digest}), flush=True)
    target = out / 'selection.json'
    value = {'family': family, 'models': selection, 'scope': 'Pinned metadata and actual file hashes; tokenizer and tensor compatibility require preflight.'}
    if target.exists():
        assert json.loads(target.read_text()) == value
    else:
        save(target, value)


if __name__ == '__main__':
    main()
