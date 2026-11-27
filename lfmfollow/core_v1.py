"""Immutable follow-up foundation: bounded journals, exact anchors and raw review linkage."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gc
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sqlite3

import torch
from familylab import campaign as legacy, data
from familylab.preflight import load
from reference import fingerprint, write_json
from batched import BatchJournal
from lfmfollow import review_v1

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
PARENT = ROOT / 'campaigns/paired-lfm25-350m-v1'
MODELS = ('original', 'abliterated')
JOB_LIMIT, PRIMARY_LIMIT, SECONDARY_LIMIT = 25000, 400, 80


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def event(directory, stage, **extra):
    value = {'program': PROGRAM.name, 'stage_id': directory.name, 'stage': stage,
             'timestamp_utc': datetime.now(timezone.utc).isoformat(), **extra}
    write_json(directory / 'status.json', value)
    with (directory / 'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')
    print(json.dumps(value), flush=True)


def other_jobs(directory, name):
    total = 0
    for path in (PROGRAM / 'stages').glob('*/' + name + '/jobs.sqlite'):
        if path.parent.parent == directory:
            continue
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            total += db.execute('SELECT count(*) FROM jobs').fetchone()[0]
    return total


def config(coordinate, prompt, setting, stage, limit, random_index=None, **extra):
    layer, neuron = coordinate.split('-N')
    value = data.numeric(setting)
    result = {'coordinate': coordinate, 'layer': int(layer[1:]), 'neuron': int(neuron),
              'prompt': prompt, 'setting': setting,
              'condition': 'off' if value == 0 else 'positive' if value > 0 else 'negative',
              'factor': abs(value), 'stage': stage, 'max_tokens': limit, 'type': 'generation', **extra}
    if random_index is not None:
        result['random_index'] = random_index
    return result


def freeze(directory, plan, source_files):
    directory.mkdir(parents=True, exist_ok=True)
    parent, models = legacy.prepare()
    assert read(directory / 'preflight.json')['passed']
    sources = dict(parent['sources'])
    for name in ['lfmfollow/__init__.py', 'lfmfollow/core_v1.py', 'lfmfollow/review_v1.py',
                 'scripts/run_lfm_followup.py', *source_files]:
        sources[name] = digest(ROOT / name)
    value = {'program_id': PROGRAM.name, 'stage_id': directory.name, 'protocol': plan,
             'parent_manifest_identity': fingerprint(parent),
             'models': {k: {f: v[f] for f in ('repository', 'revision', 'files')} for k, v in models.items()},
             'calibration_sha256': {k: digest(PARENT / k / 'calibration.json') for k in MODELS},
             'preflight_sha256': digest(directory / 'preflight.json'),
             'runtime_lock_sha256': digest(ROOT / 'family-runtime-lock.json'), 'sources': sources,
             'ceilings': {'configurations_per_checkpoint_program': JOB_LIMIT,
                          'primary_requests_program': PRIMARY_LIMIT, 'secondary_requests_program': SECONDARY_LIMIT},
             'decoding': 'Greedy BF16 native LFM with original tokenizer/configuration, no weight updates. '
             'Every physical batch has an untouched anchor. OOM splits retain anchors. '
             'Checkpoint aliases are blinded to reviewers; frozen descriptions contain no previous scores or notes.'}
    value = json.loads(json.dumps(value))
    path = directory / 'manifest.json'
    if path.exists():
        assert read(path) == value, 'Stage sources or preregistration changed; versioned recovery is required'
    else:
        write_json(path, value)
    return value, models


class Run(legacy.Run):
    def __init__(self, directory, manifest, models):
        self.directory, self.manifest, self.models = directory, manifest, models
        self.identity = fingerprint(manifest)
        if manifest['protocol'].get('public_preregistration_required'):
            receipt = read(directory / 'preregistration-receipt.json')
            assert receipt['manifest_identity'] == self.identity and receipt['pages_verified'] is True
            assert len(receipt['commit_sha']) == 40
        self.worker = self.model_name = None
        self.journals = {}
        for name in MODELS:
            (directory / name).mkdir(exist_ok=True)
            remaining = JOB_LIMIT - other_jobs(directory, name)
            self.journals[name] = BatchJournal(directory / name / 'jobs.sqlite',
                fingerprint({'parent': self.identity, 'model': name}), remaining)
        self.reviewer = review_v1.Reviewer(PROGRAM / 'codex', model='gpt-6.1-terra', limit=PRIMARY_LIMIT)
        self.confirmation = review_v1.Reviewer(PROGRAM / 'codex-confirm', model='gpt-6.1-sol', limit=SECONDARY_LIMIT)

    def progress(self, stage, **extra):
        event(self.directory, stage, completed_jobs={k: v.completed() for k, v in self.journals.items()}, **extra)

    def activate(self, name):
        if self.model_name == name:
            return
        self.worker = None
        gc.collect()
        torch.cuda.empty_cache()
        self.progress('loading_model', model=name)
        _, worker = load(name)
        actor = self.manifest['protocol'].get('actor_module', 'familylab.actor')
        if actor != 'familylab.actor':
            assert actor == 'lfmfollow.timed_actor_v1'
            worker = importlib.import_module(actor).Worker(worker.model, worker.tok)
        worker.cal = read(PARENT / name / 'calibration.json')
        self.worker, self.model_name = worker, name

    def execute(self, name, configs):
        assert shutil.disk_usage(ROOT).free >= 2 * 1024**3, 'Disk reserve below 2 GiB; evidence retained'
        assert self.journals[name].count + other_jobs(self.directory, name) <= JOB_LIMIT
        return super().execute(name, configs)

    def generate_phase(self, phase, settings, prompts, limit, controls=False):
        result = {}
        for name in MODELS:
            path = self.directory / name / (phase + '.json')
            if path.exists():
                result[name] = read(path)
                continue
            pairs = {cid: [] for cid in settings}
            for index, prompt in enumerate(prompts):
                configs = [config(cid, prompt, dose, phase, limit, random_index)
                           for cid, doses in settings.items() for dose in doses
                           for random_index in (range(4) if controls else [None])]
                for cfg, value in zip(configs, self.execute(name, configs)):
                    baseline = value['batch_baseline']
                    pairs[cfg['coordinate']].append({
                        'id': fingerprint({'identity': fingerprint({'parent': self.identity, 'model': name}), 'config': cfg}),
                        'config': cfg, 'prompt': prompt, 'condition': cfg['setting'], 'stage': phase,
                        'kind': 'random_direction' if controls else 'neuron', 'random_index': cfg.get('random_index'),
                        'baseline': baseline['text'], 'steered': value['text'], 'termination': value['termination'],
                        'token_ids': value['token_ids'], 'baseline_token_ids': baseline['token_ids'],
                        'intervention': value['intervention']})
                self.progress(phase, model=name, prompts_complete=index + 1, prompts_total=len(prompts))
            write_json(path, pairs)
            result[name] = pairs
        return result

    def assess(self, phase, cases, hypotheses=None, independent=False):
        folder = self.directory / ('confirmations' if independent else 'reviews') / phase
        folder.mkdir(parents=True, exist_ok=True)
        reviewer = self.confirmation if independent else self.reviewer
        coordinates = list(cases['original'])
        result = {}
        def one(cid):
            request = review_v1.bundle(self.directory.name + '_' + phase, cid, cases, hypotheses)
            value = reviewer.review(request)
            write_json(folder / (cid + '.json'), value)
            return cid, value
        with ThreadPoolExecutor(max_workers=2) as pool:
            for cid, value in pool.map(one, coordinates):
                result[cid] = value
                self.progress('codex_' + phase, accepted=len(result), total=len(coordinates), independent=independent)
        return result

    def audit(self, cases, reviews, confirmations, expected_counts):
        assert all(digest(ROOT / k) == v for k, v in self.manifest['sources'].items())
        counts = {}
        exact = 0
        for name, journal in self.journals.items():
            counts[name] = dict(journal.db.execute("SELECT json_extract(config,'$.stage'),count(*) FROM jobs WHERE status='complete' GROUP BY 1"))
            assert counts[name] == expected_counts
            assert journal.count == journal.completed() <= journal.limit
            for pairs in cases[name].values():
                for pair in pairs:
                    row = journal.db.execute("SELECT config,result,status FROM jobs WHERE id=?", (pair['id'],)).fetchone()
                    assert row and row[2] == 'complete' and json.loads(row[0]) == pair['config']
                    raw = json.loads(row[1])
                    assert (raw['text'], raw['token_ids'], raw['batch_baseline']['text'], raw['batch_baseline']['token_ids']) == (
                        pair['steered'], pair['token_ids'], pair['baseline'], pair['baseline_token_ids'])
                    exact += 1
        for reviewer, values in [(self.reviewer, reviews), (self.confirmation, confirmations)]:
            for record in values.values():
                key = record['input_sha256']
                bundle = read(reviewer.directory / (key + '.bundle.json'))
                wire = read(reviewer.directory / (key + '.wire.json'))
                mapping = read(reviewer.directory / (key + '.reference-map.json'))
                replay = reviewer.accept(key, record['winning_attempt'], bundle, wire, mapping)
                assert replay['analysis'] == record['analysis']
        value = {'passed': True, 'stage_id': self.directory.name, 'manifest_sha256': self.identity,
                 'counts': counts, 'exact_pairs_linked_to_raw_jobs': exact, 'review_gaps': [],
                 'reviewer_requests_program': {p.name: len(list(p.glob('*.attempt-*.request.json')))
                    for p in [PROGRAM / 'codex', PROGRAM / 'codex-confirm']},
                 'scope': 'Frozen sources, exact job IDs/text/token linkage, full planned counts, validated raw reviewer evidence and finite ceilings.'}
        write_json(self.directory / 'independent-audit.json', value)
        return value
