"""Acquire the two selected revisions, checking every weight file against its pinned hash."""
import hashlib
import json
import os
from pathlib import Path
import sys

from huggingface_hub import hf_hub_download, HfApi
from huggingface_hub.errors import GatedRepoError

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from reference import write_json
from pairedllama import data

OUT = ROOT / 'campaigns' / data.CAMPAIGN


def main():
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    selected = json.loads((OUT / 'selection.json').read_text(encoding='utf-8'))
    assert selected['normalized_configs_equal'] and selected['vocabularies_equal']
    for name, info in selected['models'].items():
        path = OUT / name / 'model.json'
        if path.exists():
            print(json.dumps({'model': name, 'acquisition': 'retained'}), flush=True)
            continue
        weights = info['weights']
        assert len(weights) == 1 and weights[0]['path'] == 'model.safetensors'
        expected = weights[0]
        source, revision = info['repository'], info['revision']
        try:
            weight_path = hf_hub_download(source, expected['path'], revision=revision, cache_dir=ROOT / '.cache/pair-selection-hub')
        except GatedRepoError:
            assert name == 'original'
            source = 'unsloth/Llama-3.2-1B-Instruct'
            revision = '5a8abab4a5d6f164389b1079fb721cfab8d7126c'
            mirror = HfApi().model_info(source, revision=revision, files_metadata=True)
            candidate = next(p for p in mirror.siblings if p.rfilename == expected['path'])
            assert candidate.lfs.sha256 == expected['sha256'] and candidate.size == expected['bytes']
            weight_path = hf_hub_download(source, expected['path'], revision=revision, cache_dir=ROOT / '.cache/pair-selection-hub')
        weight_path = Path(weight_path)
        digest = hashlib.sha256()
        with weight_path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                digest.update(block)
        assert digest.hexdigest() == expected['sha256'] and weight_path.stat().st_size == expected['bytes']
        metadata = ROOT / '.cache/pair-selection-hub' / ('models--' + info['repository'].replace('/', '--')) / 'snapshots' / info['revision']
        files = dict(info['metadata_files'])
        files[expected['path']] = {'sha256': expected['sha256'], 'bytes': expected['bytes']}
        value = {'repository': info['repository'], 'revision': info['revision'], 'snapshot': str(metadata),
                 'weight_path': str(weight_path), 'weight_source_repository': source, 'weight_source_revision': revision,
                 'config': selected['normalized_runtime_config'], 'raw_config': info['raw_config'], 'files': files}
        write_json(path, value)
        print(json.dumps({'model': name, 'repository': info['repository'], 'revision': info['revision'],
                          'weight_sha256': expected['sha256'], 'bytes': expected['bytes'], 'weight_source': source}), flush=True)


if __name__ == '__main__':
    main()
