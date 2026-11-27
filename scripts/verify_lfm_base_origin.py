"""Verify the creator's original weight revision against this campaign, without downloading weights."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
PARENT = ROOT / 'campaigns/paired-lfm25-350m-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = PROGRAM / 'posthoc-base-origin-v1.json'
    if target.exists():
        print(json.dumps(read(target))); return
    edited = read(PARENT / 'abliterated/model.json')
    config = Path(edited['snapshot']) / 'reproduce/config.toml'
    settings = tomllib.loads(config.read_text(encoding='utf-8'))
    repository, origin = settings['model'], settings['model_commit']
    assert repository == 'LiquidAI/LFM2.5-350M' and len(origin) == 40 and all(c in '0123456789abcdef' for c in origin)
    url = 'https://huggingface.co/api/models/' + urllib.parse.quote(repository,safe='/') + '/revision/' + origin + '?blobs=true'
    request = urllib.request.Request(url,headers={'User-Agent':'NeuronAtlasResearch/1.0'})
    with urllib.request.urlopen(request,timeout=30) as response:
        assert response.status == 200
        raw = response.read()
    api = json.loads(raw)
    assert api['sha'] == origin
    weight = next(item for item in api['siblings'] if item['rfilename']=='model.safetensors')['lfs']
    original = read(PROGRAM / 'stages/01-confirm-p9/manifest.json')['models']['original']
    expected = original['files']['model.safetensors']['sha256']
    result = {'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'repository':repository,'creator_base_revision':origin,'campaign_base_revision':original['revision'],
        'campaign_weight_sha256':expected,'creator_revision_weight_sha256':weight['sha256'],
        'identical_weight_file':weight['sha256']==expected,'upstream_weight_bytes':weight['size'],
        'metadata_url':url,'metadata_response_sha256':hashlib.sha256(raw).hexdigest(),
        'creator_config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),
        'scope':'Public model metadata only. No checkpoint download, model revision change or intervention job.'}
    archive = PROGRAM / 'diagnostics/upstream-base-origin-response.json'
    archive.write_bytes(raw)
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps(result))


if __name__ == '__main__': main()
