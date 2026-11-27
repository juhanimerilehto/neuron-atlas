"""Separate rare prior effects from new uniform and low-proxy coordinate samples."""
import numpy as np
from familylab.data import numeric
from lfmfollow.core_v1 import PARENT, read, digest
from lfmfollow.design_v1 import variant, plan


def build():
    generated = set(read(PARENT / 'shared-shortlist.json'))
    validated = set(read(PARENT / 'validation-plan.json'))
    chosen = {}; rare_details = []
    for name in ('original', 'abliterated'):
        rows = []
        for file in sorted((PARENT / 'reviews/discovery').glob('*.json')):
            review = read(file)
            item = next(i for i in review['analysis']['items'] if i['component_id'].startswith(name + '__'))
            cid = item['component_id'].split('__', 1)[1]
            if cid in validated:
                continue
            for effect in item['condition_effects']:
                hits = len(effect['matching_ids'])
                clean = set(effect['matching_ids']) - set(effect['collapse_ids']) - set(effect['repetition_ids'])
                if effect['change_strength'] >= 3 and effect['coherence'] >= 2 and 1 <= hits <= 2 and clean:
                    rows.append((cid, effect, review['input_sha256']))
        rows.sort(key=lambda r: (-r[1]['change_strength'], -r[1]['coherence'], len(r[1]['matching_ids']), r[0], r[1]['condition']))
        seen = set()
        for cid, effect, review_hash in rows:
            if cid in seen:
                continue
            seen.add(cid); chosen.setdefault(cid, set()).add(effect['condition'])
            rare_details.append({'coordinate': cid, 'checkpoint': name, 'condition': effect['condition'],
                                 'label': effect['label'], 'review_input_sha256': review_hash})
            if len(seen) == 12:
                break
    sampling = []; rng = np.random.default_rng(2026112703)
    for layer in range(16):
        available = [n for n in range(4608) if f'L{layer}-N{n}' not in generated]
        random_neuron = int(rng.choice(available)); random_cid = f'L{layer}-N{random_neuron}'
        chosen[random_cid] = set()
        scores = {}
        hashes = {}
        for name in ('original', 'abliterated'):
            file = PARENT / name / f'screen-L{layer:02}.json'; rows = read(file); hashes[name] = digest(file)
            for row in rows:
                scores[row['neuron']] = max(scores.get(row['neuron'], 0.), row['early'], row['late'])
        low_neuron = min((n for n in available if n != random_neuron), key=lambda n: (scores[n], n))
        low_cid = f'L{layer}-N{low_neuron}'; chosen[low_cid] = set()
        sampling.append({'layer': layer, 'sampling_frame_n': len(available), 'uniform_coordinate': random_cid,
            'low_proxy_coordinate': low_cid, 'low_proxy_rule': 'Minimum worst early/late JS across both checkpoints, excluding the uniform draw and previously generated coordinates.',
            'parent_screen_sha256': hashes})
    variants = []
    for cid, old_settings in chosen.items():
        values = {0, -3, 3, -6, 6, -12, 12} | {numeric(s) for s in old_settings}
        variants += [variant(cid, value) for value in sorted(values)]
    value = plan('03-missed-candidates', 1, variants, 2026112703)
    value['candidate_provenance'] = {'prior_generated_coordinates': len(generated), 'prior_validated_coordinates': len(validated),
        'rare_old_effects': rare_details, 'sampling': sampling,
        'scope': 'Uniform samples are conditional on not having received parent discovery generation; one coordinate per layer. '
                 'Low-proxy draws are intentionally nonrandom. No population prevalence estimate is implied.'}
    return value
