"""Exhaustive, resumable paired-checkpoint sweep with later-token screening."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gc
import ctypes
import hashlib
import json
import math
import msvcrt
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker'), str(ROOT / 'engine')]
from paired06 import data, analysis
from paired06.preflight import load
from reference import fingerprint, write_json
from batched import BatchJournal
from wide.quality import score

OUT = ROOT / 'campaigns' / data.CAMPAIGN


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    paths = list((ROOT / 'paired06').glob('*.py'))
    paths += [ROOT / p for p in ('exhaust/actor.py', 'wide/actor.py', 'extreme/worker.py',
                                 'worker/reference.py', 'engine/batched.py', 'wide/quality.py', 'rereview/reviewer.py')]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths if p.name != 'publish.py'}


def prepare():
    assert read(OUT / 'preflight.json')['passed']
    models = {name: read(OUT / name / 'model.json') for name in data.MODELS}
    manifest = {'campaign_id': data.CAMPAIGN, 'models': {k: {p: v[p] for p in ('repository', 'revision', 'files', 'config')}
                                                       for k, v in models.items()},
                'layers': 28, 'width': 3072, 'coordinates_per_model': 86016, 'seed': data.SEED,
                'broad_settings': data.BROAD, 'fine_settings': data.FINE_SETTINGS, 'checkpoints': data.CHECKPOINTS,
                'datasets': {k: getattr(data, k) for k in ('CALIBRATION', 'SCREEN', 'FINE', 'DISCOVERY', 'VALIDATION', 'TEST', 'LONG', 'REPLICATION')},
                'prefix_bank_sha256': digest(OUT / 'prefix-bank.json'),
                'calibration_sha256': {name: digest(OUT / name / 'calibration.json') for name in data.MODELS},
                'native_calibration_sha256': {name: digest(OUT / name / 'native-calibration.json') for name in data.MODELS},
                'intervention': 'One pre-down MLP coordinate clamped at all unpadded prompt and decode positions. '
                                'Both models use the ORIGINAL checkpoint calibration maxima and exactly the same signed targets. '
                                'BF16-rounded target values, greedy non-thinking generation, no parameter edits.',
                'chat_template_policy': 'Original Qwen3-0.6B template shared by both models; identical vocabulary verified in preflight.',
                'screen': 'Every coordinate at off and +/-4/12, on one shared original-model 64-token continuation. '
                          'Compare next-token distributions at 0/8/16/32/64 answer tokens; shorter prefixes explicitly retain only valid positions. '
                          'Per model/layer take 3 early-JS leaders, 3 distinct leaders by positive late-minus-early JS, '
                          'and 2 seeded random coordinates. Generate the UNION across both models; maximum 392 shared coordinates.',
                'selection': 'Fine proxy on 2 shared continuations and 17 doses in BOTH models. Common 13-setting discovery ladder. '
                             'No novelty preference. Validate union of 12 readable and 4 mixed/collapse nominations per checkpoint. '
                             'Then test union of 6 strongest readable nominations per checkpoint, at both nominated settings.',
                'job_ceiling_per_model': 500000, 'batches': {'screen': 128, 'generation': 32},
                'tokens': {'discovery': 128, 'validation': 192, 'locked_test': 256, 'long': 384, 'replication': 256},
                'primary_model': 'gpt-6.1-terra', 'confirmation_model': 'gpt-6.1-sol', 'reasoning': 'medium',
                'primary_request_ceiling': 700, 'confirmation_request_ceiling': 100,
                'gate': 'At least 3/4 change and 3/4 coherence in validation and final review; >=4/8 validation matches, '
                        '>=8/16 locked-test matches, >=4/8 longer and >=4/8 replication matches; '
                        '<=2 repetition and <=2 collapse flags across the 32 selected-condition neuron outputs. '
                        'Independent Sol must support the frozen validation description and meet the same final criteria. '
                        'Failed quality gates remain measured catalogue observations.',
                'scope': 'Numerical coordinate coverage is exhaustive for this grid. Prompts, doses and decoding are a finite sample. '
                         'Cross-checkpoint target values and token prefixes are identical; native activation scales are also recorded. '
                         'No guarantee that an abliterated coordinate represents the same feature.',
                'sources': source_hashes()}
    manifest = json.loads(json.dumps(manifest))
    path = OUT / 'manifest.json'
    if path.exists():
        assert read(path) == manifest, 'Frozen protocol or sources changed'
    else:
        write_json(path, manifest)
    return manifest, models


def status(stage, **extra):
    value = {'campaign_id': data.CAMPAIGN, 'stage': stage, 'timestamp_utc': datetime.now(timezone.utc).isoformat(), **extra}
    write_json(OUT / 'status.json', value)
    print(json.dumps(value), flush=True)


def config(coordinate, prompt, condition, stage, limit=0, random_index=None):
    layer, neuron = coordinate.split('-N')
    value = data.numeric(condition)
    row = {'coordinate': coordinate, 'layer': int(layer[1:]), 'neuron': int(neuron), 'prompt': prompt,
           'setting': condition, 'condition': 'off' if value == 0 else 'positive' if value > 0 else 'negative',
           'factor': abs(value), 'stage': stage, 'max_tokens': limit, 'type': 'generation' if limit else 'distribution'}
    if random_index is not None:
        row['random_index'] = random_index
    return row


class Run:
    def __init__(self, manifest, models):
        self.manifest = manifest
        self.models = models
        self.identity = fingerprint(manifest)
        self.prefixes = read(OUT / 'prefix-bank.json')
        self.journals = {name: BatchJournal(OUT / name / 'jobs.sqlite', fingerprint({'parent': self.identity, 'model': name}), 500000)
                         for name in data.MODELS}
        self.worker = None
        self.model_name = None
        self.reviewer = analysis.Reviewer(OUT / 'codex', model='gpt-6.1-terra', limit=700)
        self.confirmation = analysis.Reviewer(OUT / 'codex-confirm', model='gpt-6.1-sol', limit=100)

    def progress(self, stage, **extra):
        status(stage, completed_jobs={name: journal.completed() for name, journal in self.journals.items()}, **extra)

    def activate(self, name):
        if self.model_name == name:
            return
        self.worker = None
        gc.collect()
        torch.cuda.empty_cache()
        self.progress('loading_model', model=name)
        _, self.worker = load(name)
        self.worker.cal = read(OUT / name / 'calibration.json')
        self.model_name = name

    def execute(self, name, configs):
        journal = self.journals[name]
        def action(rows):
            self.activate(name)
            def measured(part):
                try:
                    return (self.worker.generate(part) if part[0]['type'] == 'generation'
                            else self.worker.prefix_scores(part, self.prefixes[part[0]['prompt']]))
                except torch.cuda.OutOfMemoryError:
                    gc.collect()
                    torch.cuda.empty_cache()
                    if len(part) == 1:
                        raise
                    midpoint = len(part) // 2
                    return measured(part[:midpoint]) + measured(part[midpoint:])
            return measured(rows)
        size = 32 if configs[0]['type'] == 'generation' else 128
        results = []
        for start in range(0, len(configs), size):
            results.extend(journal.run(configs[start:start + size], action))
        return results

    def screen(self, name):
        path = OUT / name / 'screen-summary.json'
        if path.exists():
            return read(path)
        result = []
        for layer in range(28):
            layer_path = OUT / name / f'screen-L{layer:02}.json'
            if layer_path.exists():
                result.extend(read(layer_path))
                continue
            configs = [config(f'L{layer}-N{neuron}', data.SCREEN[0], dose, 'screen')
                       for neuron in range(3072) for dose in data.BROAD]
            values = self.execute(name, configs)
            rows = []
            for neuron in range(3072):
                scores = dict(zip(data.BROAD, values[neuron * 5:(neuron + 1) * 5]))
                early = max(v['js'][0] for v in scores.values())
                late = max(max(v['js'][1:]) for v in scores.values())
                delayed = max(max(v['js'][1:]) - v['js'][0] for v in scores.values())
                rows.append({'coordinate': f'L{layer}-N{neuron}', 'layer': layer, 'neuron': neuron,
                             'early': early, 'late': late, 'delayed': delayed, 'scores': scores})
            write_json(layer_path, rows)
            result.extend(rows)
            self.progress('screening', model=name, layers_complete=layer + 1, coordinates_complete=(layer + 1) * 3072)
        write_json(path, result)
        return result

    def shortlist(self):
        path = OUT / 'shared-shortlist.json'
        if path.exists():
            return read(path)
        screens = {name: self.screen(name) for name in data.MODELS}
        selected = {}
        for layer in range(28):
            for name, rows in screens.items():
                local = rows[layer * 3072:(layer + 1) * 3072]
                used = set()
                for track, key in [('early', 'early'), ('late', 'delayed')]:
                    for row in sorted(local, key=lambda r: (-r[key], r['neuron'])):
                        if row['coordinate'] in used:
                            continue
                        selected.setdefault(row['coordinate'], {'layer': layer, 'neuron': row['neuron'], 'tracks': []})['tracks'].append(name + ':' + track)
                        used.add(row['coordinate'])
                        if sum(t == name + ':' + track for value in selected.values() if value['layer'] == layer for t in value['tracks']) == 3:
                            break
            available = [neuron for neuron in range(3072) if f'L{layer}-N{neuron}' not in selected]
            random_neurons = np.random.default_rng(data.SEED + layer).choice(available, 2, replace=False).tolist()
            for name in data.MODELS:
                for neuron in random_neurons:
                    selected.setdefault(f'L{layer}-N{neuron}', {'layer': layer, 'neuron': neuron, 'tracks': []})['tracks'].append(name + ':random')
        assert 224 <= len(selected) <= 392
        write_json(path, selected)
        return selected

    def fine(self, shortlist):
        summaries = {}
        for name in data.MODELS:
            path = OUT / name / 'fine.json'
            if path.exists():
                summaries[name] = read(path)
                continue
            sums = {cid: {dose: 0. for dose in data.FINE_SETTINGS} for cid in shortlist}
            for prompt in data.FINE:
                configs = [config(cid, prompt, dose, 'fine') for cid in shortlist for dose in data.FINE_SETTINGS]
                values = self.execute(name, configs)
                for cfg, value in zip(configs, values):
                    sums[cfg['coordinate']][cfg['setting']] += max(value['js']) / len(data.FINE)
                self.progress('fine_screen', model=name, prompt=prompt)
            write_json(path, sums)
            summaries[name] = sums
        ladders = {}
        for cid in shortlist:
            best = max(data.FINE_SETTINGS, key=lambda dose: max(summaries[name][cid][dose] for name in data.MODELS))
            center = abs(data.numeric(best)) or 1.
            nearest = sorted(sorted(data.MAGNITUDES, key=lambda value: (abs(math.log(value / center)), value))[:6])
            ladders[cid] = ['off'] + [data.setting(sign * value) for value in nearest for sign in (1, -1)]
        path = OUT / 'discovery-settings.json'
        if path.exists():
            assert read(path) == ladders
        else:
            write_json(path, ladders)
        return ladders

    def generations(self, stage, settings, prompts, limit, random_controls=False):
        output = {}
        for name in data.MODELS:
            path = OUT / name / f'{stage}.json'
            if path.exists():
                output[name] = read(path)
                continue
            pairs = {cid: [] for cid in settings}
            for prompt_index, prompt in enumerate(prompts):
                configs = [config(cid, prompt, dose, stage, limit, random_index)
                           for cid, doses in settings.items() for dose in doses
                           for random_index in (range(4) if random_controls else [None])]
                values = self.execute(name, configs)
                for cfg, value in zip(configs, values):
                    baseline = value['batch_baseline']
                    pairs[cfg['coordinate']].append({'id': fingerprint({'identity': self.identity, 'model': name, 'config': cfg}),
                        'prompt': prompt, 'condition': cfg['setting'], 'stage': stage,
                        'kind': 'random_direction' if random_controls else 'neuron', 'random_index': cfg.get('random_index'),
                        'baseline': baseline['text'], 'steered': value['text'], 'termination': value['termination'],
                        'token_ids': value['token_ids'], 'baseline_token_ids': baseline['token_ids'],
                        'intervention': value['intervention'], 'diagnostics': {'baseline': score(baseline['text']), 'steered': score(value['text'])}})
                self.progress(stage, model=name, prompts_complete=prompt_index + 1, prompts_total=len(prompts))
            write_json(path, pairs)
            output[name] = pairs
        return output

    def reviews(self, phase, pairs, settings, hypotheses=None, independent=False):
        directory = OUT / ('confirmations' if independent else 'reviews') / phase
        reviewer = self.confirmation if independent else self.reviewer
        reviewer_pool = ThreadPoolExecutor(max_workers=2)
        futures = {}
        result = {}
        coordinates = list(settings)
        for i, cid in enumerate(coordinates):
            path = directory / f'{cid}.json'
            if path.exists():
                result[cid] = read(path)
                continue
            request = analysis.bundle(phase, f'{phase}_{i}', [cid], pairs, settings, self.models, hypotheses)
            futures[cid] = (reviewer_pool.submit(reviewer.review, request), path)
            # Bound outstanding provider work so a failure stops dispatch promptly.
            if len(futures) >= 4:
                first = next(iter(futures))
                future, saved = futures.pop(first)
                result[first] = future.result()
                write_json(saved, result[first])
                self.progress('codex_' + phase, accepted=len(result), total=len(coordinates), independent=independent)
        for cid, (future, path) in futures.items():
            result[cid] = future.result()
            write_json(path, result[cid])
            self.progress('codex_' + phase, accepted=len(result), total=len(coordinates), independent=independent)
        reviewer_pool.shutdown(wait=True)
        return result

    def nominations(self, reviews, pairs, phase, readable_count, mixed_count):
        nominated = {}
        for name in data.MODELS:
            rows = []
            for cid, review in reviews.items():
                item = next(item for item in review['analysis']['items'] if item['component_id'] == name + '__' + cid)
                for effect in item['condition_effects']:
                    sample = [p for p in pairs[name][cid] if p['condition'] == effect['condition'] and p['kind'] == 'neuron']
                    hits = len(set(effect['matching_ids']) & {p['id'] for p in sample})
                    rows.append((cid, effect, hits / max(1, len(sample))))
            for readable, count in [(True, readable_count), (False, mixed_count)]:
                local = sorted((r for r in rows if (r[1]['coherence'] >= 3) == readable),
                               key=lambda r: (-r[1]['change_strength'], -r[2], -r[1]['coherence'], r[0], r[1]['condition']))
                used = set()
                layers = {}
                for cid, effect, _ in local:
                    layer = cid.split('-')[0]
                    if cid in used or layers.get(layer, 0) >= 3:
                        continue
                    nominated.setdefault(cid, set()).add(effect['condition'])
                    used.add(cid)
                    layers[layer] = layers.get(layer, 0) + 1
                    if len(used) == count:
                        break
        return {cid: sorted(doses) for cid, doses in nominated.items()}

    def run(self):
        shortlist = self.shortlist()
        ladders = self.fine(shortlist)
        discovery = self.generations('discovery', ladders, data.DISCOVERY, 128)
        reviews = self.reviews('discovery', discovery, ladders)
        nominated = self.nominations(reviews, discovery, 'discovery', 12, 4)
        validation_settings = {cid: data.refinements(doses) for cid, doses in nominated.items()}
        write_json(OUT / 'validation-plan.json', validation_settings)
        validation = self.generations('validation', validation_settings, data.VALIDATION, 192)
        validation_reviews = self.reviews('validation', validation, validation_settings)
        from paired06.publish import export
        export(self, validation, validation_reviews, stage='validation_complete')
        finalists = self.nominations(validation_reviews, validation, 'validation', 6, 0)
        write_json(OUT / 'frozen-finalists.json', finalists)
        hypotheses = {}
        for cid in finalists:
            for item in validation_reviews[cid]['analysis']['items']:
                hypotheses[item['component_id']] = [e for e in item['condition_effects'] if e['condition'] in finalists[cid]]
        write_json(OUT / 'frozen-hypotheses.json', hypotheses)
        tests = self.generations('locked_test', finalists, data.TEST, 256)
        longer = self.generations('long', finalists, data.LONG, 384)
        replication = self.generations('replication', finalists, data.REPLICATION, 256)
        controls = self.generations('random_controls', finalists, data.TEST[:8], 256, True)
        combined = {name: {cid: tests[name][cid] + longer[name][cid] + replication[name][cid] + controls[name][cid]
                           for cid in finalists} for name in data.MODELS}
        final_reviews = self.reviews('locked_test', combined, finalists, hypotheses)
        confirmations = self.reviews('locked_test', combined, finalists, hypotheses, True)
        self.audit(validation_reviews, final_reviews, confirmations)
        export(self, validation, validation_reviews, stage='complete', final_pairs=combined,
               final_reviews=final_reviews, confirmations=confirmations)
        self.progress('complete', coordinates_per_model=86016, shared_generated_candidates=len(shortlist),
                      validation_candidates=len(validation_settings), tested_candidates=len(finalists))

    def audit(self, validation_reviews, final_reviews, confirmations):
        assert source_hashes() == self.manifest['sources']
        counts = {}
        for name, journal in self.journals.items():
            counts[name] = dict(journal.db.execute("SELECT json_extract(config,'$.stage'),count(*) FROM jobs WHERE status='complete' GROUP BY 1"))
            assert counts[name]['screen'] == 86016 * 5
            assert journal.completed() == journal.count <= 500000
            assert len(read(OUT / name / 'screen-summary.json')) == 86016
        for reviews in (validation_reviews, final_reviews, confirmations):
            for review in reviews.values():
                directory = self.confirmation.directory if review['requested_model'] == 'gpt-6.1-sol' else self.reviewer.directory
                key = review['input_sha256']
                bundle = read(directory / f'{key}.bundle.json')
                analysis.validate(review['analysis'], bundle)
                wire, mapping = analysis.compact(bundle)
                replayed = (self.confirmation if directory == self.confirmation.directory else self.reviewer).accept(
                    key, review['winning_attempt'], bundle, wire, mapping)
                assert replayed['analysis'] == review['analysis']
        write_json(OUT / 'audit.json', {'passed': True, 'counts': counts, 'manifest_sha256': self.identity,
                                       'scope': 'All coordinates at the frozen grid, validated reviewer references and raw response linkage, '
                                                'source hashes and bounded completed journals. Semantic judgments remain fallible.'})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(data.SEED)
    with (OUT / '.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            manifest, models = prepare()
            if (OUT / 'status.json').exists() and read(OUT / 'status.json')['stage'] == 'complete':
                print('Completed campaign retained.', flush=True)
                return
            run = Run(manifest, models)
            run.run()
        except BaseException as exc:
            status('failed', error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            if awake:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
