"""Record a verified stage release after Pages readback; never performs a remote mutation."""
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


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=read(PROGRAM / 'programme.json')['finite_stages'][1:])
    args = parser.parse_args()
    directory = PROGRAM / 'stages' / args.stage
    audit = read(directory / 'independent-audit.json')
    assert audit['passed'] and read(directory / 'status.json')['stage'] == 'measurements_complete'
    outcomes = read(directory / 'outcomes.json')
    state = read(ROOT / '.cache/publication-state.json')
    release = ROOT / state['directory']
    payload = read(ROOT / (state['directory'] + '-payload') / 'list.json')
    assert state['head_sha'] and len(state['head_sha']) == 40 and state['expected_tree'] == payload['expected_tree']
    public = release / 'site-source/evidence' / PROGRAM.name / args.stage
    for filename in ('independent-audit.json','outcomes.json'):
        assert sha(directory / filename) == sha(public / filename), 'Verified release contains older stage evidence'
    report_name = f'campaign-{PROGRAM.name}-{args.stage}.md'
    report = ROOT / 'docs' / report_name
    assert sha(report) == sha(release / 'docs' / report_name), 'Polished report is not in the verified release'
    local = read(ROOT / 'site-source/catalogue.json')['records']
    published = {r['id']: r for r in read(release / 'site-source/catalogue.json')['records']}
    own = [r for r in local if r.get('campaign_id','').startswith(PROGRAM.name + '-' + args.stage + '-')]
    assert len(own) == outcomes['observations']
    for row in own:
        assert all(published[row['id']][field] == row[field] for field in ('state','paired_gate','primary_test_settings'))
    now = datetime.now(timezone.utc).isoformat()
    completion = {'program_id': PROGRAM.name, 'stage_id': args.stage, 'completed_at_utc': now,
        'configurations_per_checkpoint': {name: sum(counts.values()) for name,counts in audit['counts'].items()},
        'observations': outcomes['observations'], 'qualified_conditions': outcomes['qualified_frozen_condition_count'],
        'exact_pairs_linked_to_raw_jobs': audit['exact_pairs_linked_to_raw_jobs'], 'review_gaps': audit['review_gaps'],
        'independent_audit_sha256': sha(directory / 'independent-audit.json'),
        'report': report.relative_to(ROOT).as_posix(), 'report_sha256': sha(report),
        'outcomes_sha256': sha(directory / 'outcomes.json'), 'publication': state}
    write(directory / 'completion.json', completion)
    outbox_path = ROOT / '.cache/lfm-followup-publication-outbox.json'
    outbox = read(outbox_path)
    assert outbox['prepared_commit'] == state['head_sha']
    outbox.update(status='verified', deployment=state)
    write(outbox_path, outbox)
    write(ROOT / '.cache/lfm-followup-publication-history' / (state['head_sha']+'.json'), outbox)
    handoff_path = ROOT / '.cache/lfm-followup-handoff.json'
    handoff = read(handoff_path)
    handoff.update(public_snapshot=state, current_stage=read(PROGRAM / 'status.json').get('current_stage'),
                   last_completed_stage=args.stage)
    write(handoff_path, handoff)
    # The queue's publication barrier reads this receipt, so write it last.
    write(directory / 'publication-receipt.json', {'stage_id':args.stage, 'pages_verified':True,
        'commit_sha':state['head_sha'], 'independent_audit_sha256':completion['independent_audit_sha256'],
        'verified_at_utc':state['verified_at_utc'], 'recorded_at_utc':now})
    print(json.dumps({'stage':args.stage,'commit':state['head_sha'],'observations':len(own),'qualified_conditions':outcomes['qualified_frozen_condition_count'],'pages_verified':True}))


if __name__ == '__main__': main()
