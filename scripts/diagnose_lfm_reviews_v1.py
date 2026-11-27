"""Summarize saved rejected review attempts without repairing or accepting them."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
sys.path.insert(0,str(ROOT))
from rereview.reviewer import FIELDS, validate


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def violations(value, wire):
    result = []
    sources = {item['component_id']:item for item in wire['items']}
    for item in value.get('items',[]):
        source = sources.get(item.get('component_id'))
        if source is None:
            result.append({'kind':'unknown_component'}); continue
        for effect in item.get('condition_effects',[]):
            condition = effect.get('condition')
            rows = {p['id']:p for p in source['pairs'] if p['kind']=='neuron' and p['condition']==condition}
            controls = {p['id'] for p in source['pairs'] if p['kind']=='random_direction'}
            for field in FIELDS:
                refs = effect.get(field,[])
                if not isinstance(refs,list) or not all(isinstance(x,str) for x in refs): continue
                invalid = sorted(set(refs) - (controls if field=='similar_random_ids' else set(rows)))
                duplicate = len(refs)-len(set(refs))
                if invalid or duplicate:
                    result.append({'kind':'invalid_evidence_reference','component':item['component_id'],
                        'condition':condition,'field':field,'outside_condition_ids':invalid,'duplicate_count':duplicate})
            for ref in effect.get('matching_ids',[]):
                if isinstance(ref,str) and ref in rows:
                    pair = rows[ref]
                    baseline = pair.get('baseline',wire.get('baselines',{}).get(pair.get('baseline_ref')))
                    if pair['steered']==baseline:
                        result.append({'kind':'identical_text_claim','component':item['component_id'],'condition':condition,'evidence_id':ref})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=read(PROGRAM/'programme.json')['finite_stages'])
    args = parser.parse_args(); directory=PROGRAM/'stages'/args.stage
    assert directory.is_dir()
    gaps = [read(p) for p in (directory/'review-failures').glob('*.json')]
    missing = {args.stage+'_'+g['phase']+'_'+g['group'] for g in gaps}
    records = []
    for folder in ('codex','codex-confirm'):
        for path in sorted((PROGRAM/folder).glob('*.bundle.json')):
            bundle = read(path); namespace=bundle.get('namespace','')
            if not namespace.startswith(args.stage+'_'): continue
            key=path.name.removesuffix('.bundle.json'); attempts=[]
            for attempt in (1,2):
                stem=path.parent/(key+'.attempt-'+str(attempt)); error=Path(str(stem)+'.error.json')
                if not error.exists(): continue
                response=Path(str(stem)+'.response.json')
                item={'attempt':attempt,'error_type':read(error)['error_type'],'saved_error_sha256':sha(error),
                      'raw_response_sha256':sha(response) if response.exists() else None}
                try:
                    value=read(response); wire=read(path.parent/(key+'.wire.json'))
                    item['evidence_violations']=violations(value,wire)
                    try:
                        validate(value,wire); item['schema_and_reference_replay_passed']=True
                    except Exception as exc:
                        item.update(schema_and_reference_replay_passed=False,replay_error_type=type(exc).__name__)
                        if hasattr(exc,'validator'): item['schema_rule']=exc.validator
                except (OSError,ValueError,KeyError,TypeError):
                    item['response_readable_for_replay']=False
                attempts.append(item)
            if not attempts: continue
            accepted_path=path.parent/(key+'.analysis.json')
            accepted=read(accepted_path) if accepted_path.exists() else None
            records.append({'namespace':namespace,'reviewer_folder':folder,'bundle_sha256':sha(path),'bundle_key':key,
                'status':'recovered_on_bounded_retry' if accepted else 'review_unavailable' if namespace in missing else 'rejected_attempt_retry_pending',
                'winning_attempt':accepted['winning_attempt'] if accepted else None,'rejected_attempts':attempts})
    result={'stage':args.stage,'observed_at_utc':datetime.now(timezone.utc).isoformat(),
        'analysis_source_sha256':sha(Path(__file__)),'validator_source_sha256':sha(ROOT/'rereview/reviewer.py'),
        'scope':'Mutable latest diagnosis of preserved raw attempts. No response is repaired, accepted, relabeled or sent to a model. A schema replay alone does not replace execution/tool-use checks.',
        'saved_review_gaps':gaps,'rejected_bundles':records}
    target=directory/'review-diagnostics-latest.json'; temporary=target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'stage':args.stage,'bundles_with_rejected_attempts':len(records),'saved_review_gaps':len(gaps)}))


if __name__=='__main__': main()
