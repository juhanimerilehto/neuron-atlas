"""Recompute exported aggregates from immutable job artifacts without model inference."""
import json
from pathlib import Path
import sqlite3
import sys
import numpy as np
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'worker'))
from reference import JobStore, fingerprint, write_json

out=root/'campaigns'/'bracket-pilot-v1'
summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
manifest=summary['manifest']
calibration=json.loads((out/'calibration.json').read_text(encoding='utf-8'))
identity={'manifest':fingerprint(manifest),'calibration':fingerprint(calibration)}
store=JobStore(out,identity)
rows=store.db.execute('SELECT id,status,artifact FROM jobs').fetchall()
assert all(r[1]=='complete' for r in rows)
assert len(rows)<=manifest['max_jobs']
assert set(manifest['discovery_prompts']).isdisjoint(manifest['validation_prompts'])
assert set(manifest['calibration_prompts']).isdisjoint(manifest['validation_prompts'])
generation_count=0
output_tokens=0
artifact_results={}
for key,status,relative in rows:
    value=json.loads((out/relative).read_text(encoding='utf-8'))
    config=value['config']
    artifact_results[fingerprint(config)]=value['result']
    assert key==fingerprint({'identity':identity,'job':config})
    # A cached job must return without executing this callback.
    result=store.run(config,lambda:(_ for _ in ()).throw(AssertionError('cache miss')))
    assert result==value['result']
    if config['type']=='generation':
        generation_count+=1; output_tokens+=len(result['token_ids'])
        assert len(result['token_ids'])<=48
    else:
        assert result['kl_baseline_to_steered']>=0
        assert np.isclose(result['delta_logprob'],result['target_logprob']-result['baseline_target_logprob'])
for record in summary['records']:
    assert record['synthetic'] is False and record['state']=='Observed'
    assert np.isclose(record['validation']['mean_delta_logprob'],np.mean([e['delta_logprob'] for e in record['evidence']]))
    assert np.isclose(record['effect'],100*np.mean([e['target_probability']-e['baseline_target_probability'] for e in record['evidence']]))
    assert len(record['random_controls'])==16
    assert len(record['evidence'])==8
    for evidence in record['evidence']:
        config={'type':'distribution','prompt':evidence['prompt'],'layer':record['layer'],
            'kind':'neuron','index':record['neuron'],'dose':record['dose']}
        assert artifact_results[fingerprint(config)]=={k:v for k,v in evidence.items() if k!='prompt'}
store.db.close()
report={'passed':True,'jobs_checked':len(rows),'cache_hits_verified':len(rows),
    'generation_jobs':generation_count,'generated_tokens':output_tokens,
    'catalogue_records_checked':len(summary['records']), 'method':'offline artifact and export consistency; not independent inference replication'}
write_json(out/'audit.json',report)
print(json.dumps(report,indent=2))
