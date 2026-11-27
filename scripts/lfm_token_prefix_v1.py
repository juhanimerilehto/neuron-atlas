"""Post hoc continuation-onset summaries from saved tokens; no inference or new judgments."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prefix_length(first, second):
    for index,(a,b) in enumerate(zip(first,second)):
        if a != b: return index
    return min(len(first),len(second))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=read(PROGRAM/'programme.json')['finite_stages'])
    args = parser.parse_args()
    directory = PROGRAM/'stages'/args.stage
    target = directory/'posthoc-token-prefix-v1.json'
    if target.exists():
        assert read(target)['analysis_source_sha256'] == sha(Path(__file__))
        print('Existing saved-token onset analysis retained.'); return
    assert read(directory/'status.json')['stage'] == 'measurements_complete'
    assert read(directory/'independent-audit.json')['passed']
    cases, outcomes = read(directory/'pairs.json'), read(directory/'outcomes.json')
    inputs = {name:sha(directory/name) for name in ('pairs.json','outcomes.json','independent-audit.json')}
    effects = {}
    for who, name in [('Terra','locked_test.json'),('Sol','sol-locked_test.json')]:
        if args.stage == '01-confirm-p9':
            path = directory/('reviews' if who=='Terra' else 'confirmations')/'locked_test/L2-N3420.json'
            value = read(path)
            effects[who] = {checkpoint:{'L2-N3420':{'p9':next(i for i in value['analysis']['items'] if i['component_id']==alias+'__L2-N3420')['condition_effects'][0]}}
                for checkpoint,alias in [('original','A'),('abliterated','B')]}
        else:
            path = directory/'analyses'/name
            value = read(path)
            effects[who] = {checkpoint:{component:{condition:item['effect'] for condition,item in conditions.items()}
                for component,conditions in components.items()} for checkpoint,components in value.items()}
        inputs[path.relative_to(directory).as_posix()] = sha(path)
    profiles = []
    for row in outcomes['condition_gates']:
        name,component,condition = row['checkpoint'],row['coordinate'],row['condition']
        selected = [p for p in cases[name][component] if p['condition']==condition and p['kind']=='neuron' and p['stage'] in ('locked_test','long','replication')]
        assert len(selected)==32
        ratings = [effects[who][name].get(component,{}).get(condition) for who in ('Terra','Sol')]
        common = set.intersection(*(set(e['matching_ids']) for e in ratings)) if all(ratings) else set()
        bad = set().union(*(set(e[field]) for e in ratings if e for field in ('baseline_defect_ids','repetition_ids','collapse_ids')))
        records = []
        for pair in selected:
            tokens,baseline = pair['token_ids'],pair['baseline_token_ids']
            n = prefix_length(tokens,baseline)
            char_n = prefix_length(pair['steered'],pair['baseline'])
            records.append({'id':pair['id'],'prompt':pair['prompt'],'phase':pair['stage'],
                'identical_first_stored_token':bool(tokens and baseline and tokens[0]==baseline[0]),
                'common_generated_token_prefix_length':n,'shared_text_prefix':pair['baseline'][:min(160,char_n)],
                'jointly_matched':pair['id'] in common,'jointly_matched_without_baseline_or_quality_flags':pair['id'] in common-bad})
        matched = [r for r in records if r['jointly_matched']]
        profiles.append({'checkpoint':name,'component':component,'condition':condition,'n':len(records),
            'review_complete':all(ratings),'same_first_token':sum(r['identical_first_stored_token'] for r in records),
            'jointly_matched_n':len(matched),'joint_match_same_first_token':sum(r['identical_first_stored_token'] for r in matched),
            'joint_match_prefix_at_least':{str(k):sum(r['common_generated_token_prefix_length']>=k for r in matched) for k in (1,4,8,16,32)},
            'cases':records})
    result = {'analysis_kind':'Post hoc token-prefix comparison, without new inference or a new screen.', 'stage':args.stage,
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'analysis_source_sha256':sha(Path(__file__)),
        'input_sha256':inputs, 'profiles':profiles,
        'interpretation':'An unchanged greedy first token is compatible with a later behavioral change. It does not imply unchanged first-token probabilities or zero Jensen-Shannon divergence, and these data do not estimate the miss rate of the numerical screen. Common token prefixes are exact saved-token comparisons; shared text prefixes are computed separately to avoid partial Unicode-token decoding artifacts. Missing reviews do not imply no effect.'}
    temporary = target.with_suffix('.json.tmp'); temporary.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'stage':args.stage,'profiles':[{k:p[k] for k in ('checkpoint','component','condition','same_first_token','jointly_matched_n','joint_match_same_first_token','joint_match_prefix_at_least')} for p in profiles]}))


if __name__ == '__main__': main()
