"""Versioned correction of the zero-mixed-quota nomination defect, using validation only."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'campaigns/paired-qwen06-late-v1'


def read(path):
    return path.read_text(encoding='utf-8')


def build_audit():
    manifest = json.loads(read(OUT / 'manifest.json'))
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
               for path, digest in manifest['sources'].items())
    assert 'union of 6 strongest readable' in manifest['selection']
    plan = json.loads(read(OUT / 'validation-plan.json'))
    frozen = json.loads(read(OUT / 'frozen-finalists.json'))
    hashes = {}
    nominations = {}
    primary = {}
    for name in ('original', 'abliterated'):
        pairs = json.loads(read(OUT / name / 'validation.json'))
        rows = []
        for cid in plan:
            path = OUT / 'reviews/validation' / (cid + '.json')
            hashes[str(path.relative_to(OUT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
            review = json.loads(read(path))
            item = next(i for i in review['analysis']['items'] if i['component_id'] == name + '__' + cid)
            for effect in item['condition_effects']:
                if effect['coherence'] < 3:
                    continue
                sample = {p['id'] for p in pairs[cid] if p['condition'] == effect['condition'] and p['kind'] == 'neuron'}
                fraction = len(set(effect['matching_ids']) & sample) / max(1, len(sample))
                rows.append((cid, effect, fraction))
        rows.sort(key=lambda r: (-r[1]['change_strength'], -r[2], -r[1]['coherence'], r[0], r[1]['condition']))
        used = set()
        layers = {}
        nominations[name] = {}
        for cid, effect, _ in rows:
            layer = cid.split('-')[0]
            if cid in used or layers.get(layer, 0) >= 3:
                continue
            assert effect['condition'] in frozen[cid]
            nominations[name][cid] = effect['condition']
            primary.setdefault(cid, set()).add(effect['condition'])
            used.add(cid)
            layers[layer] = layers.get(layer, 0) + 1
            if len(used) == 6:
                break
    primary = {cid: sorted(doses) for cid, doses in sorted(primary.items())}
    assert len(primary) <= 12
    extra = {cid: sorted(set(doses) - set(primary.get(cid, []))) for cid, doses in frozen.items()
             if set(doses) - set(primary.get(cid, []))}
    return {'version': 'paired06-selection-correction.v1', 'passed': True,
            'detected_during': 'Held-out generation, before final reviewer assessment',
            'deviation': 'The frozen worker iterated the mixed group even when its quota was zero. '
                         'Extra mixed/collapsed settings advanced to testing. Raw evidence and frozen worker remain unchanged.',
            'correction': 'Reconstruct exactly six readable nominations per checkpoint, with the original sort and layer cap, '
                          'using only the saved validation reviews and validation pairs. Their union is the primary set. '
                          'Other tested settings are exploratory and cannot receive a primary extreme-mode pass. '
                          'Detection occurred during held-out generation; no held-out text or score enters this reconstruction.',
            'validation_review_sha256': hashes,
            'frozen_finalists_sha256': hashlib.sha256((OUT / 'frozen-finalists.json').read_bytes()).hexdigest(),
            'per_checkpoint_nominations': nominations, 'primary_settings': primary, 'exploratory_settings': extra,
            'actual_tested_coordinates': len(frozen), 'primary_coordinates': len(primary)}


def main():
    result = build_audit()
    path = OUT / 'selection-audit-v1.json'
    if path.exists():
        assert json.loads(read(path)) == result, 'Selection correction changed; retain the old audit and version the recovery'
    else:
        path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('version', 'passed', 'actual_tested_coordinates', 'primary_coordinates')}), flush=True)


if __name__ == '__main__':
    main()
