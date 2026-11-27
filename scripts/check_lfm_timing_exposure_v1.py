"""Post hoc integrity checks on saved timing traces and pre-intervention token prefixes."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT/'campaigns/lfm-depth-20261127-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_pair(pair):
    errors = []
    cfg, info = pair['config'], pair['intervention']
    timing = cfg['timing']; positions = info.get('active_prediction_positions')
    if not isinstance(positions,list) or not all(type(p) is int for p in positions):
        return ['missing_or_invalid_positions']
    if positions != sorted(set(positions)): errors.append('positions_not_sorted_unique')
    if any(p < 0 or p >= len(pair['token_ids']) for p in positions): errors.append('position_outside_generated_sequence')
    if info.get('applied_to_generated_sequence') is not bool(positions): errors.append('exposure_flag_mismatch')
    if info.get('timing') != timing or info.get('sites') != cfg['sites']: errors.append('configuration_metadata_mismatch')
    for p in positions:
        if timing == 'all': active = True
        elif timing == 'prompt': active = p == 0
        elif timing == 'decode': active = p > 0
        elif (window := re.fullmatch(r'window_(\d+)_(\d+)',timing)):
            start,end = map(int,window.groups()); active = start <= p < end
        elif (pulse := re.fullmatch(r'pulse_(\d+)',timing)):
            active = p == int(pulse[1])
        else: active = False
        if not active: errors.append('position_outside_requested_schedule'); break
    if not positions:
        if pair['token_ids'] != pair['baseline_token_ids'] or pair['steered'] != pair['baseline']:
            errors.append('unexposed_output_differs')
    elif positions[0] > 0:
        before = positions[0]
        if pair['token_ids'][:before] != pair['baseline_token_ids'][:before]:
            errors.append('tokens_differ_before_first_recorded_intervention')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['04-timing-operators','05-neuron-pairs'])
    args = parser.parse_args(); directory = PROGRAM/'stages'/args.stage
    target = directory/'posthoc-exposure-check-v1.json'
    if target.exists():
        saved = read(target); assert saved['analysis_source_sha256'] == sha(Path(__file__))
        assert saved['passed']; print('Existing exposure integrity check retained.'); return
    assert read(directory/'status.json')['stage'] == 'measurements_complete'
    audit = read(directory/'independent-audit.json'); assert audit['passed']
    pairs = read(directory/'pairs.json')
    inputs = {f:sha(directory/f) for f in ['pairs.json','independent-audit.json','manifest.json']}
    groups = defaultdict(lambda:{'n':0,'recorded_exposure':0,'no_exposure_identical':0,'nonempty_pre_intervention_prefix_checked':0})
    failures, total = [], 0
    for name,components in pairs.items():
        for component,values in components.items():
            for pair in values:
                total += 1; cfg = pair['config']
                operators = '+'.join(sorted({s['operator'] for s in cfg['sites']}))
                key = (name,pair['stage'],pair['kind'],cfg['timing'],operators)
                group = groups[key]; group['n'] += 1
                errors = check_pair(pair)
                positions = pair['intervention'].get('active_prediction_positions',[])
                if errors:
                    failures.append({'checkpoint':name,'component':component,'id':pair['id'],'errors':errors})
                elif positions:
                    group['recorded_exposure'] += 1
                    group['nonempty_pre_intervention_prefix_checked'] += int(positions[0] > 0)
                else:
                    group['no_exposure_identical'] += 1
    assert total == audit['exact_pairs_linked_to_raw_jobs']
    result = {'stage':args.stage,'passed':not failures,'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'analysis_kind':'Post hoc execution-integrity diagnostic, not a new behavioral criterion',
        'analysis_source_sha256':sha(Path(__file__)),'input_sha256':inputs,'exact_pairs_checked':total,
        'groups':[dict(zip(['checkpoint','phase','kind','timing','operators'],key),**value) for key,value in sorted(groups.items())],
        'failures':failures,
        'clock':'Stored prediction position 0 predicts human response token 1. Decode starts at position1 (response2); window8..23 predicts response9..24; pulse16 predicts response17. Prompt prefill is represented by call0.',
        'limitations':'This checks recorded traces and exact saved-token invariance before a recorded intervention, including no-exposure cases. It does not independently measure the hidden activation amplitude, locate semantic onset, change a frozen stability verdict or replace the native manual-hook preflight. Recorded exposure on random controls follows the worker trace of the matched requested coordinate write.'}
    temporary = target.with_suffix('.json.tmp'); temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'stage':args.stage,'passed':result['passed'],'exact_pairs_checked':total,'failures':len(failures)}))
    if failures: raise RuntimeError('Saved exposure diagnostics require versioned diagnosis before publication')


if __name__ == '__main__': main()
